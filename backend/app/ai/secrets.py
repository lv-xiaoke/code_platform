"""DPAPI credentials are deliberately kept outside SQLite and backups."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


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
    def __init__(self, data_dir): self.path = Path(data_dir)/'ai-key.dpapi'

    def read(self):
        if self.path.exists(): return crypt(self.path.read_bytes(),True).decode('utf-8')
        return os.environ.get('DEEPSEEK_API_KEY','').strip()

    def write(self, key):
        # Atomic replacement never publishes a partial encrypted credential.
        pending = self.path.with_suffix('.pending')
        pending.write_bytes(crypt(key.encode('utf-8')))
        pending.replace(self.path)
