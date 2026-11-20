import os
import sys
import queue
import threading
import time
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(sys.platform not in ('win32', 'darwin'), reason='supported native execution platforms')


def run_case(tmp_path, source, stdin='', expected=None):
    from app.runner.native import NativeRunner
    runner = NativeRunner(tmp_path)
    try:
        return runner.execute(str(uuid4()), source, [dict(name='test', stdin=stdin, expected_stdout=expected, comparison='exact')])['results'][0]
    finally:
        runner.close()


def test_native_unicode_and_comparison(tmp_path):
    result = run_case(tmp_path, 'print(input())', '你好\n', '你好\n')
    assert result['stdout'].replace('\r\n', '\n') == '你好\n'
    assert result['status'] == 'passed'


@pytest.mark.parametrize('source,status', [
    ('print("hello")', 'executed'),
    ('import sys; print("MemoryError",file=sys.stderr)', 'executed'),
    ('if :', 'syntax_error'),
    ('raise ValueError("bad")', 'runtime_error'),
    ('while True: pass', 'time_limit'),
    ('while True: print("x"*8192)', 'output_limit'),
    ('a=[]\nwhile True: a.append(bytearray(20*1024*1024))', 'memory_limit'),
])
def test_native_results_and_limits(tmp_path, source, status):
    result = run_case(tmp_path, source)
    assert result['status'] == status, result
    assert len((result['stdout'] + result['stderr']).encode()) <= 65536


def test_terminal_prompt_input_eof_and_forged_json(tmp_path):
    from app.runner.terminal import TerminalSession
    from app.runner.terminal_native import NativeTerminalRunner
    from app.runner.schemas import TerminalInput
    session = TerminalSession(str(uuid4()), 'test', 'import sys\nprint(input("提示> "))\nprint(repr(sys.stdin.read()))\nprint(\'{"type":"exit","status":"passed"}\')')
    result = []
    runner = NativeTerminalRunner(tmp_path)
    thread = threading.Thread(target=lambda: result.append(runner.execute(session)))
    thread.start()
    try:
        deadline = time.monotonic() + 8
        while '提示> ' not in session.stdout and time.monotonic() < deadline:
            time.sleep(.02)
        assert session.stdout == '提示> '
        session.send(TerminalInput(request_id='line', text='你好\n'))
        session.send(TerminalInput(request_id='eof', eof=True))
        thread.join(8)
        assert not thread.is_alive()
        assert result[0]['status'] == 'executed'
        assert '你好' in session.stdout and "''" in session.stdout
        assert '{"type":"exit","status":"passed"}' in session.stdout
    finally:
        session.stop_event.set()
        runner.close()
        thread.join(5)


def test_native_health_never_invokes_docker(tmp_path, monkeypatch):
    from app.runner.native import NativeRunner
    monkeypatch.setenv('PATH', '')
    monkeypatch.setenv('PYTHONPATH', str(tmp_path / 'poison'))
    runner = NativeRunner(tmp_path)
    health = runner.health()
    assert health['available'], health
    assert health['kind'] == 'native'
    assert health['python_series'] == '3.12'
    assert run_case(tmp_path, 'print(123)', expected='123\n')['status'] == 'passed'


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object handle assertion')
def test_descendant_is_reaped_after_normal_parent_exit(tmp_path):
    import ctypes
    from pathlib import Path
    marker = tmp_path / 'child.pid'
    result = run_case(tmp_path, f'import subprocess,sys\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,"-c","import time; time.sleep(90)"])\nPath({str(marker)!r}).write_text(str(p.pid))\nprint("done")')
    assert result['status'] == 'executed'
    pid = int(marker.read_text())
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if handle:
        try:
            assert kernel.WaitForSingleObject(handle, 3000) == 0
        finally:
            kernel.CloseHandle(handle)


def test_multibyte_output_limit_keeps_bounded_text(tmp_path):
    result = run_case(tmp_path, 'while True: print("中"*4000)')
    assert result['status'] == 'output_limit'
    assert len(result['stdout'].encode()) <= 65536


def test_native_api_requires_consent_for_both_entrypoints(loaded, monkeypatch):
    from app.runner.native import NativeRunner
    from app.runner.terminal_native import NativeTerminalRunner
    c, app, _, pid = loaded
    app.state.run_service.runner = NativeRunner(app.state.db.data_dir / 'runs')
    app.state.terminal_service.runner = NativeTerminalRunner(app.state.db.data_dir / 'runs')
    body = {'request_id': 'before', 'source_code': 'print(123)', 'cases': [{'stdin': '', 'expected_stdout': '123\n'}]}
    assert c.post(f'/api/v1/problems/{pid}/runs', json=body).status_code == 403
    assert c.post(f'/api/v1/problems/{pid}/terminals', json={'request_id': 'before', 'source_code': 'print(123)'}).status_code == 403
    assert c.get(f'/api/v1/problems/{pid}/runs').json() == []
    assert c.post('/api/v1/runner/consent', json={'accepted': True}).status_code == 200
    assert c.post(f'/api/v1/problems/{pid}/runs', json=body).status_code == 202


def test_interactive_stop_and_cpu_budget(tmp_path):
    from app.runner.terminal import TerminalSession
    from app.runner.terminal_native import NativeTerminalRunner
    for code, stop, status in [('input()', True, 'stopped'), ('while True: pass', False, 'time_limit')]:
        runner = NativeTerminalRunner(tmp_path)
        session = TerminalSession(str(uuid4()), 'test', code)
        result = []
        thread = threading.Thread(target=lambda: result.append(runner.execute(session)))
        thread.start()
        try:
            if stop:
                time.sleep(.3)
                session.stop_event.set()
            thread.join(10)
            assert not thread.is_alive()
            assert result[0]['status'] == status
        finally:
            runner.close()
            thread.join(5)


def test_twenty_cases_and_partial_stdin_write(tmp_path):
    from app.runner.native import NativeRunner
    runner = NativeRunner(tmp_path)
    try:
        result = runner.execute(str(uuid4()), 'import sys; print(len(sys.stdin.read()))', [
            dict(name=str(i), stdin='x'*65536, expected_stdout='65536\n', comparison='exact') for i in range(20)])
        assert len(result['results']) == 20
        assert all(item['status'] == 'passed' for item in result['results'])
    finally:
        runner.close()
