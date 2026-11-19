"""Assemble Mac apps on macOS; never overwrite or clean existing outputs."""
import argparse
import ast
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import desktop_assets

RUNTIME_VERSION = '3.12.13'
PYINSTALLER_VERSION = '6.22.3'
MACHO_MAGIC = {b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
               b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_architecture(actual, expected):
    if actual != expected:
        raise ValueError(f'Runtime architecture mismatch: {actual}, expected {expected}')


def package_name(version, arch, signed):
    return f'CodeTop-{version}-macos-{arch}' + ('' if signed else '-unsigned') + '.dmg'


def validate_runtime_link(path, root):
    if not path.resolve(strict=True).is_relative_to(root.resolve()):
        raise ValueError(f'Runtime link outside source root: {path}')


def runtime_files(runtime):
    result = {}
    for path in sorted(runtime.rglob('*')):
        if '__pycache__' in path.relative_to(runtime).parts or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            validate_runtime_link(path, runtime)
        if path.is_file():
            result[path.relative_to(runtime).as_posix()] = digest(path)
    return result


def write_runtime_manifest(runtime, target, arch):
    value = {'python_version': RUNTIME_VERSION, 'platform': 'macos', 'architecture': arch,
             'executable': 'bin/python3', 'files': runtime_files(runtime)}
    if 'bin/python3' not in value['files']:
        raise ValueError('Runtime interpreter missing')
    target.write_text(json.dumps(value, indent=2), encoding='utf-8')


def copy_runtime(source, target):
    for path in source.rglob('*'):
        if path.is_symlink():
            validate_runtime_link(path, source)
    # New destination only; preserve internal relative links and executable bits.
    shutil.copytree(source, target, symlinks=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'site-packages', 'test', 'tests', 'idlelib', 'tkinter'))
    runtime_files(target)  # catch links to excluded targets before publishing


def macho_files(app):
    seen = set()
    for path in sorted(app.rglob('*')):
        if path.is_file() and not path.is_symlink():
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            with path.open('rb') as stream:
                if stream.read(4) in MACHO_MAGIC:
                    yield path


def run(argv, **kwargs):
    return subprocess.run([str(v) for v in argv], check=True, **kwargs)


def expand_loader_path(value, binary, executable):
    for token, base in (('@loader_path', binary.parent), ('@executable_path', executable.parent)):
        if value == token or value.startswith(token + '/'):
            return (base / value[len(token):].lstrip('/')).resolve()
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    raise ValueError(f'Unsupported relative dependency path: {value}')


def is_system_path(path):
    return str(path).startswith(('/usr/lib/', '/System/Library/'))


def resolve_library(library, binary, app, executable, rpaths):
    if library.startswith(('/usr/lib/', '/System/Library/')):
        return Path(library)  # modern macOS may store this solely in the dyld cache
    if library.startswith('@rpath/'):
        candidates = [path / library[len('@rpath/'):] for path in rpaths]
    else:
        candidates = [expand_loader_path(library, binary, executable)]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_relative_to(app.resolve()) and resolved.is_file():
            return resolved
        if is_system_path(resolved):
            return resolved
    raise ValueError(f'Missing or external dependency: {binary}: {library}')


def audit_binaries(app, arch, deployment_target):
    evidence = []
    binaries = list(macho_files(app))
    loads = {path.resolve(): run(['/usr/bin/otool', '-l', path], capture_output=True, text=True).stdout for path in binaries}
    for path in binaries:
        arches = run(['/usr/bin/lipo', '-archs', path], capture_output=True, text=True).stdout.split()
        if arch not in arches:
            raise ValueError(f'Mach-O architecture mismatch: {path}')
        load = loads[path.resolve()]
        minimums = re.findall(r'\bminos\s+(\d+(?:\.\d+)+)', load)
        minimums += re.findall(r'cmd LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version (\d+(?:\.\d+)+)', load)
        for value in minimums:
            if tuple(map(int, value.split('.')[:2])) > tuple(map(int, deployment_target.split('.')[:2])):
                raise ValueError(f'{path} requires macOS {value}, above build target {deployment_target}')
        links = run(['/usr/bin/otool', '-L', path], capture_output=True, text=True).stdout.splitlines()[1:]
        runtime = app / 'Contents/Resources/python'
        executable = runtime / 'bin/python3' if path.resolve().is_relative_to(runtime.resolve()) else app / 'Contents/MacOS/CodeTop'
        rpaths = []
        for owner in (path, executable):
            commands = loads.get(owner.resolve(), '')
            for value in re.findall(r'cmd LC_RPATH\s+cmdsize \d+\s+path (.*?) \(offset', commands):
                resolved = expand_loader_path(value, owner, executable)
                if not resolved.is_relative_to(app.resolve()) and not is_system_path(resolved):
                    raise ValueError(f'External dependency search path: {owner}: {value}')
                rpaths.append(resolved)
        for line in links:
            library = line.strip().split(' (', 1)[0]
            resolve_library(library, path, app, executable, rpaths)
        evidence.append({'path': path.relative_to(app).as_posix(), 'architectures': arches, 'minos': minimums})
    return evidence


