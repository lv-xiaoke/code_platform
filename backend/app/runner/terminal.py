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
from .terminal_docker import InteractiveDockerRunner

LIMIT=65536
ACTIVE={'starting','running','stopping'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class TerminalSession:
    def __init__(self,run_id,pid,source):
        self.id,self.problem_id,self.source_code=run_id,pid,source
        self.lock=threading.RLock()
        self.inputs=queue.Queue()
        self.stop_event=threading.Event()
        self.finished=threading.Event()
        self.status='starting'
        self.stdout=self.stderr=self.stdin=self.transcript=''
        self.python_version=None
        self.input_closed=False
        self.accepting=True
        self.output_bytes=0
        self.requests={}
        self.result={}

    def emit(self,event):
        with self.lock:
            if event['type']=='ready':
                self.python_version=event.get('python_version')
                if not self.stop_event.is_set(): self.status='running'
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
            return {'id':self.id,'problem_id':self.problem_id,'status':self.status,
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
    def __init__(self,db,clock):
        self.db,self.clock=db,clock
        self.runner=InteractiveDockerRunner(db.data_dir/'runs')
        self.lock=threading.RLock()
        self.sessions={}
        self.cancelled=OrderedDict()
        self.closed=False

    def start(self,pid,payload):
        signature=digest({'mode':'interactive','problem_id':pid,'source_code':payload.source_code})
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
                    if len(self.sessions)>=2: raise HTTPException(429,'最多同时运行两个交互终端，请先停止已有程序')
                    old_id=None
                    run_id=str(uuid4())
                    case={'id':'terminal:'+run_id,'name':'交互终端','stdin':'','expected_stdout':None,'comparison':'tokens'}
                    conn.execute(insert(m.runs).values(id=run_id,problem_id=pid,request_id=payload.request_id,
                        request_hash=signature,source_code=payload.source_code,tests_json=json.dumps([case]),
                        results_json=None,status='running',error=None,image_ref=self.runner.image_ref,
                        created_at=utc_text(self.clock()),finished_at=None))
            if old_id: return self.get(old_id)
            session=TerminalSession(run_id,pid,payload.source_code)
            self.sessions[run_id]=session
            threading.Thread(target=self._execute,args=(session,),daemon=True,name='terminal-'+run_id).start()
            return session.snapshot()

    def _execute(self,session):
        try:
            result=self.runner.execute(session)
        except Exception as exc:
            result={'status':'failed','error':str(exc)[:3000],'exit_code':None,'duration_ms':0}
        try:
            with session.lock:
                session.accepting=False
                session.result=result
                session.status=result['status']
                case={'id':'terminal:'+session.id,'name':'交互终端','stdin':session.stdin,'expected_stdout':None,'comparison':'tokens'}
                record={**case,'stdout':session.stdout,'stderr':session.stderr,**result}
                output={'results':[record],'python_version':session.python_version,
                        'terminal':{**session.snapshot(),'input_requests':session.requests}}
            with self.db.write() as conn:
                conn.execute(update(m.runs).where(m.runs.c.id==session.id).values(
                    tests_json=json.dumps([case],ensure_ascii=False),results_json=json.dumps(output,ensure_ascii=False),
                    status='failed' if result['status']=='failed' else 'completed',error=result.get('error'),finished_at=utc_text(self.clock())))
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
        return {'id':run_id,'problem_id':row['problem_id'],'status':'interrupted','stdout':'','stderr':'','stdin':'',
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
        with self.lock:
            self.closed=True
            sessions=list(self.sessions.values())
        for session in sessions: session.stop_event.set()
        for session in sessions: session.finished.wait(15)
