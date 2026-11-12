from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import threading
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, insert, update

from .. import models as m
from ..learning import require_problem, utc_text
from .docker import DockerRunner
from .references import reference_for, GENERIC_TEMPLATE


def suite_for(conn,pid):
    row=conn.execute(select(m.test_suites).where(m.test_suites.c.problem_id==pid)).mappings().first()
    saved=json.loads(row['cases_json']) if row else {}
    if isinstance(saved,list): saved={'cases':saved}
    return {'revision':row['revision'] if row else 0,'cases':saved.get('cases',[]),'draft':saved.get('draft'),'updated_at':row['updated_at'] if row else None}


def acm_detail(db,pid):
    with db.engine.connect() as conn:
        require_problem(conn,pid)
        ref=reference_for(conn,pid)
        suite=suite_for(conn,pid)
    return {**suite,'reference':{k:v for k,v in ref.items() if k!='cases'} if ref else None,
            'builtin_cases':ref['cases'] if ref else [],'template':GENERIC_TEMPLATE,
            'contract_notice':'本地 ACM 约定；原题面中的函数参数需按此格式自行读取。' if ref else '本题尚未收录 ACM 约定和参考实现；可以自行定义 stdin/stdout 并保存测试。'}


def save_suite(db,pid,payload,now):
    with db.write() as conn:
        require_problem(conn,pid)
        current=suite_for(conn,pid)
        if current['revision']!=payload.revision: raise HTTPException(409,'测试用例已在其他页面更新，请保留当前输入后重新载入')
        cases=[]
        for case in payload.cases:
            record=case.model_dump()
            record['id']=record['id'] or str(uuid4())
            cases.append(record)
        draft=payload.draft.model_dump() if payload.draft else None
        values={'problem_id':pid,'revision':current['revision']+1,'cases_json':json.dumps({'cases':cases,'draft':draft},ensure_ascii=False),'updated_at':utc_text(now)}
        if current['revision']: conn.execute(update(m.test_suites).where(m.test_suites.c.problem_id==pid).values(**values))
        else: conn.execute(insert(m.test_suites).values(**values))
    return {'revision':values['revision'],'cases':cases,'draft':draft,'updated_at':values['updated_at']}


def run_dict(row,detail=False):
    result={k:v for k,v in dict(row).items() if k not in ('request_hash','source_code','tests_json','results_json')}
    payload=json.loads(row['results_json']) if row['results_json'] else None
    result.update({'language':'python','passed':sum(r.get('status')=='passed' for r in payload['results']) if payload else 0,
                   'total':len(json.loads(row['tests_json']))})
    if detail: result.update({'source_code':row['source_code'],'cases':json.loads(row['tests_json']),'results':payload['results'] if payload else [],'python_version':payload.get('python_version') if payload else None})
    return result


class RunService:
    def __init__(self,db,clock):
        self.db,self.clock=db,clock
        self.runner=DockerRunner(db.data_dir/'runs')
        self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='codetop-run')
        self.capacity=threading.BoundedSemaphore(8)
        with db.write() as conn:
            conn.execute(update(m.runs).where(m.runs.c.status.in_(['queued','running'])).values(status='interrupted',error='上次服务已停止，任务未完成；请重新运行。',finished_at=utc_text(clock())))

    def close(self):
        self.pool.shutdown(wait=True)

    def submit(self,pid,payload):
        canonical=json.dumps({'problem_id':pid,**payload.model_dump(exclude={'request_id'})},ensure_ascii=False,sort_keys=True)
        request_hash=hashlib.sha256(canonical.encode()).hexdigest()
        reserved=False
        try:
            with self.db.write() as conn:
                require_problem(conn,pid)
                old=conn.execute(select(m.runs).where(m.runs.c.request_id==payload.request_id)).mappings().first()
                if old:
                    if old['request_hash']!=request_hash: raise HTTPException(409,'此请求编号已用于不同的代码或测试')
                    return run_dict(old)
                if payload.mode=='suite':
                    cases=suite_for(conn,pid)['cases']
                else: cases=[case.model_dump() for case in payload.cases]
                if not cases: raise HTTPException(422,'本题没有已保存测试，请先添加自定义测试')
                if len(cases)>20: raise HTTPException(422,'全部测试超过 20 组，请减少自定义测试')
                if not self.capacity.acquire(blocking=False): raise HTTPException(429,'运行队列已满，请等待已有任务完成')
                reserved=True
                job_id=str(uuid4())
                values={'id':job_id,'problem_id':pid,'request_id':payload.request_id,'request_hash':request_hash,
                        'source_code':payload.source_code,'tests_json':json.dumps(cases,ensure_ascii=False),'results_json':None,
                        'status':'queued','error':None,'image_ref':self.runner.image_ref,'created_at':utc_text(self.clock()),'finished_at':None}
                conn.execute(insert(m.runs).values(**values))
            self.pool.submit(self._execute,job_id,payload.source_code,cases)
            return run_dict(values)
        except BaseException:
            if reserved: self.capacity.release()
            raise

    def _execute(self,job_id,source_code,cases):
        try:
            with self.db.write() as conn: conn.execute(update(m.runs).where(m.runs.c.id==job_id).values(status='running'))
            result=self.runner.execute(job_id,source_code,cases)
            with self.db.write() as conn:
                conn.execute(update(m.runs).where(m.runs.c.id==job_id).values(status='completed',results_json=json.dumps(result,ensure_ascii=False),finished_at=utc_text(self.clock())))
        except Exception as exc:
            with self.db.write() as conn:
                conn.execute(update(m.runs).where(m.runs.c.id==job_id).values(status='failed',error=str(exc)[:3000],finished_at=utc_text(self.clock())))
        finally: self.capacity.release()

    def get(self,job_id):
        with self.db.engine.connect() as conn:
            row=conn.execute(select(m.runs).where(m.runs.c.id==job_id)).mappings().first()
            if not row: raise HTTPException(404,'运行记录不存在')
            return run_dict(row,detail=True)

    def history(self,pid):
        with self.db.engine.connect() as conn:
            require_problem(conn,pid)
            rows=conn.execute(select(m.runs).where(m.runs.c.problem_id==pid).order_by(m.runs.c.created_at.desc(),m.runs.c.id).limit(20)).mappings()
            return [run_dict(row) for row in rows]
