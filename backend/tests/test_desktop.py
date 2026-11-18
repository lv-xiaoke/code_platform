import json
import os
from pathlib import Path
import sys


def test_desktop_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    from app.paths import application_root, default_data_dir, native_python
    installed = tmp_path / '安装 with spaces'
    installed.mkdir()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(installed / 'CodeTop.exe'))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'user'))
    monkeypatch.delenv('CODETOP_DATA_DIR', raising=False)
    monkeypatch.chdir(tmp_path)
    assert application_root() == installed
    assert default_data_dir() == tmp_path / 'user' / 'CodeTopLocal'
    assert native_python() == installed / 'python' / 'python.exe'


def test_bundled_runtime_rejects_tampered_files(tmp_path, monkeypatch):
    import hashlib
    import pytest
    from app.paths import verify_bundled_runtime
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'CodeTop.exe'))
    (tmp_path / 'python').mkdir()
    file = tmp_path / 'python/python.exe'
    file.write_bytes(b'trusted runtime')
    (tmp_path / 'runtime-lock.json').write_text(json.dumps({'files': {'python.exe': hashlib.sha256(file.read_bytes()).hexdigest()}}))
    verify_bundled_runtime()
    file.write_bytes(b'tampered runtime')
    with pytest.raises(ValueError, match='校验'):
        verify_bundled_runtime()


def test_concurrent_launcher_waits_for_first_start(tmp_path):
    import threading
    import time
    from app.desktop import launcher_lock
    from app.runtime import RuntimeLock
    entered = threading.Event()
    def first():
        with RuntimeLock(tmp_path, 'launcher.lock'):
            entered.set()
            time.sleep(.25)
    thread = threading.Thread(target=first)
    thread.start()
    entered.wait(2)
    with launcher_lock(tmp_path):
        thread.join(1)
        assert not thread.is_alive()
    thread.join(2)


def test_unrelated_health_json_is_not_a_matching_service(tmp_path):
    from app.desktop import matches
    for value in ([], None, 'ok', 123, {'app': 'codetop-local', 'root': None},
                  {'app': 'codetop-local', 'root': 123, 'data_dir': {}}):
        assert not matches(value, tmp_path)


def test_timed_out_restore_helper_is_invalidated_and_terminated(tmp_path, monkeypatch):
    import pytest
    from fastapi import HTTPException
    from app.desktop_restore import start_restore_helper
    path = tmp_path / 'status.json'
    path.write_text(json.dumps({'state': 'preview', 'ticket': 'test'}))
    (tmp_path / 'helper-ready').write_text('stale previous attempt')
    class SlowHelper:
        terminated = False
        def poll(self): return None
        def terminate(self): self.terminated = True
        def wait(self, timeout): return 1
    helper = SlowHelper()
    monkeypatch.setattr('app.desktop_restore.subprocess.Popen', lambda *a, **k: helper)
    with pytest.raises(HTTPException) as exc:
        start_restore_helper(tmp_path, ['fake-helper'], timeout=.03)
    assert exc.value.status_code == 503
    assert helper.terminated
    value = json.loads(path.read_text())
    assert value['state'] == 'preview'
    assert value.get('attempt') is None


def test_restore_preview_rejects_corruption_without_changing_data(loaded):
    from app.backups import create_backup
    c, app, _, pid = loaded
    backup = create_backup(app.state.db)
    raw = (app.state.db.data_dir / 'backups' / backup['filename']).read_bytes()
    # Source mode cannot start desktop helper, but preview/validation is safe.
    response = c.post('/api/v1/desktop/restore/preview', files={'file': ('backup.zip', raw, 'application/zip')})
    assert response.status_code == 200, response.text
    assert response.json()['counts']['problems'] == 4
    assert c.get('/api/v1/problems').json()['count'] == 4
    response = c.post('/api/v1/desktop/restore/preview', files={'file': ('bad.zip', b'broken', 'application/zip')})
    assert response.status_code == 422
    assert c.get('/api/v1/problems').json()['count'] == 4
