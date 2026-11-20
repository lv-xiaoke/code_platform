import json
from pathlib import Path
import time
from uuid import uuid4

from sqlalchemy import select, func

from app import models as m


def finished(client, run_id):
    for _ in range(400):
        value = client.get('/api/v1/runs/' + run_id).json()
        if value['status'] not in ('queued', 'preparing', 'compiling', 'running'): return value
        time.sleep(.02)
    raise AssertionError('run did not finish')


def test_same_source_different_language_does_not_reuse_request(loaded, tmp_path):
    from app.runner.native import NativeRunner
    from app.runner.toolchains.registry import ToolchainRegistry
    from app.runner.consent import accept_native_execution
    c, app, _, pid = loaded
    registry = ToolchainRegistry(Path(__file__).resolve().parents[2] / 'runtime/toolchains-ci')
    app.state.run_service.runner = NativeRunner(tmp_path / 'runs', registry=registry)
    try:
        accept_native_execution(app.state.db.data_dir)
        body = dict(request_id=str(uuid4()), source_code='print(1)', language='python', mode='custom', cases=[{'stdin': ''}])
        first = c.post(f'/api/v1/problems/{pid}/runs', json=body)
        assert first.status_code == 202, first.text
        collision = c.post(f'/api/v1/problems/{pid}/runs', json={**body, 'language': 'javascript'})
        assert collision.status_code == 409
        run = finished(c, first.json()['id'])
        assert run['language'] == 'python'
        assert run['runtime_version'].startswith('3.12.')
        assert run['toolchain_id']
        assert run['limits']['memory_mb'] == 256
        assert c.get(f'/api/v1/problems/{pid}/runs?language=java').json() == []
    finally:
        registry.close()


def test_missing_environment_creates_no_run(loaded, tmp_path):
    from app.runner.native import NativeRunner
    from app.runner.toolchains.registry import ToolchainRegistry
    from app.runner.consent import accept_native_execution
    c, app, _, pid = loaded
    registry = ToolchainRegistry(tmp_path / 'empty')
    app.state.run_service.runner = NativeRunner(tmp_path / 'runs', registry=registry)
    try:
        accept_native_execution(app.state.db.data_dir)
        response = c.post(f'/api/v1/problems/{pid}/runs', json=dict(request_id=str(uuid4()),
            source_code='console.log(1)', language='javascript', cases=[{'stdin': ''}]))
        assert response.status_code == 409
        assert response.json()['detail']['state'] == 'unprepared'
        with app.state.db.engine.connect() as conn:
            assert conn.execute(select(func.count()).select_from(m.runs)).scalar() == 0
    finally:
        registry.close()


def test_ai_run_context_has_language_compile_diagnostics_and_version(loaded):
    from app.ai.schemas import Ask
    c, app, now, pid = loaded
    run_id = str(uuid4())
    with app.state.db.write() as conn:
        conn.execute(m.runs.insert().values(id=run_id, problem_id=pid, request_id='compile-failure', request_hash='a',
            source_code='class Main {', tests_json='[]', status='compile_error', language='java',
            runtime_version='21.0.13+9', toolchain_id='temurin-reviewed',
            compile_json=json.dumps({'stderr': 'Main.java: missing brace'}), created_at=now[0].isoformat()))
    context = app.state.ai_service.context(pid, Ask(request_id=str(uuid4()), question='解释错误', run_id=run_id))
    assert context['run']['language'] == 'java'
    assert context['run']['runtime_version'] == '21.0.13+9'
    assert context['run']['compile']['stderr'] == 'Main.java: missing brace'


def test_stop_batch_marks_run_stopped_and_releases_slot(loaded, tmp_path):
    from app.runner.native import NativeRunner
    from app.runner.consent import accept_native_execution
    c, app, _, pid = loaded
    app.state.run_service.runner = NativeRunner(tmp_path / 'runs')
    accept_native_execution(app.state.db.data_dir)
    request_id = str(uuid4())
    response = c.post(f'/api/v1/problems/{pid}/runs', json=dict(request_id=request_id,
        source_code='import time;time.sleep(20)', cases=[{'stdin': ''}]))
    assert response.status_code == 202
    time.sleep(.2)
    assert c.post('/api/v1/run-requests/' + request_id + '/stop').status_code == 200
    assert finished(c, response.json()['id'])['status'] == 'stopped'


def test_cancel_between_check_and_insert_never_executes(loaded, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from sqlalchemy import event
    from app.runner.native import NativeRunner
    from app.runner.consent import accept_native_execution
    c, app, _, pid = loaded
    app.state.run_service.runner=NativeRunner(tmp_path/'runs')
    accept_native_execution(app.state.db.data_dir)
    inserting, proceed=threading.Event(),threading.Event()
    def barrier(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO code_runs'):
            inserting.set()
            assert proceed.wait(5)
    event.listen(app.state.db.engine,'before_cursor_execute',barrier)
    request_id=str(uuid4())
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(lambda:c.post(f'/api/v1/problems/{pid}/runs',json=dict(request_id=request_id,
                source_code='print("must not execute")',cases=[{'stdin':''}])))
            try:
                assert inserting.wait(3)
                assert c.post('/api/v1/run-requests/'+request_id+'/stop').status_code==200
            finally:
                proceed.set()
            response=future.result(timeout=5)
        assert response.status_code==202
        result=finished(c,response.json()['id'])
        assert result['status']=='stopped',result
        assert not result['results']
    finally:
        event.remove(app.state.db.engine,'before_cursor_execute',barrier)


def test_ai_masks_infrastructure_paths_but_keeps_local_diagnostics(loaded, monkeypatch):
    from app.ai.schemas import Ask
    from app.paths import toolchains_dir
    c,app,now,pid=loaded
    prefix=str(toolchains_dir())
    diagnostic=prefix+'/llvm/include/c++/v1/vector: no matching constructor'
    run_id=str(uuid4())
    with app.state.db.write() as conn:
        conn.execute(m.runs.insert().values(id=run_id,problem_id=pid,request_id=run_id,request_hash='hash',
            source_code='std::vector<int> x("bad");',tests_json='[]',language='cpp',status='compile_error',
            error=diagnostic,compile_json=json.dumps({'stderr':diagnostic}),created_at=now[0].isoformat()))
    context=app.state.ai_service.context(pid,Ask(request_id=str(uuid4()),question='why',run_id=run_id,include_history=True))
    assert prefix not in context['run']['compile']['stderr']
    assert prefix not in context['run']['error']
    assert prefix not in context['recent_runs'][0]['error']
    assert 'vector: no matching constructor' in context['run']['compile']['stderr']
    local=c.get('/api/v1/runs/'+run_id).json()
    assert local['compile']['stderr']==diagnostic
