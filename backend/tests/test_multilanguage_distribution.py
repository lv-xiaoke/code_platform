import importlib.util
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_desktop_assets_include_language_manifest_but_no_environment(tmp_path):
    module('desktop_assets').copy_assets(ROOT, tmp_path / 'assets')
    assert json.loads((tmp_path / 'assets/packaging/toolchains.json').read_text())['artifacts']
    assert (tmp_path / 'assets/backend/migrations/versions/0004_multilanguage.py').is_file()
    assert not (tmp_path / 'assets/runtime').exists()
    assert not (tmp_path / 'assets/data').exists()


def test_source_distribution_has_language_assets_and_no_cached_tools(tmp_path):
    path = module('package_release').create_package(ROOT, tmp_path / 'source.zip')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert 'CodeTop-Local/packaging/toolchains.json' in names
        assert 'CodeTop-Local/backend/app/runner/toolchains/registry.py' in names
        assert not any('/runtime/' in name or '/toolchains-ci/' in name for name in names)
