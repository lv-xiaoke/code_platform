import os
import queue
import sys
import threading
import time
from uuid import uuid4
import pytest

pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='requires macOS process groups')


@pytest.mark.parametrize('code,status', [
    ('print("你好")', 'executed'),
    ('if :', 'syntax_error'),
    ('raise ValueError("bad")', 'runtime_error'),
    ('while True: pass', 'time_limit'),
    ('while True: print("x" * 8192)', 'output_limit'),
    ('a=[]\nwhile True: a.append(bytearray(20*1024*1024))', 'memory_limit'),
])
def test_macos_statuses(tmp_path, code, status):
    from app.runner.native import NativeRunner
    runner = NativeRunner(tmp_path)
    try:
        result = runner.execute(str(uuid4()), code, [{'stdin': ''}])['results'][0]
        assert result['status'] == status, result
        assert len((result['stdout'] + result['stderr']).encode()) <= 65536
    finally:
        runner.close()


def test_unicode_input_and_no_inherited_secrets(tmp_path, monkeypatch):
    from app.runner.native import NativeRunner
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'must-not-inherit')
    runner = NativeRunner(tmp_path)
    try:
        result = runner.execute(str(uuid4()), 'import os\nprint(input())\nprint(os.environ.get("DEEPSEEK_API_KEY", "absent"))',
                                [{'stdin': '你好\n', 'expected_stdout': '你好\nabsent\n'}])['results'][0]
        assert result['status'] == 'passed', result
    finally:
        runner.close()


def test_stop_while_waiting_for_input_and_eof(tmp_path):
    from app.runner.native_process import execute_process
    from app.paths import native_python
    script = tmp_path / 'input.py'
    script.write_text('import sys\nprint(sys.stdin.read())')
    inputs, stop, results = queue.Queue(), threading.Event(), []
    thread = threading.Thread(target=lambda: results.append(execute_process(native_python(), script, inputs=inputs, stop_event=stop)))
    thread.start()
    time.sleep(.15)
    stop.set()
    thread.join(5)
    assert not thread.is_alive()
    assert results[0]['status'] == 'stopped'
    inputs = queue.Queue()
    inputs.put({'text': '结束', 'eof': True})
    result = execute_process(native_python(), script, inputs=inputs)
    assert result['stdout'].strip() == '结束'


def test_parent_exit_cleans_child_holding_pipe(tmp_path):
    import psutil
    from app.runner.native_process import execute_process
    from app.paths import native_python
    script = tmp_path / 'child.py'
    script.write_text('import subprocess,sys\np=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"])\nprint(p.pid, flush=True)')
    started = time.monotonic()
    result = execute_process(native_python(), script)
    assert time.monotonic() - started < 5
    pid = int(result['stdout'].strip())
    try:
        process = psutil.Process(pid)
        assert process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass


def test_detached_child_cannot_keep_transport_threads_alive(tmp_path):
    import psutil
    from app.runner.native_process import execute_process
    from app.paths import native_python
    before = {t.ident for t in threading.enumerate()}
    script = tmp_path / 'detached.py'
    script.write_text('import subprocess,sys\np=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True)\nprint(p.pid,flush=True)')
    result = execute_process(native_python(), script)
    try:
        assert not [t for t in threading.enumerate() if t.ident not in before]
    finally:
        # One explicitly named test child outside the runner's documented group scope.
        pid = int(result['stdout'].strip())
        try:
            child = psutil.Process(pid)
            if 'time.sleep(30)' in ' '.join(child.cmdline()):
                child.kill()
                child.wait(timeout=5)
        except psutil.NoSuchProcess:
            pass
