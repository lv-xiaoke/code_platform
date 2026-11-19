"""Fetch only a reviewed, hash-pinned standalone runtime into a new directory."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def source_files(root):
    files = {}
    for file in sorted(root.rglob('*')):
        if '__pycache__' in file.relative_to(root).parts or file.suffix == '.pyc':
            continue
        if file.is_file():
            with file.open('rb') as stream:
                files[file.relative_to(root).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return files


def fetch_runtime(arch):
    lock = json.loads((ROOT / 'packaging/macos-python-sources.json').read_text())
    source = lock[arch]
    target = ROOT / 'runtime' / ('macos-python-' + arch + '-' + uuid4().hex[:8])
    target.mkdir(parents=True)
    archive = target / 'python.tar.gz'
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'CodeTop-build'})
    with urllib.request.urlopen(request, timeout=120) as response, archive.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != source['sha256']:
        raise ValueError('Standalone Python SHA-256 mismatch; archive retained for inspection')
    with tarfile.open(archive) as bundle:
        # The data filter rejects paths, hardlinks and symlinks escaping target.
        bundle.extractall(target, filter='data')
    python_root = target / 'python'
    if not (python_root / 'bin/python3').is_file():
        raise ValueError('Pinned Python archive layout mismatch')
    (target / 'source-lock.json').write_text(json.dumps({'source': source, 'files': source_files(python_root)}, indent=2), encoding='utf-8')
    return python_root.resolve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--arch', choices=['arm64', 'x86_64'], required=True)
    print(fetch_runtime(parser.parse_args().arch))
