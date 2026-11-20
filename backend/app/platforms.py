"""Small OS boundary; native libraries are loaded only by their own backend."""
import platform
import sys
import time
import subprocess


def system_name():
    return {'win32': 'windows', 'darwin': 'macos'}.get(sys.platform, 'unsupported')


def architecture():
    machine = platform.machine().lower()
    if machine in ('amd64', 'x86_64'):
        return 'x86_64'
    if machine in ('arm64', 'aarch64'):
        return 'arm64'
    raise ValueError(f'不支持的处理器架构：{machine}')


def background_options():
    return {'creationflags': 0x08000000} if system_name() == 'windows' else {'start_new_session': True}


def open_browser(url):
    try:
        if system_name() == 'macos':
            subprocess.run(['/usr/bin/open', url], check=True, timeout=15, capture_output=True)
        else:
            import webbrowser
            if not webbrowser.open(url):
                raise RuntimeError('Browser unavailable')
    except (OSError, subprocess.SubprocessError, RuntimeError):
        raise RuntimeError(f'无法打开浏览器，请手动打开 {url}') from None


def process_identity(pid):
    if system_name() != 'macos':
        return None
    import psutil
    try:
        process = psutil.Process(pid)
        return f'{pid}:{process.create_time():.6f}' if process.is_running() else None
    except psutil.NoSuchProcess:
        return None


def wait_for_process(pid, identity=None, timeout=60):
    if system_name() == 'windows':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, int(timeout * 1000)) == 258:
                    raise RuntimeError('服务未退出，取消恢复；原数据保留')
            finally:
                kernel.CloseHandle(handle)
        elif ctypes.get_last_error() not in (0, 87):
            raise RuntimeError('无法确认服务已退出，取消恢复；原数据保留')
        return
    if not identity:
        raise RuntimeError('缺少原服务身份，取消恢复；原数据保留')
    deadline = time.monotonic() + timeout
    while process_identity(pid) == identity:
        if time.monotonic() >= deadline:
            raise RuntimeError('服务未退出，取消恢复；原数据保留')
        time.sleep(.05)


def show_error(message):
    if system_name() == 'windows':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'CodeTop 启动失败', 0x10)
    elif system_name() == 'macos':
        script = 'on run argv\ndisplay alert "CodeTop 启动失败" message (item 1 of argv) as critical\nend run'
        try:
            subprocess.run(['/usr/bin/osascript', '-', message], input=script,
                           text=True, timeout=30, check=True, capture_output=True)
        except (OSError, subprocess.SubprocessError):
            print(message, file=sys.stderr)
