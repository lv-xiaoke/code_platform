"""Container-only stdin bridge. Never execute this supervisor on the host."""
import codecs
import ctypes
import json
import os
import resource
import runpy
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

LIMIT=65536
WALL_SECONDS=300


def container_cpu():
    path=Path('/sys/fs/cgroup/cpu.stat')
    if path.exists():
        values=dict(line.split() for line in path.read_text().splitlines())
        if 'usage_usec' in values: return int(values['usage_usec'])/1000000
    for name in ['/sys/fs/cgroup/cpuacct/cpuacct.usage','/sys/fs/cgroup/cpuacct.usage']:
        path=Path(name)
        if path.exists(): return int(path.read_text())/1000000000
    raise RuntimeError('container cumulative CPU accounting is required')


def emit(kind,**fields):
    print(json.dumps({'type':kind,**fields},ensure_ascii=True),flush=True)


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU,(3,4))
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def main():
    shared=runpy.run_path('/opt/codetop-worker.py')
    shared['require_private_container_init']()
    # Same-UID child code must not reopen /proc/1/fd and forge the JSON channel.
    if ctypes.CDLL(None,use_errno=True).prctl(4,0,0,0,0)!=0:
        raise OSError(ctypes.get_errno(),'unable to protect supervisor')
    started=time.monotonic()
    cpu_started=container_cpu()
    process=subprocess.Popen([sys.executable,'-I','-S','-B','-u','/work/main.py'],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=child_limits,
        env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8'},cwd='/tmp')
    selector=selectors.DefaultSelector()
    for stream,name in [(sys.stdin.buffer,'input'),(process.stdout,'stdout'),(process.stderr,'stderr')]:
        os.set_blocking(stream.fileno(),False)
        selector.register(stream,selectors.EVENT_READ,name)
    os.set_blocking(process.stdin.fileno(),False)
    decoders={name:codecs.getincrementaldecoder('utf-8')(errors='replace') for name in ('stdout','stderr')}
    protocol=bytearray()
    pending=bytearray()
    total=0
    input_total=0
    close_input=False
    input_registered=False
    reaped=False
    status='executed'
    stderr_tail=''
    emit('ready',python_version=sys.version.split()[0])
    try:
        while True:
            if process.poll() is not None and not reaped:
                shared['reap_case_descendants']()
                reaped=True
            if reaped and not any(key.data in ('stdout','stderr') for key in selector.get_map().values()): break
            if status=='executed' and (time.monotonic()-started>WALL_SECONDS or container_cpu()-cpu_started>3):
                status='time_limit';shared['kill_group'](process)
            for key,_ in selector.select(.03):
                if key.data=='write':
                    try:
                        count=os.write(process.stdin.fileno(),pending)
                        del pending[:count]
                    except BlockingIOError: continue
                    except BrokenPipeError: pending.clear();close_input=True
                    if not pending:
                        selector.unregister(process.stdin);input_registered=False
                        if close_input: process.stdin.close()
                    continue
                raw=os.read(key.fileobj.fileno(),8192)
                if key.data=='input':
                    if not raw:
                        selector.unregister(key.fileobj);close_input=True
                    else:
                        protocol.extend(raw)
                        if len(protocol)>450000: raise ValueError('input protocol limit')
                        while b'\n' in protocol:
                            line,_,remaining=protocol.partition(b'\n');protocol=bytearray(remaining)
                            message=json.loads(line)
                            if close_input: continue
                            data=message.get('text','').encode('utf-8')
                            input_total+=len(data)
                            if input_total>LIMIT: raise ValueError('input limit')
                            pending.extend(data)
                            if message.get('eof'): close_input=True
                    if pending and not input_registered and not process.stdin.closed:
                        selector.register(process.stdin,selectors.EVENT_WRITE,'write');input_registered=True
                    elif close_input and not pending and not process.stdin.closed:
                        process.stdin.close()
                    continue
                name=key.data
                if not raw:
                    selector.unregister(key.fileobj)
                    text=decoders[name].decode(b'',final=True)
                else:
                    available=max(0,LIMIT-total)
                    total+=len(raw)
                    text=decoders[name].decode(raw[:available],final=total>LIMIT)
                    if total>LIMIT and status=='executed':
                        status='output_limit';shared['kill_group'](process)
                if text:
                    emit(name,text=text)
                    if name=='stderr': stderr_tail=(stderr_tail+text)[-4096:]
        return_code=process.wait(timeout=1)
        if status=='executed' and return_code:
            status='time_limit' if return_code==-signal.SIGXCPU else 'syntax_error' if 'SyntaxError' in stderr_tail or 'IndentationError' in stderr_tail else 'memory_limit' if 'MemoryError' in stderr_tail else 'runtime_error'
        emit('exit',status=status,exit_code=return_code,duration_ms=round((time.monotonic()-started)*1000,2))
    finally:
        shared['kill_group'](process)
        shared['reap_case_descendants']()
        selector.close()
        for stream in (process.stdin,process.stdout,process.stderr): stream.close()


if __name__=='__main__': main()
