"""Credential storage is deliberately kept outside SQLite and backups.

Windows keeps a DPAPI-encrypted file and macOS uses Keychain; other systems
store a user-only (0600) local file next to the database.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import hashlib
from .. import platforms


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def crypt(data, decrypt=False):
    if os.name != 'nt': raise ValueError('此系统请通过 DEEPSEEK_API_KEY 环境变量配置 Key')
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    dll = ctypes.WinDLL('crypt32', use_last_error=True)
    function = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise ValueError('本机 Key 加密存储不可用，请重新配置或使用环境变量')
    try: return ctypes.string_at(target.data,target.size)
    finally:
        kernel = ctypes.WinDLL('kernel32')
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree(ctypes.cast(target.data,ctypes.c_void_p))


class KeyStore:
    def __init__(self, data_dir):
        self.path = Path(data_dir)/'ai-key.dpapi'
        self.local_path = Path(data_dir)/'ai-key.local'
        self.account = hashlib.sha256(str(Path(data_dir).resolve()).encode('utf-8')).hexdigest()

    def read(self):
        if platforms.system_name() == 'macos':
            from . import macos_keychain
            value = macos_keychain.read('CodeTopLocal.DeepSeek', self.account)
            return value if value is not None else os.environ.get('DEEPSEEK_API_KEY', '').strip()
        if os.name != 'nt':
            if self.local_path.exists():
                try:
                    return self.local_path.read_text(encoding='utf-8').strip()
                except OSError as exc:
                    raise ValueError('本机 Key 文件读取失败，请重新配置') from exc
            return os.environ.get('DEEPSEEK_API_KEY','').strip()
        if self.path.exists(): return crypt(self.path.read_bytes(),True).decode('utf-8')
        return os.environ.get('DEEPSEEK_API_KEY','').strip()

    def write(self, key):
        if platforms.system_name() == 'macos':
            from . import macos_keychain
            macos_keychain.write('CodeTopLocal.DeepSeek', self.account, key)
            return
        if os.name != 'nt':
            # Atomic replacement never publishes a partial credential.
            pending = self.local_path.with_suffix('.pending')
            try:
                handle = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                try:
                    os.fchmod(handle, 0o600)
                    os.write(handle, key.encode('utf-8'))
                finally:
                    os.close(handle)
            except OSError as exc:
                raise ValueError('Key 本地保存失败，请检查数据目录写入权限') from exc
            pending.replace(self.local_path)
            return
        # Atomic replacement never publishes a partial encrypted credential.
        pending = self.path.with_suffix('.pending')
        pending.write_bytes(crypt(key.encode('utf-8')))
        pending.replace(self.path)
