"""Bounded extraction, including validated internal links in macOS JDK archives."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import urllib.request
import zipfile

MAX_DOWNLOAD = 1024 ** 3
MAX_EXTRACT = 4 * 1024 ** 3
MAX_MEMBERS = 100000


def download_archive(url, path, sha256, stop_event):
    request = urllib.request.Request(url, headers={'User-Agent': 'CodeTop-toolchains'})
    digest, count = hashlib.sha256(), 0
    with urllib.request.urlopen(request, timeout=30) as response, path.open('xb') as output:
        if int(response.headers.get('Content-Length', 0)) > MAX_DOWNLOAD:
            raise ValueError('工具链下载超过大小限制')
        while chunk := response.read(1024 * 1024):
            if stop_event.is_set(): raise InterruptedError('环境准备已取消')
            count += len(chunk)
            if count > MAX_DOWNLOAD: raise ValueError('工具链下载超过大小限制')
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != sha256:
        raise ValueError('工具链 SHA-256 校验失败；下载文件已保留')


def member_path(root, name):
    normalized = name.replace('\\', '/')
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or '..' in relative.parts or ':' in normalized or '\x00' in name:
        raise ValueError('工具链归档包含越界路径')
    target = root.joinpath(*relative.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('工具链归档包含越界路径')
    return target


def extract_archive(archive, root, kind, stop_event=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    seen, links, total = set(), [], 0
    with (zipfile.ZipFile(archive) if kind == 'zip' else tarfile.open(archive, 'r:gz')) as bundle:
        members = bundle.infolist() if kind == 'zip' else bundle.getmembers()
        if len(members) > MAX_MEMBERS: raise ValueError('工具链归档成员过多')
        # Validate the whole member list before writing any member.
        for item in members:
            name = item.filename if kind == 'zip' else item.name
            target = member_path(root, name)
            key = os.path.normcase(str(target))
            if key in seen: raise ValueError('工具链归档包含重复路径')
            seen.add(key)
            size = item.file_size if kind == 'zip' else item.size
            total += size
            if total > MAX_EXTRACT: raise ValueError('工具链解压超过大小限制')
            if kind == 'zip':
                if stat.S_ISLNK(item.external_attr >> 16): raise ValueError('Windows 归档不允许符号链接')
            elif item.issym():
                linkname = item.linkname.replace('\\', '/')
                if PurePosixPath(linkname).is_absolute() or ':' in linkname:
                    raise ValueError('工具链链接越界')
                resolved = (target.parent / linkname).resolve()
                if not resolved.is_relative_to(root.resolve()): raise ValueError('工具链链接越界')
                links.append((target, linkname))
            elif not item.isfile() and not item.isdir():
                raise ValueError('工具链归档包含硬链接或特殊文件')
        for item in members:
            if stop_event and stop_event.is_set(): raise InterruptedError('环境准备已取消')
            name = item.filename if kind == 'zip' else item.name
            target = member_path(root, name)
            is_dir = item.is_dir() if kind == 'zip' else item.isdir()
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
            elif kind != 'zip' and item.issym():
                continue
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.open(item) if kind == 'zip' else bundle.extractfile(item)
                with source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                if kind != 'zip': target.chmod(item.mode & 0o777)
        for target, linkname in links:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(linkname, target)
            if not target.resolve().is_relative_to(root.resolve()): raise ValueError('工具链链接越界')
