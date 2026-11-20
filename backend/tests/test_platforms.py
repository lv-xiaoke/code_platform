import hashlib
import json
import sys

import pytest


def test_frozen_macos_paths_ignore_cwd(tmp_path, monkeypatch):
    from app import paths, platforms
    contents = tmp_path / '中文 App.app' / 'Contents'
    (contents / 'MacOS').mkdir(parents=True)
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(contents / 'MacOS/CodeTop'))
    monkeypatch.setattr(paths.Path, 'home', lambda: tmp_path / '用户')
    monkeypatch.delenv('CODETOP_DATA_DIR', raising=False)
    monkeypatch.chdir(tmp_path)
    assert paths.application_root() == contents / 'Resources'
    assert paths.native_python() == contents / 'Resources/python/bin/python3'
    assert paths.default_data_dir() == tmp_path / '用户/Library/Application Support/CodeTopLocal'
    monkeypatch.setenv('CODETOP_DATA_DIR', str(tmp_path / 'override'))
    assert paths.default_data_dir() == tmp_path / 'override'


def test_source_paths_remain_project_local(monkeypatch):
    from app import paths, platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.delenv('CODETOP_DATA_DIR', raising=False)
    assert paths.default_data_dir() == paths.application_root() / 'data'


@pytest.mark.parametrize('relative', ['../escape', '/absolute', 'bin/../../escape'])
def test_runtime_rejects_invalid_executable(tmp_path, monkeypatch, relative):
    from app import paths, platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths, 'application_root', lambda: tmp_path)
    (tmp_path / 'runtime-lock.json').write_text(json.dumps({'executable': relative, 'files': {relative: 'a' * 64}}))
    with pytest.raises(ValueError, match='校验'):
        paths.verify_bundled_runtime()


def test_macos_runtime_hash_and_executable(tmp_path, monkeypatch):
    from app import paths, platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(paths, 'application_root', lambda: tmp_path)
    python = tmp_path / 'python/bin/python3'
    python.parent.mkdir(parents=True)
    python.write_bytes(b'portable-python')
    manifest = {'executable': 'bin/python3', 'files': {'bin/python3': hashlib.sha256(python.read_bytes()).hexdigest()}}
    (tmp_path / 'runtime-lock.json').write_text(json.dumps(manifest))
    paths.verify_bundled_runtime()
    python.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='校验'):
        paths.verify_bundled_runtime()


def test_platform_start_options_and_architecture(monkeypatch):
    from app import platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    assert platforms.background_options() == {'start_new_session': True}
    monkeypatch.setattr(platforms.platform, 'machine', lambda: 'AMD64')
    assert platforms.architecture() == 'x86_64'
    monkeypatch.setattr(platforms.platform, 'machine', lambda: 'aarch64')
    assert platforms.architecture() == 'arm64'
