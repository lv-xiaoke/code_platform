"""Track the service lock and the browser tabs that keep it running."""
import os
from contextlib import contextmanager
from time import monotonic


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


class BrowserTabs:
    startup_grace = 60
    close_grace = 5

    def __init__(self, clock=monotonic):
        self._clock = clock
        self._idle_until: float | None = None
        self._active = 0

    @contextmanager
    def connected(self):
        self._active += 1
        try:
            yield
        finally:
            self._active -= 1
            if not self._active:
                self._idle_until = self._clock() + self.close_grace

    def should_stop(self):
        now = self._clock()
        if self._idle_until is None:
            self._idle_until = now + self.startup_grace
        return not self._active and now >= self._idle_until
