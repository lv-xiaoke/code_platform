import threading
import time
from uuid import uuid4

import pytest

from test_multilanguage_native import SOURCES, language_registry


@pytest.mark.parametrize('language', SOURCES)
def test_terminal_supports_language_input_and_eof(tmp_path, language_registry, language):
    from app.runner.terminal import TerminalSession
    from app.runner.terminal_native import NativeTerminalRunner
    from app.runner.schemas import TerminalInput
    assert language_registry.capability(language)['available']
    session = TerminalSession(str(uuid4()), 'p', SOURCES[language], language=language)
    runner = NativeTerminalRunner(tmp_path, registry=language_registry)
    result = []
    thread = threading.Thread(target=lambda: result.append(runner.execute(session)))
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while session.status not in ('running', 'failed') and time.monotonic() < deadline:
            time.sleep(.02)
        assert session.status == 'running'
        assert session.snapshot()['language'] == language
        session.send(TerminalInput(request_id='one', text='你好\n'))
        session.send(TerminalInput(request_id='eof', eof=True))
        thread.join(8)
        assert not thread.is_alive()
        assert result[0]['status'] == 'executed', result
        assert session.stdout.replace('\r\n', '\n') == '你好\n'
        assert session.snapshot()['runtime_version']
    finally:
        session.stop_event.set()
        thread.join(5)
        runner.close()


def test_terminal_start_identity_has_language_and_compile_failure_is_terminal(loaded, tmp_path):
    from app.runner.terminal_native import NativeTerminalRunner
    from app.runner.consent import accept_native_execution
    from app.runner.toolchains.registry import ToolchainRegistry
    c, app, _, pid = loaded
    from pathlib import Path
    registry = ToolchainRegistry(Path(__file__).resolve().parents[2] / 'runtime/toolchains-ci')
    app.state.terminal_service.runner = NativeTerminalRunner(tmp_path, registry=registry)
    try:
        accept_native_execution(app.state.db.data_dir)
        body = dict(request_id=str(uuid4()), source_code='public class Main {', language='java')
        response = c.post(f'/api/v1/problems/{pid}/terminals', json=body)
        assert response.status_code == 202, response.text
        assert c.post(f'/api/v1/problems/{pid}/terminals', json={**body, 'language': 'python'}).status_code == 409
        for _ in range(500):
            state = c.get('/api/v1/terminals/' + response.json()['id']).json()
            if state['status'] not in ('starting', 'preparing', 'compiling', 'running'): break
            time.sleep(.02)
        assert state['status'] == 'compile_error', state
        assert state['compile']['stderr']
        assert state['stdout'] == ''
        assert state['input_closed']
        assert c.post('/api/v1/terminals/' + state['id'] + '/input', json={'request_id': 'late', 'text': 'x'}).status_code == 409
    finally:
        registry.close()


def test_stop_during_compilation_never_reaches_ready(loaded, tmp_path, monkeypatch):
    from app.runner.terminal_native import NativeTerminalRunner
    from app.runner.consent import accept_native_execution
    from app.runner import programs
    from app.runner.toolchains.registry import ToolchainRegistry
    from pathlib import Path
    c, app, _, pid = loaded
    compiling = threading.Event()
    def blocked_prepare(self, job_id, language, source, stop_event, on_phase=None):
        on_phase({'type': 'phase', 'status': 'compiling', 'language': language})
        compiling.set()
        assert stop_event.wait(5)
        raise programs.PreparationError('stopped', {'stderr': 'compile stopped'}, {'language': language})
    monkeypatch.setattr(programs.ProgramPreparer, 'prepare', blocked_prepare)
    registry = ToolchainRegistry(Path(__file__).resolve().parents[2] / 'runtime/toolchains-ci')
    app.state.terminal_service.runner = NativeTerminalRunner(tmp_path, registry=registry)
    try:
        accept_native_execution(app.state.db.data_dir)
        request_id = str(uuid4())
        response = c.post(f'/api/v1/problems/{pid}/terminals', json=dict(request_id=request_id,
            source_code='class Main {}', language='java'))
        assert response.status_code == 202
        assert compiling.wait(3)
        stopped = c.post('/api/v1/terminal-requests/' + request_id + '/stop')
        assert stopped.status_code == 200
        assert stopped.json()['status'] == 'stopped'
        assert stopped.json().get('runtime_version') is None
        assert not app.state.terminal_service.sessions
    finally:
        registry.close()
