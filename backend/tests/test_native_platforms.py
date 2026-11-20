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


def test_first_macos_runner_metadata_is_host_correct(tmp_path, monkeypatch):
    from app import platforms
    from app.runner.native import NativeRunner
    from app.runner.terminal_native import NativeTerminalRunner
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(platforms, 'architecture', lambda: 'arm64')
    for runner in (NativeRunner(tmp_path / 'runs'), NativeTerminalRunner(tmp_path / 'terminals')):
        assert runner.image_ref.endswith('-macos-arm64')


def test_macos_kernel_cpu_limit_maps_to_time_limit(tmp_path, monkeypatch):
    from app import platforms
    from app.runner import native_process
    class CpuLimitedProcess:
        memory_exceeded = False
        def __init__(self, *args, **kwargs):
            self.stdin, self.stdout, self.stderr = [(tmp_path / name).open('w+b', buffering=0)
                                                  for name in ('stdin', 'stdout', 'stderr')]
        def limit_events(self): return False
        def cpu_seconds(self): return 2.99
        def poll(self): return -24  # Darwin SIGXCPU
        def terminate(self): pass
        def close(self):
            for stream in (self.stdin, self.stdout, self.stderr):
                stream.close()
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(native_process, 'process_backend', lambda: CpuLimitedProcess)
    script = tmp_path / 'cpu.py'
    script.write_text('while True: pass')
    from app.paths import native_python
    result = native_process.execute_process(native_python(), script, wall_seconds=300)
    assert result['status'] == 'time_limit'


def test_normal_source_entry_defaults_to_multilanguage_native(monkeypatch):
    from app.runner.factory import runner_kind
    monkeypatch.delenv('CODETOP_RUNNER', raising=False)
    assert runner_kind() == 'native'
    monkeypatch.setenv('CODETOP_RUNNER', 'docker')
    assert runner_kind() == 'docker'
