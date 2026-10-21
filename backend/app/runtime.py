"""OS-held lock: released automatically even if the process terminates."""
import os


class RuntimeLock:
    def __init__(self, data_dir):
        self.path = data_dir / 'service.lock'
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, 'a+b')
        self.handle.seek(0)
        if self.path.stat().st_size == 0:
            self.handle.write(b'0')
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            raise ValueError('应用服务正在使用此数据目录，请先运行 scripts/stop.ps1') from exc
        return self

    def __exit__(self, *args):
        if self.handle: self.handle.close()