def sign_app(app, identity, arch):
    options = ['--options', 'runtime', '--timestamp'] if identity != '-' else []
    for path in sorted(macho_files(app), key=lambda p: len(p.parts), reverse=True):
        run(['/usr/bin/codesign', '--force', '--sign', identity, *options, path])
    # Framework and nested bundle seals must be regenerated after their binaries.
    bundles = [p for p in app.rglob('*') if p.is_dir() and not p.is_symlink() and p.suffix in ('.framework', '.app', '.bundle')]
    for path in sorted(bundles, key=lambda p: len(p.parts), reverse=True):
        run(['/usr/bin/codesign', '--force', '--sign', identity, *options, path])
    resources = app / 'Contents/Resources'
    write_runtime_manifest(resources / 'python', resources / 'runtime-lock.json', arch)
    run(['/usr/bin/codesign', '--force', '--sign', identity, *options,
         '--entitlements', ROOT / 'packaging/macos-entitlements.plist', app])
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', app])


def notarize(path, profile):
    result = run(['/usr/bin/xcrun', 'notarytool', 'submit', path, '--keychain-profile', profile,
                  '--wait', '--output-format', 'json'], capture_output=True, text=True)
    if json.loads(result.stdout).get('status') != 'Accepted':
        raise ValueError('Apple notarization did not accept the package')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python-root', type=Path, required=True)
    parser.add_argument('--arch', choices=['arm64', 'x86_64'], required=True)
    parser.add_argument('--identity')
    parser.add_argument('--notary-profile')
    parser.add_argument('--deployment-target', default='13.0')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Mac application builds require a macOS host')
    if bool(args.identity) != bool(args.notary_profile):
        parser.error('Formal packages require both --identity and --notary-profile')
    if args.identity == '-':
        parser.error('Omit signing options for an unsigned test build')
    if sys.version.split()[0] != RUNTIME_VERSION or importlib.metadata.version('pyinstaller') != PYINSTALLER_VERSION:
        raise ValueError('Build Python/PyInstaller version mismatch')
    check_architecture(platform.machine(), args.arch)
    source = args.python_root.resolve()
    pinned = json.loads((ROOT / 'packaging/macos-python-sources.json').read_text())[args.arch]
    receipt = json.loads((source.parent / 'source-lock.json').read_text())
    if receipt.get('source') != pinned or receipt.get('files') != runtime_files(source):
        raise ValueError('Runtime input does not match the pinned download receipt; use fetch_macos_python.py')
    interpreter = source / 'bin/python3'
    probe = run([interpreter, '-I', '-S', '-B', '-c', 'import platform,sys,json; print(json.dumps([platform.machine(),platform.python_version()]))'],
                capture_output=True, text=True)
    architecture, version = json.loads(probe.stdout)
    check_architecture(architecture, args.arch)
    if version != RUNTIME_VERSION:
        raise ValueError('Standalone Python version mismatch')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8]
    build, output = ROOT / 'runtime' / ('macos-build-' + stamp), ROOT / 'dist' / ('macos-' + stamp)
    build.mkdir(parents=True)
    output.mkdir(parents=True)
    (build / 'input-runtime-lock.json').write_text(json.dumps({'architecture': args.arch, 'files': runtime_files(source)}, indent=2))
    env = os.environ.copy()
    env['MACOSX_DEPLOYMENT_TARGET'] = args.deployment_target
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', build / 'frozen',
         '--workpath', build / 'work', ROOT / 'packaging/macos.spec'], cwd=ROOT, env=env)
    app = build / 'frozen/CodeTop.app'
    resources = app / 'Contents/Resources'
    copy_runtime(source, resources / 'python')
    desktop_assets.copy_assets(ROOT, resources)
    desktop_assets.copy_licenses(ROOT, resources)
    binaries = audit_binaries(app, args.arch, args.deployment_target)
    sign_app(app, args.identity or '-', args.arch)
    minimal_env = {'PATH': str(resources / 'python/bin'), 'TMPDIR': str(build)}
    run([resources / 'python/bin/python3', '-I', '-S', '-B', '-c',
         'import encodings,ssl,sqlite3,ctypes,subprocess; print("portable Python OK")'], cwd=build, env=minimal_env)
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', app])
    if args.identity:
        archive = build / 'CodeTop-notarization.zip'
        run(['/usr/bin/ditto', '-c', '-k', '--keepParent', app, archive])
        notarize(archive, args.notary_profile)
        run(['/usr/bin/xcrun', 'stapler', 'staple', app])
    staging = build / 'dmg'
    staging.mkdir()
    run(['/usr/bin/ditto', app, staging / 'CodeTop.app'])
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', staging / 'CodeTop.app'])
    (staging / 'Applications').symlink_to('/Applications')
    version_module = ast.parse((ROOT / 'backend/app/__init__.py').read_text(encoding='utf-8-sig'))
    app_version = next(ast.literal_eval(s.value) for s in version_module.body if isinstance(s, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == '__version__' for t in s.targets))
    dmg = output / package_name(app_version, args.arch, bool(args.identity))
    run(['/usr/bin/hdiutil', 'create', '-volname', 'CodeTop', '-srcfolder', staging, '-format', 'UDZO', dmg])
    if args.identity:
        run(['/usr/bin/codesign', '--sign', args.identity, '--timestamp', dmg])
        notarize(dmg, args.notary_profile)
        run(['/usr/bin/xcrun', 'stapler', 'staple', dmg])
        run(['/usr/sbin/spctl', '--assess', '--type', 'execute', app])
    dmg.with_suffix('.dmg.sha256').write_text(digest(dmg) + '  ' + dmg.name + '\n', encoding='ascii')
    result = {'app': str(app), 'dmg': str(dmg), 'architecture': args.arch, 'signed_and_notarized': bool(args.identity),
              'build_deployment_target': args.deployment_target, 'minimum_os_verified': False, 'binaries': binaries}
    report = output / 'build-report.json'
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('APP:', app)
    print('DMG:', dmg)
    print('REPORT:', report)


if __name__ == '__main__':
    main()
