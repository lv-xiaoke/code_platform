"""Build-time only: resolve official assets to an immutable, reviewable manifest."""
import argparse
import json
from pathlib import Path
import urllib.request
from urllib.parse import quote


def read(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'CodeTop-toolchain-lock'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def build_manifest():
    artifacts = []
    node_version = next(item['version'] for item in json.loads(read('https://nodejs.org/dist/index.json')) if item['version'].startswith('v24.'))
    checksums = dict(line.split()[::-1] for line in read(f'https://nodejs.org/dist/{node_version}/SHASUMS256.txt').decode().splitlines())
    for os_name, arch, suffix, executable in [
        ('windows', 'x86_64', 'win-x64.zip', 'node.exe'),
        ('macos', 'arm64', 'darwin-arm64.tar.gz', 'bin/node'),
        ('macos', 'x86_64', 'darwin-x64.tar.gz', 'bin/node')]:
        name = f'node-{node_version}-{suffix}'
        artifacts.append(dict(id=f'node-{node_version}-{os_name}-{arch}', languages=['javascript'],
            os=os_name, arch=arch, version=node_version[1:], url=f'https://nodejs.org/dist/{node_version}/{name}',
            sha256=checksums[name], archive='zip' if os_name == 'windows' else 'tar.gz',
            root=name.removesuffix('.zip').removesuffix('.tar.gz'), executables={'node': executable},
            license='MIT and bundled third-party licenses (LICENSE in distribution)'))
    for os_name, provider_os, arch, provider_arch in [
        ('windows', 'windows', 'x86_64', 'x64'), ('macos', 'mac', 'arm64', 'aarch64'), ('macos', 'mac', 'x86_64', 'x64')]:
        assets = json.loads(read(f'https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture={provider_arch}&image_type=jdk&os={provider_os}&vendor=eclipse'))
        asset = assets[0]
        package = asset['binary']['package']
        release = asset['release_name']
        is_mac = os_name == 'macos'
        exe_prefix = 'Contents/Home/bin/' if is_mac else 'bin/'
        artifacts.append(dict(id=f'temurin-{release}-{os_name}-{arch}', languages=['java'], os=os_name, arch=arch,
            version=release.removeprefix('jdk-'), url=package['link'], sha256=package['checksum'],
            archive='tar.gz' if is_mac else 'zip', root=release,
            executables={key: exe_prefix + key + ('' if is_mac else '.exe') for key in ('javac', 'java')},
            license='GPL-2.0 with Classpath Exception (legal/ in distribution)'))
    release = json.loads(read('https://api.github.com/repos/mstorsjo/llvm-mingw/releases/latest'))
    asset = next(a for a in release['assets'] if a['name'].endswith('-ucrt-x86_64.zip'))
    checksum = asset.get('digest', '').removeprefix('sha256:')
    if len(checksum) != 64:
        sums = next(a for a in release['assets'] if 'sha256' in a['name'].lower())
        lines = read(sums['browser_download_url']).decode().splitlines()
        checksum = next(line.split()[0] for line in lines if asset['name'] in line)
    artifacts.append(dict(id=f'llvm-mingw-{release["tag_name"]}-windows-x86_64', languages=['c', 'cpp'],
        os='windows', arch='x86_64', version=release['tag_name'], url=asset['browser_download_url'],
        sha256=checksum, archive='zip', root=asset['name'].removesuffix('.zip'),
        executables={'cc': 'bin/clang.exe', 'cxx': 'bin/clang++.exe'},
        license='Apache-2.0 WITH LLVM-exception, mingw-w64 and bundled licenses'))
    return dict(schema=1, artifacts=artifacts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for item in manifest['artifacts']:
        print(item['id'], item['sha256'])
