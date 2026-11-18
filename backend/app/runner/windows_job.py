"""Public Win32 process/Job APIs. Assign the suspended child before resuming it."""
import ctypes as c
from ctypes import wintypes as w
import msvcrt
import os
import subprocess
import time

SIZE = c.c_size_t
HANDLE = w.HANDLE
LP = c.c_void_p
k = c.WinDLL('kernel32', use_last_error=True)


def api(name, result, *args):
    fn = getattr(k, name)
    fn.restype, fn.argtypes = result, list(args)
    return fn


CloseHandle = api('CloseHandle', w.BOOL, HANDLE)
CreateJobObject = api('CreateJobObjectW', HANDLE, LP, w.LPCWSTR)
SetJob = api('SetInformationJobObject', w.BOOL, HANDLE, c.c_int, LP, w.DWORD)
QueryJob = api('QueryInformationJobObject', w.BOOL, HANDLE, c.c_int, LP, w.DWORD, LP)
TerminateJob = api('TerminateJobObject', w.BOOL, HANDLE, w.UINT)
CreatePipe = api('CreatePipe', w.BOOL, LP, LP, LP, w.DWORD)
SetHandleInformation = api('SetHandleInformation', w.BOOL, HANDLE, w.DWORD, w.DWORD)
InitializeAttributes = api('InitializeProcThreadAttributeList', w.BOOL, LP, w.DWORD, w.DWORD, LP)
UpdateAttributes = api('UpdateProcThreadAttribute', w.BOOL, LP, w.DWORD, SIZE, LP, SIZE, LP, LP)
DeleteAttributes = api('DeleteProcThreadAttributeList', None, LP)
CreateProcess = api('CreateProcessW', w.BOOL, w.LPCWSTR, w.LPWSTR, LP, LP, w.BOOL, w.DWORD, LP, w.LPCWSTR, LP, LP)
ResumeThread = api('ResumeThread', w.DWORD, HANDLE)
WaitForSingleObject = api('WaitForSingleObject', w.DWORD, HANDLE, w.DWORD)
GetExitCode = api('GetExitCodeProcess', w.BOOL, HANDLE, LP)
CreatePort = api('CreateIoCompletionPort', HANDLE, HANDLE, HANDLE, SIZE, w.DWORD)
GetPort = api('GetQueuedCompletionStatus', w.BOOL, HANDLE, LP, LP, LP, w.DWORD)
TerminateProcess = api('TerminateProcess', w.BOOL, HANDLE, w.UINT)


class Security(c.Structure):
    _fields_ = [('size', w.DWORD), ('descriptor', LP), ('inherit', w.BOOL)]


class Startup(c.Structure):
    _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
                ('x', w.DWORD), ('y', w.DWORD), ('width', w.DWORD), ('height', w.DWORD),
                ('xchars', w.DWORD), ('ychars', w.DWORD), ('fill', w.DWORD), ('flags', w.DWORD),
                ('show', w.WORD), ('reserved_size', w.WORD), ('reserved2', LP),
                ('stdin', HANDLE), ('stdout', HANDLE), ('stderr', HANDLE)]


class StartupEx(c.Structure):
    _fields_ = [('info', Startup), ('attributes', LP)]


class ProcessInfo(c.Structure):
    _fields_ = [('process', HANDLE), ('thread', HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]


class BasicLimits(c.Structure):
    _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong), ('flags', w.DWORD),
                ('min_working', SIZE), ('max_working', SIZE), ('processes', w.DWORD),
                ('affinity', SIZE), ('priority', w.DWORD), ('scheduling', w.DWORD)]


class Limits(c.Structure):
    _fields_ = [('basic', BasicLimits), ('io', c.c_ulonglong * 6), ('process_memory', SIZE),
                ('job_memory', SIZE), ('peak_process_memory', SIZE), ('peak_job_memory', SIZE)]


class Accounting(c.Structure):
    _fields_ = [('user', c.c_longlong), ('kernel', c.c_longlong), ('period_user', c.c_longlong),
                ('period_kernel', c.c_longlong), ('faults', w.DWORD), ('total', w.DWORD),
                ('active', w.DWORD), ('terminated', w.DWORD)]


class PortAssociation(c.Structure):
    _fields_ = [('key', LP), ('port', HANDLE)]


def check(value):
    if not value:
        raise c.WinError(c.get_last_error())
    return value


