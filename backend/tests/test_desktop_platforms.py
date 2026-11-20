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


def test_macos_browser_open_is_independent_of_path(monkeypatch):
    from app import platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setenv('PATH', '')
    captured = []
    monkeypatch.setattr(platforms.subprocess, 'run', lambda argv, **kw: captured.append((argv, kw)))
    platforms.open_browser('http://127.0.0.1:8000/')
    assert captured[0][0] == ['/usr/bin/open', 'http://127.0.0.1:8000/']
    assert captured[0][1]['check'] is True


def test_failed_browser_launch_has_manual_url(monkeypatch):
    from app import platforms
    import webbrowser
    monkeypatch.setattr(platforms, 'system_name', lambda: 'windows')
    monkeypatch.setattr(webbrowser, 'open', lambda url: False)
    with pytest.raises(RuntimeError, match='http://127.0.0.1:8000/'):
        platforms.open_browser('http://127.0.0.1:8000/')


def test_macos_port_probe_allows_rebinding_after_restore(monkeypatch):
    from app import desktop, platforms
    import socket
    options = []
    class Probe:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def setsockopt(self, *args): options.append(args)
        def bind(self, address): self.address = address
        def getsockname(self): return self.address
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(desktop.socket, 'socket', Probe)
    assert desktop.free_port(18061) == 18061
    assert (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) in options
