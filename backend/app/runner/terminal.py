"""Bounded, authenticated-by-router interactive sessions; history uses code_runs."""
import hashlib
import json
import queue
import threading
from collections import OrderedDict
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, insert, update

from .. import models as m
from ..learning import require_problem, utc_text
from .factory import create_runner
from .consent import require_native_consent
from .execution import require_environment
from .programs import PreparationError

LIMIT=65536
ACTIVE={'starting','preparing','compiling','running','stopping'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class TerminalSession:
    def __init__(self,run_id,pid,source,language='python'):
        self.id,self.problem_id,self.source_code=run_id,pid,source
        self.lock=threading.RLock()
        self.inputs=queue.Queue()
        self.stop_event=threading.Event()
        self.finished=threading.Event()
        self.status='starting'
        self.stdout=self.stderr=self.stdin=self.transcript=''
        self.python_version=None
        self.language=language
        self.metadata={}
        self.input_closed=False
        self.accepting=True
        self.output_bytes=0
        self.requests={}
        self.result={}

    def emit(self,event):
        with self.lock:
            if event['type']=='ready':
                self.python_version=event.get('python_version')
                self.metadata.update({k:v for k,v in event.items() if k!='type'})
                if not self.stop_event.is_set(): self.status='running'
            elif event['type']=='phase':
                self.metadata.update({k:v for k,v in event.items() if k not in ('type','status')})
                if not self.stop_event.is_set(): self.status=event['status']
            elif event['type'] in ('stdout','stderr'):
                text=event['text']
                raw=text.encode('utf-8')
                if self.output_bytes+len(raw)>LIMIT:
                    raise ValueError('终端输出超过 64 KiB')
                self.output_bytes+=len(raw)
                setattr(self,event['type'],getattr(self,event['type'])+text)
                self.transcript+=text

    def snapshot(self):
        with self.lock:
            return {**self.metadata,'id':self.id,'problem_id':self.problem_id,'status':self.status,'language':self.language,
                    'stdout':self.stdout,'stderr':self.stderr,'stdin':self.stdin,'transcript':self.transcript,
                    'input_closed':self.input_closed or not self.accepting,'python_version':self.python_version,
                    'exit_code':self.result.get('exit_code'),'error':self.result.get('error')}

    def send(self,payload):
        key=payload.request_id
        body={'text':payload.text,'eof':payload.eof}
        signature=digest(body)
        with self.lock:
            if key in self.requests:
                if self.requests[key]!=signature: raise HTTPException(409,'此输入编号已用于不同内容')
                return self.snapshot()
            if not self.accepting or self.input_closed or self.stop_event.is_set():
                raise HTTPException(409,'程序已结束或输入已关闭，请重新运行')
            if len(self.requests)>=1024: raise HTTPException(422,'本次输入次数已达上限，请重新运行')
            if len((self.stdin+payload.text).encode('utf-8'))>LIMIT: raise HTTPException(422,'本次输入累计不能超过 64 KiB')
            self.requests[key]=signature
            self.stdin+=payload.text
            self.transcript+=payload.text
            self.input_closed=payload.eof
            self.inputs.put(body)
            return self.snapshot()


class TerminalService:
    def __init__(self,db,clock,registry=None):
        self.db,self.clock=db,clock
        self.runner=create_runner(db.data_dir/'runs', interactive=True)
        if registry is not None and getattr(self.runner,'kind',None)=='native': self.runner.registry=registry
        self.lock=threading.RLock()
        self.sessions={}
        self.cancelled=OrderedDict()
        self.closed=False

    def start(self,pid,payload):
        require_native_consent(self.db.data_dir, self.runner)
        signature=digest({'mode':'interactive','problem_id':pid,'source_code':payload.source_code,'language':payload.language})
        with self.lock:
            if self.closed: raise HTTPException(503,'服务正在停止')
            if payload.request_id in self.cancelled: raise HTTPException(409,'这次运行已取消，请重新点击运行')
            with self.db.write() as conn:
                require_problem(conn,pid)
                old=conn.execute(select(m.runs).where(m.runs.c.request_id==payload.request_id)).mappings().first()
                if old:
                    if old['request_hash']!=signature: raise HTTPException(409,'此请求编号已用于不同的程序')
                    old_id=old['id']
                else:
                    require_environment(self.runner,payload.language)
                    if len(self.sessions)>=2: raise HTTPException(429,'最多同时运行两个交互终端，请先停止已有程序')
                    old_id=None
                    run_id=str(uuid4())
                    case={'id':'terminal:'+run_id,'name':'交互终端','stdin':'','expected_stdout':None,'comparison':'tokens'}
                    conn.execute(insert(m.runs).values(id=run_id,problem_id=pid,request_id=payload.request_id,
                        request_hash=signature,source_code=payload.source_code,tests_json=json.dumps([case]),
                        results_json=None,status='preparing',error=None,image_ref=self.runner.image_ref,language=payload.language,
                        created_at=utc_text(self.clock()),finished_at=None))
            if old_id: return self.get(old_id)
            session=TerminalSession(run_id,pid,payload.source_code,language=payload.language)
            self.sessions[run_id]=session
            threading.Thread(target=self._execute,args=(session,),daemon=True,name='terminal-'+run_id).start()
            return session.snapshot()

    def _execute(self,session):
        try:
            result=self.runner.execute(session)
        except PreparationError as exc:
            result={'status':exc.status,'error':str(exc)[:3000],'compile':exc.diagnostics,**exc.metadata,'exit_code':None,'duration_ms':0}
        except Exception as exc:
            result={'status':'failed','error':str(exc)[:3000],'exit_code':None,'duration_ms':0}
        try:
            with session.lock:
                session.accepting=False
                session.result=result
                session.metadata.update({key:result[key] for key in ('language','runtime_version','toolchain_id','compile','limits') if key in result})
                session.status=result['status']
                case={'id':'terminal:'+session.id,'name':'交互终端','stdin':session.stdin,'expected_stdout':None,'comparison':'tokens'}
                record={**case,'stdout':session.stdout,'stderr':session.stderr,**result}
                output={'results':[record],'python_version':session.python_version,**session.metadata,
                        'terminal':{**session.snapshot(),'input_requests':session.requests}}
            with self.db.write() as conn:
                conn.execute(update(m.runs).where(m.runs.c.id==session.id).values(
                    tests_json=json.dumps([case],ensure_ascii=False),results_json=json.dumps(output,ensure_ascii=False),
                    status=result['status'] if result['status'] in ('failed','compile_error','compile_time_limit','stopped') else 'completed',
                    runtime_version=session.metadata.get('runtime_version') or session.python_version,toolchain_id=session.metadata.get('toolchain_id'),
                    compile_json=json.dumps(session.metadata.get('compile'),ensure_ascii=False),limits_json=json.dumps(session.metadata.get('limits')),
                    error=result.get('error'),finished_at=utc_text(self.clock())))
        finally:
            session.finished.set()
            with self.lock: self.sessions.pop(session.id,None)

    def _stored(self,run_id):
        with self.db.engine.connect() as conn:
            row=conn.execute(select(m.runs).where(m.runs.c.id==run_id)).mappings().first()
            if not row or not json.loads(row['tests_json'])[0].get('id','').startswith('terminal:'):
                raise HTTPException(404,'交互终端不存在')
            return dict(row)

    def get(self,run_id):
        with self.lock: session=self.sessions.get(run_id)
        if session: return session.snapshot()
        row=self._stored(run_id)
        payload=json.loads(row['results_json']) if row['results_json'] else {}
        result=payload.get('terminal')
        if result: return {k:v for k,v in result.items() if k!='input_requests'}
        return {'id':run_id,'problem_id':row['problem_id'],'status':'interrupted','language':row['language'],'stdout':'','stderr':'','stdin':'',
                'transcript':'','input_closed':True,'python_version':None,'exit_code':None,'error':row['error'] or '服务已重启，请重新运行'}

    def send(self,run_id,payload):
        with self.lock: session=self.sessions.get(run_id)
        if session: return session.send(payload)
        row=self._stored(run_id)
        output=json.loads(row['results_json']) if row['results_json'] else {}
        previous=output.get('terminal',{}).get('input_requests',{}).get(payload.request_id)
        if previous:
            if previous!=digest({'text':payload.text,'eof':payload.eof}): raise HTTPException(409,'此输入编号已用于不同内容')
            return self.get(run_id)
        raise HTTPException(409,'程序已结束，请重新运行')

    def stop(self,run_id):
        with self.lock: session=self.sessions.get(run_id)
        if session:
            with session.lock:
                if session.status in ACTIVE: session.status='stopping'
                session.accepting=False
                session.stop_event.set()
            if not session.finished.wait(12): raise HTTPException(503,'程序正在停止，请稍后重试')
        return self.get(run_id)

    def stop_request(self,request_id):
        with self.lock:
            self.cancelled[request_id]=True
            self.cancelled.move_to_end(request_id)
            if len(self.cancelled)>2048: self.cancelled.popitem(last=False)
            with self.db.engine.connect() as conn:
                run_id=conn.execute(select(m.runs.c.id).where(m.runs.c.request_id==request_id)).scalar()
        return self.stop(run_id) if run_id else {'status':'not_started'}

    def close(self):
        if hasattr(self.runner, 'close'): self.runner.close()
        with self.lock:
            self.closed=True
            sessions=list(self.sessions.values())
        for session in sessions: session.stop_event.set()
        for session in sessions: session.finished.wait(15)
