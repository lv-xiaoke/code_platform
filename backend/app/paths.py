"""Application assets and executable runtimes are independent of cwd/PATH."""
import os
from pathlib import Path
import sys
import hashlib
import json


def application_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def default_data_dir():
    if os.environ.get('CODETOP_DATA_DIR'):
        return Path(os.environ['CODETOP_DATA_DIR']).resolve()
    if getattr(sys, 'frozen', False):
        base = os.environ.get('LOCALAPPDATA')
        if not base:
            raise ValueError('无法定位用户数据目录 LOCALAPPDATA')
        return Path(base) / 'CodeTopLocal'
    return application_root() / 'data'


def native_python():
    if getattr(sys, 'frozen', False):
        return application_root() / 'python' / 'python.exe'
    # Development uses the base interpreter, never a PATH lookup or a frozen EXE.
    return Path(sys._base_executable).resolve()


def verify_bundled_runtime():
    if not getattr(sys, 'frozen', False):
        return
    root = application_root()
    try:
        manifest = json.loads((root / 'runtime-lock.json').read_text(encoding='utf-8'))
        if 'python.exe' not in manifest['files'] or not manifest['files']:
            raise ValueError('运行时清单无效')
        for relative, expected in manifest['files'].items():
            path = (root / 'python' / relative).resolve()
            if not path.is_relative_to((root / 'python').resolve()):
                raise ValueError('运行时路径无效')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise ValueError('运行时校验失败，请重新安装完整桌面版')
    except (OSError, KeyError, ValueError) as exc:
        raise ValueError('内置 Python 校验失败，请重新安装完整桌面版') from exc
