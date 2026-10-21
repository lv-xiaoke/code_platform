import json
import threading
import time
from uuid import uuid4

from sqlalchemy import select, update

from app import models as m
from app.runner.service import RunService
from app.backups import restore_backup


class FakeRunner:
    image_ref='python@test-digest'
    def health(self): return {'available':True,'image_ref':self.image_ref}
    def execute(self,job_id,source_code,cases):
        return {'image_ref':self.image_ref,'python_version':'3.12','results':[{**c,'status':'passed','stdout':c.get('expected_stdout') or '', 'stderr':'','duration_ms':1,'exit_code':0} for c in cases]}


def wait(c,run_id):
    for _ in range(200):
        result=c.get('/api/v1/runs/'+run_id).json()
        if result['status'] not in ('queued','running'): return result
        time.sleep(.01)
    raise AssertionError('job did not finish')


def test_acm_contract_and_case_revisions(loaded):
    c,app,_,pid=loaded
    data=c.get(f'/api/v1/problems/{pid}/acm').json()
    assert data['reference']['display_id']=='3'
    assert data['reference']['source_record_id']=='1681'
    assert len(data['builtin_cases'])>=3 and data['revision']==0
    body={'revision':0,'cases':[{'id':'mine','name':'空输入','stdin':'','expected_stdout':'','comparison':'exact'}],'draft':{'name':'草稿','stdin':'abc','expected_stdout':None,'comparison':'tokens'}}
    r=c.put(f'/api/v1/problems/{pid}/test-cases',json=body)
    assert r.status_code==200,r.text
    assert r.json()['revision']==1 and r.json()['cases'][0]['expected_stdout']==''
    assert c.get(f'/api/v1/problems/{pid}/acm').json()['draft']['stdin']=='abc'
    assert c.put(f'/api/v1/problems/{pid}/test-cases',json=body).status_code==409
    other=next(p['id'] for p in c.get('/api/v1/problems').json()['items'] if p['display_id']=='补充题 9')
    assert c.get(f'/api/v1/problems/{other}/acm').json()['reference'] is None
    assert c.get('/api/v1/problems/missing/acm').status_code==404


def test_jobs_idempotency_history_backup_and_no_study_changes(loaded,tmp_path):
    c,app,_,pid=loaded
    app.state.run_service.runner=FakeRunner()
    body={'request_id':str(uuid4()),'source_code':'print(42)','mode':'custom','cases':[{'name':'mine','stdin':'','expected_stdout':'42','comparison':'tokens'}]}
    r=c.post(f'/api/v1/problems/{pid}/runs',json=body)
    assert r.status_code==202,r.text
    run_id=r.json()['id']
    assert c.post(f'/api/v1/problems/{pid}/runs',json=body).json()['id']==run_id
    assert c.post(f'/api/v1/problems/{pid}/runs',json={**body,'source_code':'print(43)'}).status_code==409
    result=wait(c,run_id)
    assert result['status']=='completed' and result['results'][0]['status']=='passed'
    assert result['source_code']=='print(42)'
    assert c.get(f'/api/v1/problems/{pid}/runs').json()[0]['id']==run_id
    assert c.get('/api/v1/activity').json()['attempts']==0
    assert c.get(f'/api/v1/problems/{pid}').json()['state']['revision']==0
    archive=c.post('/api/v1/backups').json()['filename']
    counts=restore_backup(app.state.db.data_dir/'backups'/archive,tmp_path/'restore')
    assert counts['code_runs']==1


def test_run_validation_and_suite_execution(loaded):
    c,app,_,pid=loaded
    app.state.run_service.runner=FakeRunner()
    base={'request_id':str(uuid4()),'source_code':'print(0)','mode':'suite'}
    r=c.post(f'/api/v1/problems/{pid}/runs',json=base)
    assert r.status_code==202,r.text
    assert len(wait(c,r.json()['id'])['results'])>=3
    for bad in [dict(base,request_id=str(uuid4()),language='javascript'),dict(base,request_id=str(uuid4()),mode='custom',cases=[]),dict(base,request_id=str(uuid4()),source_code='')]:
        assert c.post(f'/api/v1/problems/{pid}/runs',json=bad).status_code==422
    assert c.post('/api/v1/problems/missing/runs',json=base).status_code==404


def test_queue_capacity(loaded):
    c,app,_,pid=loaded
    ready=threading.Event()
    class BlockingRunner(FakeRunner):
        def execute(self,*args):
            ready.wait(10)
            return super().execute(*args)
    app.state.run_service.runner=BlockingRunner()
    payload={'source_code':'print(1)','mode':'custom','cases':[{'name':'one','stdin':'','expected_stdout':'1','comparison':'tokens'}]}
    try:
        jobs=[c.post(f'/api/v1/problems/{pid}/runs',json={**payload,'request_id':str(uuid4())}) for _ in range(8)]
        assert all(r.status_code==202 for r in jobs)
        assert c.post(f'/api/v1/problems/{pid}/runs',json={**payload,'request_id':str(uuid4())}).status_code==429
    finally: ready.set()
    for job in jobs: wait(c,job.json()['id'])


def test_restart_marks_only_unfinished_jobs_interrupted(loaded):
    c,app,_,pid=loaded
    app.state.run_service.runner=FakeRunner()
    payload={'source_code':'print(1)','mode':'custom','cases':[{'name':'one','stdin':'','expected_stdout':'1','comparison':'tokens'}]}
    jobs=[c.post(f'/api/v1/problems/{pid}/runs',json={**payload,'request_id':str(uuid4())}).json()['id'] for _ in range(3)]
    for job in jobs: wait(c,job)
    app.state.run_service.close()
    with app.state.db.write() as conn:
        for job,status in zip(jobs,['queued','running','completed']):
            conn.execute(update(m.runs).where(m.runs.c.id==job).values(status=status))
    app.state.run_service=RunService(app.state.db,app.state.clock)
    for job in jobs[:2]:
        result=c.get('/api/v1/runs/'+job).json()
        assert result['status']=='interrupted' and result['finished_at'] and result['error']
    assert c.get('/api/v1/runs/'+jobs[2]).json()['status']=='completed'
