def test_native_health_can_select_macos(tmp_path, monkeypatch):
    from app import platforms
    from app.runner.native import NativeRunner
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(platforms, 'architecture', lambda: 'arm64')
    monkeypatch.setattr(platforms, 'background_options', lambda: {})
    runner = NativeRunner(tmp_path)
    health = runner.health()
    assert health['available'], health
    assert health['image_ref'].endswith('-macos-arm64')
    assert health['limits']['memory_enforcement'] == 'rss-monitor'
    assert runner.python_version.count('.') == 2


def test_macos_backend_import_does_not_load_windows_api(monkeypatch):
    from app import platforms
    from app.runner.native_process import process_backend
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    assert process_backend().__name__ == 'MacProcess'
