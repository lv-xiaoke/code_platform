"""Release contracts: usable seed/build, no personal files, no overwrites."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_health_declares_utf8_for_windows_powershell_paths(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app
    root = tmp_path / '中文安装 with spaces'
    app = create_app(root=root, data_dir=root / 'data', bootstrap=False)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        response = client.get('/api/v1/health')
        assert 'charset=utf-8' in response.headers['content-type'].lower()
        assert response.json()['root'] == str(root.resolve())


def test_seed_is_not_ignored_by_git():
    if not (ROOT / '.git').exists() or not shutil.which('git'):
        pytest.skip('Git checkout required; source ZIPs have no ignore metadata')
    result = subprocess.run(
        ['git', 'check-ignore', '--no-index', '-q', 'vendor/algoTop-main/public/data/codetop.json'],
        cwd=ROOT, capture_output=True,
    )
    assert result.returncode == 1, 'Fresh clones must include the built-in catalog snapshot'


@pytest.fixture
def packager():
    path = ROOT / 'scripts/package_release.py'
    assert path.is_file(), 'The release packager must exist'
    spec = importlib.util.spec_from_file_location('package_release', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path):
    root = tmp_path / '源代码 with spaces'
    files = {
        'README.md': '# CodeTop', 'THIRD_PARTY_NOTICES.md': 'Attribution',
        'Start-CodeTop.cmd': '@echo off', 'Setup-CodeTop.cmd': '@echo off',
        'scripts/common.ps1': '# common', 'scripts/start.ps1': '# start',
        'scripts/setup.ps1': '# setup', 'scripts/stop.ps1': '# stop',
        'scripts/backup.ps1': '# backup', 'scripts/restore.ps1': '# restore',
        'scripts/setup-runner.ps1': '# runner',
        'backend/app/__init__.py': "__version__ = '1.5.0'",
        'backend/migrations/env.py': '# migration',
        'backend/runner/runtime.json': '{}', 'backend/runner/worker.py': '# worker',
        'backend/requirements.lock.txt': 'fastapi==0.156.4',
        'backend/reference_pack/manifest.json': '{}',
        'vendor/algoTop-main/LICENSE': 'MIT',
        'vendor/algoTop-main/public/data/codetop.json': '{"questions":{}}',
        'frontend/LICENSE': 'MIT',
        'docs/deployment.md': '# Deploy', 'docs/user-guide.md': '# Guide',
        'releases/current.json': json.dumps({'path': 'releases/test-build', 'version': '1.5.0'}),
        'releases/test-build/index.html': '<html>CodeTop</html>',
        'releases/test-build/assets/app.js': 'console.log(1)',
        'releases/old/index.html': 'old build',
        'data/study.sqlite3': 'PRIVATE', 'data/ai-key.dpapi': 'SECRET',
        'runtime/server.log': 'PRIVATE', 'backend/.venv/secret.py': 'PRIVATE',
        'frontend/.env': 'SECRET', 'tools/node_modules/private.js': 'PRIVATE',
        'releases/test-build/.env': 'SECRET',
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    return root


def test_package_contains_seed_current_assets_and_no_personal_files(packager, source, tmp_path):
    target = tmp_path / 'release.zip'
    packager.create_package(source, target)
    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        assert 'CodeTop-Local/vendor/algoTop-main/public/data/codetop.json' in names
        assert 'CodeTop-Local/backend/runner/worker.py' in names
        assert 'CodeTop-Local/releases/test-build/assets/app.js' in names
        assert 'CodeTop-Local/Setup-CodeTop.cmd' in names
        assert archive.read('CodeTop-Local/releases/current.json') == (source / 'releases/current.json').read_bytes()
        assert not any('PRIVATE' in archive.read(name).decode('utf-8') or 'SECRET' in archive.read(name).decode('utf-8') for name in names)
        assert not any('/old/' in name for name in names)


def test_missing_seed_aborts_before_creating_archive(packager, source, tmp_path):
    (source / 'vendor/algoTop-main/public/data/codetop.json').unlink()
    target = tmp_path / 'release.zip'
    with pytest.raises(ValueError, match='codetop.json'):
        packager.create_package(source, target)
    assert not target.exists()


@pytest.mark.parametrize('release', ['../private', 'backend', '/private', 'releases/../backend'])
def test_release_manifest_cannot_escape_release_directory(packager, source, tmp_path, release):
    (source / 'releases/current.json').write_text(json.dumps({'path': release}), encoding='utf-8')
    with pytest.raises(ValueError, match='release'):
        packager.create_package(source, tmp_path / 'release.zip')


def test_existing_archive_is_never_overwritten(packager, source, tmp_path):
    target = tmp_path / 'release.zip'
    target.write_bytes(b'existing release')
    with pytest.raises(FileExistsError):
        packager.create_package(source, target)
    assert target.read_bytes() == b'existing release'
