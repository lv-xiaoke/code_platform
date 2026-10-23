import json
import threading
import time
from uuid import uuid4

from sqlalchemy import select
from app import models as m


def wait_chat(c, pid):
    for _ in range(200):
        chat = c.get(f'/api/v1/problems/{pid}/ai').json()
        if not chat.get('busy'): return chat
        time.sleep(.01)
    raise AssertionError('AI did not finish')


def ask(c, pid, **extra):
    return c.post(f'/api/v1/problems/{pid}/ai', json={
        'request_id': str(uuid4()), 'question': '给一点提示', 'code': 'draft = 123', **extra})


def configure(c):
    response = c.put('/api/v1/ai/settings', json={'api_key':'sk-test-secret-1234','model':'deepseek-flash'})
    assert response.status_code == 200, response.text
    return response


def test_settings_encrypt_key_and_missing_key_keeps_chat_empty(loaded):
    c, app, _, pid = loaded
    status = c.get('/api/v1/ai/settings')
    assert status.status_code == 200
    assert not status.json()['configured']
    assert ask(c, pid).status_code == 409
    assert c.get(f'/api/v1/problems/{pid}/ai').json()['messages'] == []
    result = configure(c)
    assert 'sk-test-secret' not in result.text and result.json()['configured']
    secret = app.state.db.data_dir/'ai-key.dpapi'
    assert b'sk-test-secret' not in secret.read_bytes()
    with app.state.db.engine.connect() as conn:
        assert 'sk-test-secret' not in str(conn.execute(select(m.settings)).all())
    from app.backups import create_backup
    import zipfile
    backup=create_backup(app.state.db)
    with zipfile.ZipFile(app.state.db.data_dir/'backups'/backup['filename']) as archive:
        assert not any('ai-key' in name for name in archive.namelist())
    assert c.put('/api/v1/ai/settings',json={'api_key':'','model':'deepseek-v4-pro'}).json()['configured']
    assert c.put('/api/v1/ai/settings',json={'model':'fake'}).status_code == 422
    invalid=c.put('/api/v1/ai/settings',json={'api_key':'sk-do-not-echo\nsecret'})
    assert invalid.status_code==422 and 'sk-do-not-echo' not in invalid.text


def test_stream_context_and_retry_idempotence(loaded):
    c, app, _, pid = loaded
    configure(c)
    captured = []
    gate = threading.Event()
    def stream(key, model, messages, stop):
        captured.append(messages)
        yield '先看'
        gate.wait(2)
        yield '窗口边界。'
    app.state.ai_service.provider.stream = stream
    request_id = str(uuid4())
    response = ask(c, pid, request_id=request_id)
    assert response.status_code == 202, response.text
    for _ in range(100):
        partial = c.get(f'/api/v1/problems/{pid}/ai').json()
        if partial['messages'][-1]['content']: break
        time.sleep(.01)
    assert partial['messages'][-1]['content'] == '先看'
    assert ask(c, pid, request_id=request_id).status_code == 202
    assert ask(c, pid, request_id=request_id, question='different').status_code == 409
    assert ask(c, pid).status_code == 409
    gate.set()
    final = wait_chat(c, pid)
    assert final['messages'][-1]['content'] == '先看窗口边界。'
    assert len(captured) == 1
    context = json.loads(captured[0][-1]['content'])
    assert context['code'] == 'draft = 123' and '题面' in context['statement']
    assert 'notes' not in context and 'run' not in context
    assert ask(c, pid, request_id=request_id).status_code == 202
    assert len(c.get(f'/api/v1/problems/{pid}/ai').json()['messages']) == 2
    assert c.get('/api/v1/activity').json()['attempts'] == 0


def test_cancel_failure_and_separate_problem_history(loaded):
    c, app, _, pid = loaded
    configure(c)
    def stream(key, model, messages, stop):
        yield 'partial'
        stop.wait(2)
        yield 'must not appear'
    app.state.ai_service.provider.stream = stream
    assert ask(c, pid).status_code == 202
    response = c.post(f'/api/v1/problems/{pid}/ai/stop')
    assert response.status_code == 200
    final = wait_chat(c, pid)
    assert final['messages'][-1]['status'] == 'stopped'
    assert 'must not appear' not in final['messages'][-1]['content']
    other = next(p['id'] for p in c.get('/api/v1/problems').json()['items'] if p['id'] != pid)
    assert c.get(f'/api/v1/problems/{other}/ai').json()['messages'] == []
    assert ask(c, pid, code='x'*65537).status_code == 422
    assert c.post(f'/api/v1/problems/{pid}/ai',json={'request_id':str(uuid4()),'question':'hi'},headers={'Origin':'http://evil.test'}).status_code == 403
    assert ask(c, 'missing').status_code == 404


def test_run_analysis_uses_submitted_code_and_optional_notes(loaded):
    c, app, now, pid = loaded
    configure(c)
    run_id = str(uuid4())
    with app.state.db.write() as conn:
        conn.execute(m.runs.insert().values(id=run_id,problem_id=pid,request_id=str(uuid4()),request_hash='x',source_code='print(1/0)',tests_json='[{"stdin":"old input"}]',results_json='{"results":[{"stderr":"ZeroDivisionError"}]}',status='completed',created_at=now[0].isoformat()))
    captured = []
    def stream(key, model, messages, stop):
        captured.append(messages)
        yield '检查除数'
    app.state.ai_service.provider.stream = stream
    assert ask(c, pid, run_id=run_id, include_code=False, notes='my private note').status_code == 202
    wait_chat(c, pid)
    context = json.loads(captured[-1][-1]['content'])
    assert context['run']['source_code'] == 'print(1/0)'
    assert 'code' not in context and context['notes'] == 'my private note'
    assert ask(c, pid, run_id='missing').status_code == 404
    assert ask(c, pid, question=' ', code='').status_code == 422


def test_global_capacity_and_no_auto_requests(loaded):
    c,app,_,pid=loaded
    configure(c)
    calls=[]
    def stream(key,model,messages,stop):
        calls.append(1)
        stop.wait(3)
        yield 'done'
    app.state.ai_service.provider.stream=stream
    problems=c.get('/api/v1/problems').json()['items']
    others=[row['id'] for row in problems if row['id']!=pid]
    c.get('/api/v1/ai/settings');c.get(f'/api/v1/problems/{pid}/ai')
    assert not calls
    assert ask(c,pid).status_code==202
    assert ask(c,others[0]).status_code==202
    assert ask(c,others[1]).status_code==429
    c.post(f'/api/v1/problems/{pid}/ai/stop')
    c.post(f'/api/v1/problems/{others[0]}/ai/stop')
    wait_chat(c,pid);wait_chat(c,others[0])

