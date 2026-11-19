import json
import pytest


def test_pid_reuse_is_treated_as_parent_exit(monkeypatch):
    from app import platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(platforms, 'process_identity', lambda pid: 'new-process')
    platforms.wait_for_process(12345, 'old-process', timeout=0)


def test_same_parent_times_out_without_terminating_it(monkeypatch):
    from app import platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(platforms, 'process_identity', lambda pid: 'same')
    with pytest.raises(RuntimeError, match='未退出'):
        platforms.wait_for_process(12345, 'same', timeout=0)


def test_restore_waits_for_data_lock(tmp_path):
    from app.desktop import wait_data_unlock
    from app.runtime import RuntimeLock
    with RuntimeLock(tmp_path):
        with pytest.raises(RuntimeError, match='数据'):
            wait_data_unlock(tmp_path, timeout=0)
    wait_data_unlock(tmp_path, timeout=0)


def test_restore_helper_uses_platform_options(tmp_path, monkeypatch):
    from app import desktop_restore, platforms
    (tmp_path / 'status.json').write_text(json.dumps({'state': 'preview'}))
    monkeypatch.setattr(platforms, 'background_options', lambda: {'start_new_session': True})
    captured = {}
    class Process:
        def poll(self): return None
    def popen(argv, **kwargs):
        captured.update(kwargs)
        (tmp_path / ('helper-ready-' + argv[-1])).write_text('ready')
        return Process()
    monkeypatch.setattr(desktop_restore.subprocess, 'Popen', popen)
    desktop_restore.start_restore_helper(tmp_path, ['helper'])
    assert captured == {'start_new_session': True}
