import hashlib
import io
import json
import tarfile
import time
import zipfile

import pytest


def test_archive_rejects_escape_and_links_before_writing(tmp_path):
    from app.runner.toolchains.archive import extract_archive
    for name in ('../escape', '/absolute', 'C:/escape', 'root/../../escape'):
        archive = tmp_path / (hashlib.sha256(name.encode()).hexdigest() + '.zip')
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr(name, 'bad')
        with pytest.raises(ValueError):
            extract_archive(archive, tmp_path / archive.stem, 'zip')
    archive = tmp_path / 'link.tar.gz'
    with tarfile.open(archive, 'w:gz') as bundle:
        link = tarfile.TarInfo('root/link')
        link.type, link.linkname = tarfile.SYMTYPE, '../../escape'
        bundle.addfile(link)
    with pytest.raises(ValueError):
        extract_archive(archive, tmp_path / 'link', 'tar.gz')
    assert not (tmp_path / 'escape').exists()


def test_internal_symlink_survives_safe_extraction(tmp_path):
    import os
    from app.runner.toolchains.archive import extract_archive
    if os.name == 'nt':
        pytest.skip('internal symlinks are needed by macOS tar distributions')
    archive = tmp_path / 'ok.tar.gz'
    with tarfile.open(archive, 'w:gz') as bundle:
        member = tarfile.TarInfo('root/real')
        member.size = 2
        bundle.addfile(member, io.BytesIO(b'ok'))
        link = tarfile.TarInfo('root/link')
        link.type, link.linkname = tarfile.SYMTYPE, 'real'
        bundle.addfile(link)
    extract_archive(archive, tmp_path / 'out', 'tar.gz')
    assert (tmp_path / 'out/root/link').read_bytes() == b'ok'


def test_selection_never_downloads_and_manifest_rejects_mutable_sources(tmp_path):
    from app.runner.toolchains.registry import ToolchainRegistry
    registry = ToolchainRegistry(tmp_path, 'packaging/toolchains.json')
    try:
        assert registry.capability('javascript')['state'] == 'unprepared'
        assert list(tmp_path.iterdir()) == []
    finally:
        registry.close()
    from app.runner.toolchains.manifest import load_manifest
    invalid = tmp_path / 'bad.json'
    invalid.write_text(json.dumps({'schema': 1, 'artifacts': [{'url': 'https://example.com/latest', 'sha256': ''}]}))
    with pytest.raises(ValueError):
        load_manifest(invalid)


def test_hash_failure_does_not_publish_and_can_retry(tmp_path, monkeypatch):
    from app.runner.toolchains.registry import ToolchainRegistry
    from app.runner.toolchains import archive
    def bad_download(url, path, sha256, stop_event):
        path.write_bytes(b'bad')
        raise ValueError('SHA-256 mismatch')
    monkeypatch.setattr(archive, 'download_archive', bad_download)
    registry = ToolchainRegistry(tmp_path / 'tools', 'packaging/toolchains.json')
    try:
        first = registry.prepare('javascript')
        deadline = time.monotonic() + 3
        while registry.capability('javascript')['state'] not in ('failed', 'ready') and time.monotonic() < deadline:
            time.sleep(.01)
        result = registry.capability('javascript')
        assert result['state'] == 'failed'
        assert 'SHA-256' in result['error']
        assert not list((tmp_path / 'tools').glob('ready-*.json'))
        second = registry.prepare('javascript')
        assert second['job_id'] != first['job_id']
    finally:
        registry.close()


def test_c_and_cpp_share_prepare_and_cancel(tmp_path, monkeypatch):
    import threading
    from app.runner.toolchains import archive
    from app.runner.toolchains.registry import ToolchainRegistry
    started = threading.Event()
    def waiting(url, path, sha256, stop_event):
        started.set()
        assert stop_event.wait(3)
        raise InterruptedError('cancelled')
    monkeypatch.setattr(archive, 'download_archive', waiting)
    registry = ToolchainRegistry(tmp_path, 'packaging/toolchains.json')
    try:
        # This downloadable C/C++ preparation path is Windows-specific.
        from app import platforms
        monkeypatch.setattr(platforms, 'system_name', lambda: 'windows')
        monkeypatch.setattr(platforms, 'architecture', lambda: 'x86_64')
        first = registry.prepare('c')
        assert started.wait(2)
        assert registry.prepare('cpp')['job_id'] == first['job_id']
        registry.cancel('cpp')
    finally:
        registry.close()
    assert registry.capability('c')['state'] == 'failed'


def test_missing_macos_clt_never_calls_compiler_stub(tmp_path, monkeypatch):
    from app import platforms
    from app.runner.toolchains import registry as module
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(platforms, 'architecture', lambda: 'arm64')
    def missing(argv, env=None):
        assert argv == ['/usr/bin/xcode-select', '-p']
        raise ValueError('missing CLT')
    monkeypatch.setattr(module, 'probe_output', missing)
    registry = module.ToolchainRegistry(tmp_path, 'packaging/toolchains.json')
    try:
        assert registry.capability('cpp')['state'] == 'needs_system_tool'
        assert registry.capability('java')['state'] == 'unprepared'
        assert list(tmp_path.iterdir()) == []
    finally:
        registry.close()


def test_publication_retries_transient_windows_directory_lock(tmp_path, monkeypatch):
    from pathlib import Path
    import threading
    from app.runner.toolchains.registry import publish_directory
    source, target = tmp_path / 'content', tmp_path / 'ready'
    source.mkdir()
    (source / 'runtime').write_bytes(b'verified')
    original, attempts = Path.rename, []
    def locked(path, destination):
        if path == source and len(attempts) < 2:
            attempts.append(path)
            raise PermissionError('scanner temporarily holds directory')
        return original(path, destination)
    monkeypatch.setattr(Path, 'rename', locked)
    publish_directory(source, target, threading.Event())
    assert (target / 'runtime').read_bytes() == b'verified'
