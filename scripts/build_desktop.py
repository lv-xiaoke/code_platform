"""Reproducible-input desktop assembly into fresh directories. Never clean output."""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_VERSION = '3.12.13'
PYINSTALLER_VERSION = '6.22.3'
INNO_SHA256 = '8a5a6711c3766a6e5fb74f280ba0e3551e719ce94538d901fdbd1f8f9920b3f0'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def copy_file(source, dest):
    if source.is_symlink() or source.is_junction():
        raise ValueError(f'Linked build input: {source}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def copy_runtime(source, dest):
    for path in source.rglob('*'):
        relative = path.relative_to(source)
        if path.is_dir():
            continue
        if any(p.lower() in ('site-packages', '__pycache__', 'test', 'tests', 'ensurepip', 'idlelib', 'tkinter', 'turtledemo') for p in relative.parts):
            continue
        if len(relative.parts) == 1:
            keep = path.suffix.lower() in ('.exe', '.dll') or path.name == 'LICENSE.txt'
        else:
            keep = relative.parts[0] in ('Lib', 'DLLs') and path.suffix.lower() in ('.py', '.pyd', '.dll', '.pem', '.txt', '.json')
        if keep:
            copy_file(path, dest / relative)


def copy_assets(stage):
    patterns = ('backend/migrations/**/*.py', 'backend/migrations/**/*.sql', 'backend/runner/*.py',
                'backend/runner/runtime.json', 'backend/reference_pack/*.py', 'backend/reference_pack/*.json',
                'docs/*.png', 'docs/*.jpg')
    files = set()
    for pattern in patterns:
        files.update(ROOT.glob(pattern))
    for relative in ('README.md', 'THIRD_PARTY_NOTICES.md', 'docs/deployment.md', 'docs/user-guide.md',
                     'frontend/LICENSE', 'vendor/algoTop-main/LICENSE', 'vendor/algoTop-main/public/data/codetop.json'):
        files.add(ROOT / relative)
    marker = ROOT / 'releases/current.json'
    relative = json.loads(marker.read_text(encoding='utf-8-sig'))['path']
    build = (ROOT / relative).resolve()
    if not build.is_relative_to(ROOT / 'releases') or not (build / 'index.html').is_file():
        raise ValueError('Invalid frontend release')
    files.add(marker)
    files.update(p for p in build.rglob('*') if p.is_file() and (p.name == 'index.html' or 'assets' in p.relative_to(build).parts))
    for path in files:
        copy_file(path, stage / path.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-installer', action='store_true')
    args = parser.parse_args()
    if sys.version.split()[0] != RUNTIME_VERSION or importlib.metadata.version('pyinstaller') != PYINSTALLER_VERSION:
        raise ValueError('Desktop build tool/runtime version mismatch')
    build = ROOT / 'runtime' / ('desktop-build-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:6])
    build.mkdir(parents=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(build / 'frozen'),
                    '--workpath', str(build / 'work'), str(ROOT / 'packaging/desktop.spec')], cwd=ROOT, check=True)
    stage = build / 'frozen' / 'CodeTop'
    python_source = Path(sys._base_executable).parent
    copy_runtime(python_source, stage / 'python')
    copy_assets(stage)
    license_dir = stage / 'licenses'
    for distribution in importlib.metadata.distributions():
        for file in distribution.files or []:
            if file.name.lower().startswith(('license', 'copying', 'notice')):
                original = Path(distribution.locate_file(file))
                if original.is_file():
                    copy_file(original, license_dir / distribution.metadata['Name'] / file.name)
    frontend_modules = ROOT / 'frontend/node_modules'
    for manifest in frontend_modules.glob('**/package.json'):
        if 'node_modules' in manifest.parent.relative_to(frontend_modules).parts[1:]:
            continue
        for file in manifest.parent.glob('*'):
            if file.is_file() and file.name.lower().startswith(('license', 'copying', 'notice')):
                relative = manifest.parent.relative_to(frontend_modules)
                # Bun may use linked packages; dereference only this explicit license file.
                copy_file(file.resolve(), license_dir / 'frontend' / relative / file.name)
    hashes = {p.relative_to(stage / 'python').as_posix(): digest(p) for p in (stage / 'python').rglob('*') if p.is_file()}
    lock = {'python_version': RUNTIME_VERSION, 'python_source': 'https://github.com/astral-sh/python-build-standalone',
            'pyinstaller': PYINSTALLER_VERSION, 'inno': '7.1.1', 'inno_sha256': INNO_SHA256,
            'files': hashes}
    lock_file = ROOT / 'packaging/runtime-lock.json'
    if lock_file.exists():
        previous = json.loads(lock_file.read_text())
        if previous != lock:
            raise ValueError('Runtime/tool lock changed; review input change before rebuilding')
    else:
        lock_file.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    shutil.copy2(lock_file, stage / 'runtime-lock.json')
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('PYTHON', 'CODETOP'))}
    env['PATH'] = str(stage / 'python')
    subprocess.run([str(stage / 'python/python.exe'), '-I', '-S', '-X', 'utf8', '-c',
                    'import encodings,json,sqlite3,ssl,subprocess,threading,ctypes; print("portable Python OK")'],
                   cwd=build, env=env, check=True)
    (build / 'stage-path.txt').write_text(str(stage), encoding='utf-8')
    (ROOT / 'runtime/desktop-work/latest-stage.txt').write_text(str(stage), encoding='utf-8')
    manifest = {p.relative_to(stage).as_posix(): digest(p) for p in stage.rglob('*') if p.is_file()}
    (stage / 'distribution-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if not args.skip_installer:
        compiler = ROOT / 'runtime/desktop-work/inno/ISCC.exe'
        installer_source = ROOT / 'runtime/desktop-work/innosetup-7.1.1-x64.exe'
        if digest(installer_source) != INNO_SHA256:
            raise ValueError('Inno installer checksum mismatch')
        output = ROOT / 'dist' / ('desktop-' + uuid4().hex[:8])
        output.mkdir(parents=True)
        subprocess.run([str(compiler), '/DStageDir=' + str(stage), '/DOutputDir=' + str(output), str(ROOT / 'packaging/CodeTop.iss')], check=True)
        exe = output / 'CodeTop-Setup-1.6.0-windows-x64.exe'
        exe.with_suffix('.exe.sha256').write_text(digest(exe) + '  ' + exe.name + '\n', encoding='ascii')
        print('INSTALLER:', exe)
    print('STAGE:', stage)


if __name__ == '__main__':
    main()
