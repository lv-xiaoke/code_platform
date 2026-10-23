"""Host transport. Submitted code is executed only inside the pinned container."""
import json
import queue
import subprocess
import threading
import time

from .docker import DockerRunner, FLAGS, RUNNER_ROOT


class InteractiveDockerRunner(DockerRunner):
    def command(self,job_id,job_dir):
        command=super().command(job_id,job_dir)
        command.insert(2,'-i')
        command.insert(3,'--cgroupns=private')
        index=command.index('--entrypoint')
        command[index:index]=['--mount',f'type=bind,source={RUNNER_ROOT / "interactive_worker.py"},target=/opt/codetop-interactive.py,readonly']
        command[-1]='/opt/codetop-interactive.py'
        return command

    def execute(self,session):
        started=time.monotonic()
        job_dir=self.artifact_root/session.id
        command=self.command(session.id,job_dir)
        job_dir.mkdir(exist_ok=False)
        (job_dir/'main.py').write_text(session.source_code,encoding='utf-8')
        (job_dir/'request.json').write_text('{"mode":"interactive"}',encoding='utf-8')
        name='codetop-run-'+session.id
        process=None
        final={}
        errors=[]
        diagnostic=bytearray()
        threads=[]
        try:
            if session.stop_event.is_set(): return {'status':'stopped','exit_code':None,'duration_ms':0}
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**FLAGS)

            def read_events():
                total=0
                try:
                    while True:
                        raw=process.stdout.readline(460000)
                        if not raw: break
                        total+=len(raw)
                        if len(raw)>=460000 or total>8*1024*1024: raise ValueError('终端传输超过上限')
                        event=json.loads(raw)
                        if event['type']=='exit':
                            final.update(event)
                            with session.lock: session.accepting=False
                        else: session.emit(event)
                except Exception as exc: errors.append(str(exc))
                finally: process.stdout.close()

            def read_errors():
                try:
                    while True:
                        raw=process.stderr.read(1024)
                        if not raw: break
                        diagnostic.extend(raw[:max(0,4096-len(diagnostic))])
                finally: process.stderr.close()

            def write_inputs():
                try:
                    while process.poll() is None and not session.stop_event.is_set():
                        try: message=session.inputs.get(timeout=.05)
                        except queue.Empty: continue
                        process.stdin.write((json.dumps(message,ensure_ascii=True)+'\n').encode())
                        process.stdin.flush()
                        if message['eof']: break
                except (OSError,ValueError): pass
                finally:
                    try: process.stdin.close()
                    except OSError: pass

            threads=[threading.Thread(target=target,daemon=True) for target in (read_events,read_errors,write_inputs)]
            for thread in threads: thread.start()
            forced=None
            while process.poll() is None:
                if session.stop_event.is_set() or errors or time.monotonic()-started>315:
                    forced='stopped' if session.stop_event.is_set() else 'failed' if errors else 'time_limit'
                    self._control('kill',name)
                    if process.poll() is None: process.kill()
                    break
                time.sleep(.02)
            process.wait(timeout=3)
            for thread in threads: thread.join(timeout=2)
            if forced:
                return {'status':forced,'exit_code':None,'duration_ms':round((time.monotonic()-started)*1000,2),
                        **({'error':errors[0]} if errors else {})}
            if not final or process.returncode:
                raise RuntimeError('Docker 交互运行失败，请检查运行环境。'+diagnostic.decode('utf-8',errors='replace')[:2000])
            return {k:v for k,v in final.items() if k!='type'}
        finally:
            if process is not None and process.poll() is None:
                self._control('kill',name)
                process.kill()
                process.wait(timeout=3)
            self._control('rm',name)