class JobProcess:
    def __init__(self, argv, cwd, env, *, memory_mb=256, max_processes=32):
        self.job = self.port = self.handle = None
        self.stdin = self.stdout = self.stderr = None
        self.memory_exceeded = False
        pipes = []
        attrs = None
        info = ProcessInfo()
        try:
            self.job = check(CreateJobObject(None, None))
            limits = Limits()
            limits.basic.flags = 0x2000 | 0x200 | 0x8  # kill-on-close, aggregate memory, active processes
            limits.basic.processes = max_processes
            limits.job_memory = memory_mb * 1024 * 1024
            check(SetJob(self.job, 9, c.byref(limits), c.sizeof(limits)))
            self.port = check(CreatePort(HANDLE(-1), None, 0, 1))
            association = PortAssociation(None, self.port)
            check(SetJob(self.job, 7, c.byref(association), c.sizeof(association)))
            security = Security(c.sizeof(Security), None, True)
            for _ in range(3):
                read, write = HANDLE(), HANDLE()
                check(CreatePipe(c.byref(read), c.byref(write), c.byref(security), 0))
                pipes.append([read.value, write.value])
            parents = [pipes[0][1], pipes[1][0], pipes[2][0]]
            children = [pipes[0][0], pipes[1][1], pipes[2][1]]
            for handle in parents:
                check(SetHandleInformation(handle, 1, 0))
            size = SIZE()
            InitializeAttributes(None, 1, 0, c.byref(size))
            attrs = c.create_string_buffer(size.value)
            check(InitializeAttributes(attrs, 1, 0, c.byref(size)))
            inherited = (HANDLE * 3)(*children)
            check(UpdateAttributes(attrs, 0, 0x20002, inherited, c.sizeof(inherited), None, None))
            startup = StartupEx()
            startup.info.cb = c.sizeof(startup)
            startup.info.flags = 0x100
            startup.info.stdin, startup.info.stdout, startup.info.stderr = children
            startup.attributes = c.cast(attrs, LP)
            command = c.create_unicode_buffer(subprocess.list2cmdline([str(v) for v in argv]))
            block = c.create_unicode_buffer('\0'.join(f'{key}={value}' for key, value in sorted(env.items())) + '\0\0')
            check(CreateProcess(str(argv[0]), command, None, None, True,
                                0x4 | 0x80000 | 0x400 | 0x08000000, block, str(cwd), c.byref(startup), c.byref(info)))
            self.handle, self.pid = info.process, info.pid
            # There is no gap in which unassigned user code can run.
            check(api('AssignProcessToJobObject', w.BOOL, HANDLE, HANDLE)(self.job, self.handle))
            for index, (handle, mode) in enumerate(zip(parents, ('wb', 'rb', 'rb'))):
                fd = msvcrt.open_osfhandle(handle, (os.O_WRONLY if mode == 'wb' else os.O_RDONLY) | os.O_BINARY)
                pipes[0 if index == 0 else index][1 if index == 0 else 0] = None
                setattr(self, ('stdin', 'stdout', 'stderr')[index], os.fdopen(fd, mode, buffering=0))
            if ResumeThread(info.thread) == 0xffffffff:
                raise c.WinError(c.get_last_error())
        except BaseException:
            if info.process:
                TerminateProcess(info.process, 1)
            self.close()
            raise
        finally:
            if info.thread:
                CloseHandle(info.thread)
            if attrs:
                DeleteAttributes(attrs)
            for pair in pipes:
                for handle in pair:
                    if handle:
                        CloseHandle(handle)

    def poll(self):
        if WaitForSingleObject(self.handle, 0) == 258:
            return None
        code = w.DWORD()
        check(GetExitCode(self.handle, c.byref(code)))
        return code.value

    def cpu_seconds(self):
        accounting = Accounting()
        check(QueryJob(self.job, 1, c.byref(accounting), c.sizeof(accounting), None))
        return (accounting.user + accounting.kernel) / 10_000_000

    def limit_events(self):
        while True:
            message, key, overlapped = w.DWORD(), SIZE(), LP()
            if not GetPort(self.port, c.byref(message), c.byref(key), c.byref(overlapped), 0):
                break
            if message.value in (9, 10):
                self.memory_exceeded = True
        return self.memory_exceeded

    def terminate(self):
        if self.job:
            TerminateJob(self.job, 1)

    def wait(self, timeout=5):
        if WaitForSingleObject(self.handle, int(timeout * 1000)) == 258:
            raise TimeoutError('Python 进程未按时退出')
        return self.poll()

    def close(self):
        self.terminate()
        for name in ('stdin', 'stdout', 'stderr'):
            stream = getattr(self, name, None)
            if stream:
                stream.close()
                setattr(self, name, None)
        for name in ('handle', 'job', 'port'):
            handle = getattr(self, name, None)
            if handle:
                CloseHandle(handle)
                setattr(self, name, None)
