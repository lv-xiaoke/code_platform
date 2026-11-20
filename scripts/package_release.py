"""Build a Windows runtime ZIP from an allowlist; never copy user directories."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from uuid import uuid4
import zipfile

REQUIRED = (
    'README.md', 'THIRD_PARTY_NOTICES.md', 'Start-CodeTop.cmd', 'Setup-CodeTop.cmd',
    'scripts/common.ps1', 'scripts/setup.ps1', 'scripts/start.ps1', 'scripts/stop.ps1',
    'scripts/backup.ps1', 'scripts/restore.ps1', 'scripts/setup-runner.ps1',
    'backend/app/__init__.py', 'backend/requirements.lock.txt',
    'backend/migrations/env.py', 'backend/runner/runtime.json',
    'backend/reference_pack/manifest.json', 'frontend/LICENSE',
    'vendor/algoTop-main/LICENSE', 'vendor/algoTop-main/public/data/codetop.json',
    'docs/deployment.md', 'docs/user-guide.md', 'releases/current.json', 'packaging/toolchains.json',
)
PATTERNS = (
    'backend/app/**/*.py', 'backend/migrations/**/*.py', 'backend/migrations/**/*.sql',
    'backend/runner/*.py', 'backend/reference_pack/*.py', 'backend/reference_pack/*.json',
    'docs/*.png', 'docs/*.jpg',
)
ASSET_SUFFIXES = {'.js', '.css', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico', '.woff', '.woff2', '.ttf'}


def create_package(root, target):
    root, target = Path(root).resolve(), Path(target).absolute()
    if target.exists():
        raise FileExistsError(target)
    files = set()

    def include(relative):
        path = root / relative
        # Check every ancestor as well: a linked assets/ directory can leak files.
        if not path.is_file():
            raise ValueError(f'Missing or linked release input: {relative}')
        current = path
        while current != root:
            if current.is_symlink() or current.is_junction():
                raise ValueError(f'Linked release input: {relative}')
            current = current.parent
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'Unsafe release input: {relative}')
        files.add(path)

    for relative in REQUIRED:
        include(relative)
    manifest = json.loads((root / 'releases/current.json').read_text(encoding='utf-8-sig'))
    release = PurePosixPath(manifest['path'])
    if '\\' in manifest['path'] or len(release.parts) != 2 or release.parts[0] != 'releases' or release.parts[1] in ('.', '..'):
        raise ValueError('Invalid release path in current.json')
    include(str(release / 'index.html'))
    for pattern in PATTERNS:
        for path in root.glob(pattern):
            include(path.relative_to(root))
    for path in (root / str(release)).rglob('*'):
        relative = path.relative_to(root / str(release))
        if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES and (relative.parts[0] == 'assets' or relative.as_posix() == 'favicon.svg'):
            include(path.relative_to(root))
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, 'CodeTop-Local/' + path.relative_to(root).as_posix())
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target = args.root / 'dist' / f'CodeTop-Local-Windows-{stamp}-{uuid4().hex[:6]}.zip'
    create_package(args.root, target)
    with target.open('rb') as handle:
        checksum = hashlib.file_digest(handle, 'sha256').hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{checksum}  {target.name}\n', encoding='ascii')
    print(f'Release ZIP: {target}')
    print(f'SHA256: {checksum}')


if __name__ == '__main__':
    main()
