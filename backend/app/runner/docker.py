import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from uuid import UUID

from .comparison import compare_output

from ..paths import application_root
RUNNER_ROOT=application_root()/'backend'/'runner'
RUNTIME=json.loads((RUNNER_ROOT/'runtime.json').read_text(encoding='utf-8'))
FLAGS={'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0)}


class RunnerUnavailable(RuntimeError): pass


class DockerRunner:
    kind = 'docker'
    def __init__(self,artifact_root):
        self.artifact_root=Path(artifact_root).resolve()
        self.artifact_root.mkdir(parents=True,exist_ok=True)
        self.image_ref=RUNTIME['image']
        self.docker=shutil.which('docker') or 'docker'

    def health(self):
        try:
            version=subprocess.run([self.docker,'version','--format','{{.Server.Version}}'],capture_output=True,timeout=5,**FLAGS)
            if version.returncode: raise RunnerUnavailable('Docker 未就绪，请启动 Docker Desktop 并使用 Linux 容器。')
            image=subprocess.run([self.docker,'image','inspect',self.image_ref,'--format','{{.Id}}'],capture_output=True,timeout=5,**FLAGS)
            if image.returncode: raise RunnerUnavailable('Python 运行镜像尚未安装，请运行 scripts/setup-runner.ps1。')
            return {'available':True,'image_ref':self.image_ref,'python_series':'3.12','limits':RUNTIME,'engine_version':version.stdout.decode().strip()}
        except (OSError,subprocess.TimeoutExpired,RunnerUnavailable) as exc:
            return {'available':False,'image_ref':self.image_ref,'python_series':'3.12','limits':RUNTIME,'error':str(exc)}

    def command(self,job_id,job_dir):
        if str(UUID(job_id))!=job_id: raise ValueError('运行编号无效')
        job_dir=Path(job_dir).resolve()
        if job_dir.parent!=self.artifact_root or job_dir.name!=job_id: raise ValueError('运行目录不在预期范围')
        return [self.docker,'run','--pull','never','--name','codetop-run-'+job_id,
            '--label','app=codetop-local-runner','--network','none','--read-only',
            '--user','65534:65534','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','32','--memory','256m','--memory-swap','256m','--cpus','1',
            '--ulimit','nofile=64:64','--ulimit','core=0:0','--log-driver','none',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=16m,mode=1777',
            '--mount',f'type=bind,source={job_dir},target=/work,readonly',
            '--mount',f'type=bind,source={RUNNER_ROOT / "worker.py"},target=/opt/codetop-worker.py,readonly',
            '--entrypoint','python',self.image_ref,'-I','-S','-B','/opt/codetop-worker.py']

    def _control(self,verb,name):
        try:
            return subprocess.run([self.docker,verb,*(['--force'] if verb=='rm' else []),name],capture_output=True,timeout=8,**FLAGS)
        except (OSError,subprocess.TimeoutExpired): return None

    def execute(self,job_id,source_code,cases):
        if not 1<=len(cases)<=20: raise ValueError('每次运行需要 1–20 组测试')
        job_dir=self.artifact_root/job_id
        command=self.command(job_id,job_dir)
        job_dir.mkdir(exist_ok=False)
        (job_dir/'main.py').write_text(source_code,encoding='utf-8')
        (job_dir/'request.json').write_text(json.dumps({'case_count':len(cases)}),encoding='utf-8')
        for i,case in enumerate(cases): (job_dir/f'case-{i}.in').write_bytes(case['stdin'].encode('utf-8'))
        name='codetop-run-'+job_id
        buffers=[bytearray(),bytearray()]
        # JSON may expand each captured byte to six ASCII bytes (e.g. NUL).
        # Keep the host pipe bounded while allowing every legal case output.
        transport_limit=len(cases)*(RUNTIME['output_limit_bytes']*6+4096)+65536
        exceeded=threading.Event()
        process=None
        try:
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.DEVNULL,**FLAGS)
            def capture(stream,buffer):
                try:
                    while True:
                        raw=stream.read(8192)
                        if not raw: break
                        remaining=max(0,transport_limit-len(buffer))
                        buffer.extend(raw[:remaining])
                        if len(raw)>remaining:
                            exceeded.set()
                            break
                finally: stream.close()
            threads=[threading.Thread(target=capture,args=(stream,buf),daemon=True) for stream,buf in zip((process.stdout,process.stderr),buffers)]
            for thread in threads: thread.start()
            deadline=time.monotonic()+len(cases)*2.5+15
            while process.poll() is None:
                if exceeded.is_set() or time.monotonic()>deadline:
                    self._control('kill',name)
                    process.kill();process.wait(timeout=5)
                    raise RunnerUnavailable('运行器输出异常或整个任务超时，容器已停止。')
                time.sleep(0.03)
            for thread in threads: thread.join(timeout=2)
            if exceeded.is_set(): raise RunnerUnavailable('运行器输出超过传输上限')
            if process.returncode:
                error=buffers[1].decode('utf-8',errors='replace')[:2000]
                raise RunnerUnavailable('Docker 执行失败，请检查 Docker Desktop 和运行镜像。'+error)
            try: payload=json.loads(buffers[0])
            except (json.JSONDecodeError,UnicodeDecodeError) as exc: raise RunnerUnavailable('运行器返回格式错误') from exc
            if not isinstance(payload,dict) or not isinstance(payload.get('results'),list) or len(payload['results'])!=len(cases): raise RunnerUnavailable('运行器返回测试数量不匹配')
            results=[]
            for case,result in zip(cases,payload['results']):
                if not isinstance(result,dict) or not isinstance(result.get('stdout'),str) or not isinstance(result.get('stderr'),str): raise RunnerUnavailable('运行器结果字段错误')
                if result['status']=='executed' and case.get('expected_stdout') is not None:
                    result['status']='passed' if compare_output(result['stdout'],case['expected_stdout'],case.get('comparison','tokens')) else 'wrong_answer'
                results.append({**case,**result})
            output={'results':results,'image_ref':self.image_ref,'python_version':payload.get('python_version')}
            (job_dir/'result.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
            return output
        finally:
            if process is not None and process.poll() is None:
                self._control('kill',name)
                process.kill()
                process.wait(timeout=5)
            # Only this individual generated container; never prune or remove host files.
            self._control('rm',name)
