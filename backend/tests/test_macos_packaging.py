import hashlib
import json
from pathlib import Path
import pytest


def test_runtime_symlink_cannot_escape_source(tmp_path):
    from scripts.build_macos import validate_runtime_link
    root = tmp_path / 'python'
    root.mkdir()
    external = tmp_path / 'outside'
    external.write_text('not runtime')
    link = root / 'bad'
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip('symlink creation unavailable')
    with pytest.raises(ValueError, match='outside'):
        validate_runtime_link(link, root)


def test_runtime_manifest_records_final_signed_bytes(tmp_path):
    from scripts.build_macos import write_runtime_manifest
    runtime = tmp_path / 'python'
    (runtime / 'bin').mkdir(parents=True)
    python = runtime / 'bin/python3'
    python.write_bytes(b'signed runtime bytes')
    target = tmp_path / 'runtime-lock.json'
    write_runtime_manifest(runtime, target, 'arm64')
    value = json.loads(target.read_text())
    assert value['executable'] == 'bin/python3'
    assert value['files']['bin/python3'] == hashlib.sha256(python.read_bytes()).hexdigest()
    assert value['architecture'] == 'arm64'


def test_build_rejects_wrong_architecture():
    from scripts.build_macos import check_architecture
    with pytest.raises(ValueError, match='architecture'):
        check_architecture('x86_64', 'arm64')
    check_architecture('arm64', 'arm64')


def test_unsigned_build_cannot_be_mislabeled_release():
    from scripts.build_macos import package_name
    assert 'unsigned' in package_name('1.6.0', 'arm64', False)
    assert 'unsigned' not in package_name('1.6.0', 'arm64', True)


def test_frontend_failure_keeps_current_release(tmp_path):
    from scripts.build_frontend import build_frontend
    import subprocess
    releases = tmp_path / 'releases'
    releases.mkdir()
    current = releases / 'current.json'
    current.write_text('{"path":"releases/old"}')
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    with pytest.raises(subprocess.CalledProcessError):
        build_frontend(tmp_path, 'node', run=fail)
    assert json.loads(current.read_text())['path'] == 'releases/old'


def test_runtime_receipt_ignores_only_generated_bytecode(tmp_path):
    from scripts.build_macos import runtime_files
    from scripts.fetch_macos_python import source_files
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__/ssl.cpython-312.pyc').write_bytes(b'generated')
    (tmp_path / 'ssl.py').write_bytes(b'trusted source')
    expected = {'ssl.py': hashlib.sha256(b'trusted source').hexdigest()}
    assert runtime_files(tmp_path) == expected
    assert source_files(tmp_path) == expected


def test_smoke_uses_absolute_data_dir_for_relative_report(tmp_path, monkeypatch):
    from scripts.verify_macos import verify_app
    from scripts import verify_macos
    app = tmp_path / 'CodeTop.app'
    executable = app / 'Contents/MacOS/CodeTop'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'fake mac executable')
    monkeypatch.chdir(tmp_path)
    captured = {}
    class StopProbe(Exception): pass
    def stop(argv, **kwargs):
        captured.update(kwargs)
        raise StopProbe()
    class NoNetwork:
        def open(self, *args, **kwargs): raise OSError('no server')
    monkeypatch.setattr(verify_macos.subprocess, 'Popen', stop)
    monkeypatch.setattr(verify_macos.urllib.request, 'build_opener', lambda *a: NoNetwork())
    with pytest.raises(StopProbe):
        verify_app(app, Path('reports/smoke.json'))
    assert captured['cwd'].is_absolute()


def test_native_health_does_not_write_bytecode(tmp_path, monkeypatch):
    from app.runner.native import NativeRunner
    import subprocess
    real_run = subprocess.run
    commands = []
    def capture(argv, **kwargs):
        commands.append(argv)
        return real_run(argv, **kwargs)
    monkeypatch.setattr(subprocess, 'run', capture)
    assert NativeRunner(tmp_path).health()['available']
    assert '-B' in commands[0]


def test_missing_or_external_relative_dylib_is_rejected(tmp_path):
    from scripts.build_macos import resolve_library
    app = tmp_path / 'CodeTop.app'
    executable = app / 'Contents/MacOS/CodeTop'
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'exe')
    library = app / 'Contents/Frameworks/good.dylib'
    library.parent.mkdir()
    library.write_bytes(b'lib')
    assert resolve_library('@rpath/good.dylib', executable, app, executable, [library.parent]) == library
    with pytest.raises(ValueError, match='dependency'):
        resolve_library('@rpath/missing.dylib', executable, app, executable, [library.parent])
    with pytest.raises(ValueError, match='dependency'):
        resolve_library('@loader_path/../../../outside.dylib', executable, app, executable, [])


def test_signing_generates_manifest_after_inner_signature(tmp_path, monkeypatch):
    from scripts import build_macos
    app = tmp_path / 'CodeTop.app'
    runtime = app / 'Contents/Resources/python'
    python = runtime / 'bin/python3'
    python.parent.mkdir(parents=True)
    python.write_bytes(b'\xcf\xfa\xed\xfeoriginal')
    def sign(argv, **kwargs):
        if argv[0] == '/usr/bin/codesign' and '--sign' in argv:
            if Path(argv[-1]) == python:
                python.write_bytes(b'\xcf\xfa\xed\xfesigned')
            elif Path(argv[-1]) == app:
                manifest = json.loads((app / 'Contents/Resources/runtime-lock.json').read_text())
                assert manifest['files']['bin/python3'] == hashlib.sha256(python.read_bytes()).hexdigest()
    monkeypatch.setattr(build_macos, 'run', sign)
    build_macos.sign_app(app, '-', 'arm64')


def test_frozen_entry_disables_resource_bytecode_before_import(monkeypatch):
    import runpy
    import sys
    import types
    observed = []
    fake = types.ModuleType('app.desktop')
    fake.entry = lambda: observed.append(sys.dont_write_bytecode)
    monkeypatch.setitem(sys.modules, 'app.desktop', fake)
    monkeypatch.setattr(sys, 'dont_write_bytecode', False)
    runpy.run_path(str(Path(__file__).resolve().parents[2] / 'packaging/desktop_entry.py'))
    assert observed == [True]
