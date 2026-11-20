import importlib.util
import json
from pathlib import Path
import zipfile
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def release_source(tmp_path):
    root = tmp_path / 'source'
    # A fresh clone has no ignored releases/current.json. Exercise real assets
    # against a controlled built-page fixture rather than a developer's release.
    files = set(module('package_release').REQUIRED) - {'releases/current.json'}
    files.update(('backend/migrations/versions/0004_multilanguage.py',
                  'backend/app/runner/toolchains/registry.py'))
    for relative in files:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative, content in [('releases/current.json', '{"path":"releases/test-build"}'),
            ('releases/test-build/index.html', '<html>isolated fixture</html>'),
            ('releases/test-build/assets/app.js', 'console.log("fixture")'),
            ('runtime/private.txt', 'PRIVATE'), ('data/private.txt', 'PRIVATE')]:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding='utf-8')
    return root


def test_desktop_assets_include_language_manifest_but_no_environment(tmp_path, release_source):
    module('desktop_assets').copy_assets(release_source, tmp_path / 'assets')
    assert json.loads((tmp_path / 'assets/packaging/toolchains.json').read_text())['artifacts']
    assert (tmp_path / 'assets/backend/migrations/versions/0004_multilanguage.py').is_file()
    assert not (tmp_path / 'assets/runtime').exists()
    assert not (tmp_path / 'assets/data').exists()


def test_source_distribution_has_language_assets_and_no_cached_tools(tmp_path, release_source):
    path = module('package_release').create_package(release_source, tmp_path / 'source.zip')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert 'CodeTop-Local/packaging/toolchains.json' in names
        assert 'CodeTop-Local/backend/app/runner/toolchains/registry.py' in names
        assert not any('/runtime/' in name or '/toolchains-ci/' in name for name in names)
