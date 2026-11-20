"""Application assets and executable runtimes are independent of cwd/PATH."""
import os
from pathlib import Path
import sys
import hashlib
import json
from . import platforms


def application_root():
    if getattr(sys, 'frozen', False):
        executable_dir = Path(sys.executable).resolve().parent
        if platforms.system_name() == 'macos':
            return executable_dir.parent / 'Resources'
        return executable_dir
    return Path(__file__).resolve().parents[2]


def default_data_dir():
    if os.environ.get('CODETOP_DATA_DIR'):
        return Path(os.environ['CODETOP_DATA_DIR']).resolve()
    if getattr(sys, 'frozen', False):
        if platforms.system_name() == 'macos':
            return Path.home() / 'Library' / 'Application Support' / 'CodeTopLocal'
        base = os.environ.get('LOCALAPPDATA')
        if not base:
            raise ValueError('无法定位用户数据目录 LOCALAPPDATA')
        return Path(base) / 'CodeTopLocal'
    return application_root() / 'data'


def native_python():
    if getattr(sys, 'frozen', False):
        executable = 'bin/python3' if platforms.system_name() == 'macos' else 'python.exe'
        return application_root() / 'python' / executable
    # Development uses the base interpreter, never a PATH lookup or a frozen EXE.
    return Path(sys._base_executable).resolve()


def toolchains_dir():
    if os.environ.get('CODETOP_TOOLCHAINS_DIR'):
        return Path(os.environ['CODETOP_TOOLCHAINS_DIR']).resolve()
    if platforms.system_name() == 'macos':
        return Path.home() / 'Library/Application Support/CodeTopLocal/toolchains'
    base = os.environ.get('LOCALAPPDATA')
    if not base: raise ValueError('无法定位用户语言环境目录 LOCALAPPDATA')
    return Path(base) / 'CodeTopLocal/toolchains'


def verify_bundled_runtime():
    if not getattr(sys, 'frozen', False):
        return
    root = application_root()
    try:
        manifest = json.loads((root / 'runtime-lock.json').read_text(encoding='utf-8'))
        executable = manifest.get('executable', 'python.exe')
        if not isinstance(executable, str) or executable not in manifest['files'] or not manifest['files']:
            raise ValueError('运行时清单无效')
        for relative, expected in manifest['files'].items():
            if not isinstance(relative, str) or Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('运行时路径无效')
            path = (root / 'python' / relative).resolve()
            if not path.is_relative_to((root / 'python').resolve()):
                raise ValueError('运行时路径无效')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise ValueError('运行时校验失败，请重新安装完整桌面版')
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError('内置 Python 校验失败，请重新安装完整桌面版') from exc
