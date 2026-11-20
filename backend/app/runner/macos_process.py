"""macOS process-group supervision. RSS monitoring is not an isolation sandbox."""
import os
import signal
import subprocess
from ..paths import application_root


class MacProcess:
    def __init__(self, argv, cwd, env, *, memory_mb=256, max_processes=32, cpu_seconds=3):
        import psutil
        self.psutil = psutil
        self.memory_limit = memory_mb * 1024 * 1024
        self.max_processes = max_processes
        self.memory_exceeded = False
        self.process_limit_exceeded = False
        self.samples = {}
        self.terminated = False
        bootstrap = application_root() / 'backend/runner/native_bootstrap.py'
        if not bootstrap.is_file():
            raise ValueError('本机执行启动文件缺失，请重新安装')
        from ..paths import native_python
        command = [str(native_python()), '-I', '-S', '-B', str(bootstrap),
                   '--cpu-seconds', str(cpu_seconds), '--', *map(str, argv)]
        self.process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        bufsize=0, start_new_session=True, close_fds=True)
        self.pid = self.process.pid
        self.stdin, self.stdout, self.stderr = self.process.stdin, self.process.stdout, self.process.stderr
        try:
            self.leader = psutil.Process(self.pid)
            self.created = self.leader.create_time()
        except psutil.NoSuchProcess:
            # A short program can exit before the first sample; retain its Popen handle.
            self.leader, self.created = None, 0

    def poll(self):
        return self.process.poll()

    def members(self):
        # PGID remains reserved while any original group member remains alive.
        for process in self.psutil.process_iter():
            try:
                if os.getpgid(process.pid) == self.pid and os.getsid(process.pid) == self.pid:
                    yield process
            except (ProcessLookupError, PermissionError, self.psutil.NoSuchProcess):
                continue

    def limit_events(self):
        rss, count = 0, 0
        try:
            for process in self.members():
                try:
                    identity = (process.pid, process.create_time())
                    times = process.cpu_times()
                    self.samples[identity] = max(self.samples.get(identity, 0), times.user + times.system)
                    rss += process.memory_info().rss
                    count += 1
                except self.psutil.NoSuchProcess:
                    continue
        except self.psutil.AccessDenied:
            self.terminate()
            raise RuntimeError('无法监测练习进程资源，已停止本次运行') from None
        if rss > self.memory_limit:
            self.memory_exceeded = True
        if count > self.max_processes:
            self.process_limit_exceeded = True
            self.terminate()
            raise RuntimeError('练习进程数量超过 32 个，已停止本次运行')
        return self.memory_exceeded

    def cpu_seconds(self):
        return sum(self.samples.values())

    def terminate(self):
        if self.terminated:
            return
        try:
            # Refuse a recycled leader PID. If the original leader has exited,
            # its still-existing group (including inherited pipes) remains ours.
            try:
                current = self.psutil.Process(self.pid)
                if self.created and current.create_time() != self.created:
                    self.terminated = True
                    return
            except self.psutil.NoSuchProcess:
                pass
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.terminated = True

    def wait(self, timeout=5):
        return self.process.wait(timeout=timeout)

    def close(self):
        self.terminate()
        try:
            self.wait()
        finally:
            for stream in (self.stdin, self.stdout, self.stderr):
                if stream:
                    stream.close()
