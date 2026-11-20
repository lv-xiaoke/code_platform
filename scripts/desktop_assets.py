"""Shared public assets and licenses; never include a user's data directory."""
import importlib.metadata
import json
from pathlib import Path
import shutil


def copy_file(source, dest):
    if source.is_symlink() or source.is_junction():
        raise ValueError(f'Linked build input: {source}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def copy_assets(root, stage):
    patterns = ('backend/migrations/**/*.py', 'backend/migrations/**/*.sql', 'backend/runner/*.py',
                'backend/runner/runtime.json', 'backend/reference_pack/*.py', 'backend/reference_pack/*.json',
                'docs/*.png', 'docs/*.jpg')
    files = set()
    for pattern in patterns:
        files.update(root.glob(pattern))
    for relative in ('README.md', 'THIRD_PARTY_NOTICES.md', 'docs/deployment.md', 'docs/user-guide.md', 'packaging/toolchains.json',
                     'frontend/LICENSE', 'vendor/algoTop-main/LICENSE', 'vendor/algoTop-main/public/data/codetop.json'):
        files.add(root / relative)
    marker = root / 'releases/current.json'
    relative = json.loads(marker.read_text(encoding='utf-8-sig'))['path']
    build = (root / relative).resolve()
    if not build.is_relative_to((root / 'releases').resolve()) or not (build / 'index.html').is_file():
        raise ValueError('Invalid frontend release')
    files.add(marker)
    files.update(p for p in build.rglob('*') if p.is_file() and (p.name == 'index.html' or 'assets' in p.relative_to(build).parts))
    for path in sorted(files):
        copy_file(path, stage / path.relative_to(root))


def copy_licenses(root, stage):
    license_dir = stage / 'licenses'
    for distribution in importlib.metadata.distributions():
        for file in distribution.files or []:
            if file.name.lower().startswith(('license', 'copying', 'notice')):
                original = Path(distribution.locate_file(file))
                if original.is_file():
                    copy_file(original.resolve(), license_dir / distribution.metadata['Name'] / file.name)
    modules = root / 'frontend/node_modules'
    for manifest in modules.glob('**/package.json'):
        if 'node_modules' in manifest.parent.relative_to(modules).parts[1:]:
            continue
        for file in manifest.parent.glob('*'):
            if file.is_file() and file.name.lower().startswith(('license', 'copying', 'notice')):
                copy_file(file.resolve(), license_dir / 'frontend' / manifest.parent.relative_to(modules) / file.name)
