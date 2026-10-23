import json
import queue
import time
from uuid import uuid4

from app import models as m
from sqlalchemy import select


def wait_terminal(c,run_id,predicate=None,timeout=12):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        response=c.get('/api/v1/terminals/'+run_id)
        assert response.status_code==200,response.text
        result=response.json()
        if predicate(result) if predicate else result['status'] not in ('starting','running','stopping'):
            return result
        time.sleep(.02)
    raise AssertionError('terminal did not reach expected state: '+str(result))


class FakeTerminalRunner:
    image_ref='python@test-terminal'
    def execute(self,session):
        session.emit({'type':'ready','python_version':'3.12'})
        session.emit({'type':'stdout','text':'输入：'})
        while not session.stop_event.is_set():
            try: message=session.inputs.get(timeout=.02)
            except queue.Empty: continue
            if message['eof']: break
            session.emit({'type':'stdout','text':'收到 '+message['text']})
        return {'status':'stopped' if session.stop_event.is_set() else 'executed','exit_code':0,'duration_ms':1}


def start(c,pid,source='print(input())',request_id=None):
    response=c.post(f'/api/v1/problems/{pid}/terminals',json={'request_id':request_id or str(uuid4()),'source_code':source})
    assert response.status_code==202,response.text
    return response.json()


def test_terminal_waits_streams_multiple_lines_and_persists_history(loaded):
    c,app,_,pid=loaded
    app.state.terminal_service.runner=FakeTerminalRunner()
    run=start(c,pid)
    active=wait_terminal(c,run['id'],lambda r:'输入：' in r['transcript'])
    assert active['status']=='running' and active['stdout']=='输入：'
    for line in ['你好\n','第二行\n']:
        response=c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'text':line})
        assert response.status_code==200,response.text
    wait_terminal(c,run['id'],lambda r:'收到 第二行' in r['stdout'])
    c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'eof':True})
    final=wait_terminal(c,run['id'])
    assert final['status']=='executed' and final['input_closed']
    assert final['stdin']=='你好\n第二行\n'
    record=c.get('/api/v1/runs/'+run['id']).json()
    assert record['source_code']=='print(input())'
    assert record['cases'][0]['stdin']==final['stdin']
    assert record['results'][0]['stdout']==final['stdout']
    assert c.get('/api/v1/activity').json()['attempts']==0
    assert c.get(f'/api/v1/problems/{pid}/acm').json()['revision']==0


def test_start_and_input_retries_are_idempotent(loaded):
    c,app,_,pid=loaded
    app.state.terminal_service.runner=FakeTerminalRunner()
    request_id=str(uuid4())
    run=start(c,pid,request_id=request_id)
    assert start(c,pid,request_id=request_id)['id']==run['id']
    assert c.post(f'/api/v1/problems/{pid}/terminals',json={'request_id':request_id,'source_code':'print(2)'}).status_code==409
    body={'request_id':str(uuid4()),'text':'once\n'}
    for _ in range(2): assert c.post('/api/v1/terminals/'+run['id']+'/input',json=body).status_code==200
    assert c.post('/api/v1/terminals/'+run['id']+'/input',json={**body,'text':'different\n'}).status_code==409
    c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'eof':True})
    final=wait_terminal(c,run['id'])
    assert final['stdin']=='once\n'
    assert final['stdout'].count('收到 once')==1
    assert c.post('/api/v1/terminals/'+run['id']+'/input',json=body).status_code==200


def test_stop_capacity_and_invalid_requests(loaded):
    c,app,_,pid=loaded
    app.state.terminal_service.runner=FakeTerminalRunner()
    first,second=start(c,pid),start(c,pid)
    full=c.post(f'/api/v1/problems/{pid}/terminals',json={'request_id':str(uuid4()),'source_code':'x=1'})
    assert full.status_code==429
    for run in [first,second]:
        assert c.post('/api/v1/terminals/'+run['id']+'/stop').status_code==200
        assert wait_terminal(c,run['id'])['status']=='stopped'
        assert c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'text':'late\n'}).status_code==409
    assert c.post('/api/v1/problems/missing/terminals',json={'request_id':str(uuid4()),'source_code':'print(1)'}).status_code==404
    assert c.post(f'/api/v1/problems/{pid}/terminals',json={'request_id':str(uuid4()),'source_code':' '}).status_code==422
    assert c.get('/api/v1/terminals/missing').status_code==404


def test_terminal_input_budget_and_eof_validation(loaded):
    c,app,_,pid=loaded
    class QuietRunner(FakeTerminalRunner):
        def execute(self,session):
            session.emit({'type':'ready'})
            session.stop_event.wait(10)
            return {'status':'stopped','exit_code':0,'duration_ms':1}
    app.state.terminal_service.runner=QuietRunner()
    run=start(c,pid)
    assert c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'text':'x'*65536}).status_code==200
    assert c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'text':'x'}).status_code==422
    assert c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'text':'x','eof':True}).status_code==422
    c.post('/api/v1/terminals/'+run['id']+'/stop')


def test_cancel_pending_start_prevents_a_late_request_from_running(loaded):
    c,app,_,pid=loaded
    app.state.terminal_service.runner=FakeTerminalRunner()
    request_id=str(uuid4())
    assert c.post('/api/v1/terminal-requests/'+request_id+'/stop').status_code==200
    assert c.post(f'/api/v1/problems/{pid}/terminals',json={'request_id':request_id,'source_code':'print(1)'}).status_code==409
    assert c.post(f'/api/v1/problems/{pid}/terminals',headers={'Origin':'https://other.test'},json={'request_id':str(uuid4()),'source_code':'print(1)'}).status_code==403
