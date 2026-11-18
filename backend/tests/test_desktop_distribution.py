import importlib.util
import json
from pathlib import Path

import pytest


def assembler():
    path = Path(__file__).resolve().parents[2] / 'scripts/build_desktop.py'
    spec = importlib.util.spec_from_file_location('desktop_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_desktop_assets_exclude_personal_files_and_old_builds(tmp_path, monkeypatch):
    module = assembler()
    source, target = tmp_path / 'source', tmp_path / 'output'
    files = {
        'README.md': 'readme', 'THIRD_PARTY_NOTICES.md': 'notices',
        'docs/deployment.md': 'deploy', 'docs/user-guide.md': 'guide',
        'frontend/LICENSE': 'MIT', 'vendor/algoTop-main/LICENSE': 'MIT',
        'vendor/algoTop-main/public/data/codetop.json': '{}',
        'backend/migrations/env.py': '# migration',
        'backend/runner/runtime.json': '{}',
        'releases/current.json': json.dumps({'path': 'releases/current-build'}),
        'releases/current-build/index.html': '<html>ok</html>',
        'releases/current-build/assets/app.js': 'ok',
        'releases/old/index.html': 'PRIVATE', 'data/study.sqlite3': 'PRIVATE',
        'data/native-consent.json': 'PRIVATE', 'data/ai-key.dpapi': 'PRIVATE',
        'frontend/.env': 'PRIVATE', 'runtime/secret.txt': 'PRIVATE',
        'backend/.venv/private.py': 'PRIVATE',
    }
    for relative, content in files.items():
        file = source / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding='utf-8')
    monkeypatch.setattr(module, 'ROOT', source)
    module.copy_assets(target)
    assert (target / 'vendor/algoTop-main/public/data/codetop.json').is_file()
    assert (target / 'backend/migrations/env.py').is_file()
    assert (target / 'releases/current-build/assets/app.js').read_text() == 'ok'
    assert not (target / 'data').exists()
    assert not (target / 'runtime').exists()
    assert not any('PRIVATE' in p.read_text() for p in target.rglob('*') if p.is_file())
    (source / 'releases/current.json').write_text(json.dumps({'path': 'backend'}))
    with pytest.raises(ValueError, match='frontend'):
        module.copy_assets(tmp_path / 'invalid')
