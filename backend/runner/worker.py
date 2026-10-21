"""Trusted Linux-only supervisor. User code always runs in a separate process."""
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import time

LIMIT=65536
TIMEOUT=2.0


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU,(3,3))
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def kill_group(process):
    try: os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError: pass


def require_private_container_init():
    # kill(-1) below is permitted ONLY for our dedicated Docker PID namespace.
    # This supervisor is the direct entrypoint; never use --pid=host or --init.
    if sys.platform!='linux' or os.getpid()!=1 or not Path('/.dockerenv').is_file():
        raise RuntimeError('worker requires PID 1 in its private Docker container')


def reap_case_descendants():
    require_private_container_init()
    deadline=time.monotonic()+1.0
    while True:
        try: os.kill(-1,signal.SIGKILL)
        except ProcessLookupError: pass
        try:
            while os.waitpid(-1,os.WNOHANG)[0]: pass
        except ChildProcessError:
            return
        if time.monotonic()>=deadline:
            raise RuntimeError('unable to reap case descendants; stopping this container')
        time.sleep(0.005)


def run_case(index):
    started=time.monotonic()
    chunks={'stdout':bytearray(),'stderr':bytearray()}
    status='executed'
    with open(f'/work/case-{index}.in','rb') as input_file:
        process=subprocess.Popen([sys.executable,'-I','-S','-B','-u','/work/main.py'],
            stdin=input_file,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            start_new_session=True,preexec_fn=child_limits,
            env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8'},cwd='/tmp')
        selector=selectors.DefaultSelector()
        for name,stream in [('stdout',process.stdout),('stderr',process.stderr)]:
            os.set_blocking(stream.fileno(),False)
            selector.register(stream,selectors.EVENT_READ,name)
        total=0
        deadline=started+TIMEOUT
        killed_at=None
        try:
            while selector.get_map():
                current=time.monotonic()
                if killed_at is None and current>=deadline:
                    status='time_limit';kill_group(process);killed_at=current
                if killed_at is not None and current-killed_at>0.5: break
                for key,_ in selector.select(0.02):
                    raw=os.read(key.fileobj.fileno(),8192)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    remaining=max(0,LIMIT-total)
                    chunks[key.data].extend(raw[:remaining])
                    total+=len(raw)
                    if total>LIMIT and killed_at is None:
                        status='output_limit';kill_group(process);killed_at=time.monotonic()
            try: return_code=process.wait(timeout=max(0.05,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                status='time_limit';kill_group(process);return_code=process.wait(timeout=1)
        finally:
            kill_group(process)
            selector.close()
            process.stdout.close();process.stderr.close()
            # PID 1 adopts detached descendants and zombies. Reap every child
            # before allowing the next case to consume the shared PID budget.
            reap_case_descendants()
    stdout=chunks['stdout'].decode('utf-8',errors='replace')
    stderr=chunks['stderr'].decode('utf-8',errors='replace')
    if status=='executed' and return_code!=0:
        status='syntax_error' if 'SyntaxError' in stderr or 'IndentationError' in stderr else 'memory_limit' if 'MemoryError' in stderr else 'runtime_error'
    return {'stdout':stdout,'stderr':stderr,'status':status,'exit_code':return_code,
            'duration_ms':round((time.monotonic()-started)*1000,2)}


def main():
    require_private_container_init()
    request=json.loads(Path('/work/request.json').read_text(encoding='utf-8'))
    count=request['case_count']
    if type(count) is not int or not 1<=count<=20: raise ValueError('invalid case count')
    results=[run_case(i) for i in range(count)]
    print(json.dumps({'results':results,'python_version':sys.version.split()[0]},ensure_ascii=True),flush=True)


if __name__=='__main__': main()
