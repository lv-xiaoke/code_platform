from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app


def attempt(c, pid, request_id, outcome='independent'):
    return c.post(f'/api/v1/problems/{pid}/attempts', json={'request_id': request_id, 'outcome': outcome, 'duration_seconds': 120})


def test_note_revision_and_restart(loaded):
    c, app, _, pid = loaded
    path = f'/api/v1/problems/{pid}/note/body'
    payload = {'revision': 0, 'body_md': '# 笔记'}
    assert c.put(path, json=payload).json()['revision'] == 1
    assert c.put(path, json=payload).status_code == 409
    second = create_app(data_dir=app.state.db.data_dir, bootstrap=False)
    with TestClient(second, base_url='http://127.0.0.1:8000') as restarted:
        assert restarted.get(f'/api/v1/problems/{pid}').json()['note']['body_md'] == '# 笔记'


def test_schedule_same_day_cross_day_pause_and_idempotency(loaded):
    c, app, now, pid = loaded
    assert attempt(c, pid, 'one').status_code == 200
    assert attempt(c, pid, 'one').json()['duplicate'] is True
    assert attempt(c, pid, 'two').json()['state']['review_step'] == 0
    assert c.get(f'/api/v1/problems/{pid}').json()['state']['next_review_date'] == '2026-10-22'
    now[0] += timedelta(days=1)
    assert c.get('/api/v1/reviews/due').json()['count'] == 1
    assert attempt(c, pid, 'three').json()['state']['review_step'] == 1
    assert attempt(c, pid, 'four', 'hint').json()['state']['review_step'] == -1
    assert attempt(c, pid, 'five').json()['state']['review_step'] == -1
    detail = c.get(f'/api/v1/problems/{pid}').json()
    state = detail['state']
    r = c.patch(f'/api/v1/problems/{pid}/state', json={'revision': state['revision'], 'review_enabled': False, 'mastery': 3})
    assert r.status_code == 200
    now[0] += timedelta(days=2)
    assert c.get('/api/v1/reviews/due').json()['count'] == 0
    assert attempt(c, pid, 'six').json()['state']['review_enabled'] is False
    assert len(c.get(f'/api/v1/problems/{pid}').json()['attempts']) == 6


def test_shanghai_midnight_and_highest_step(loaded):
    c, _, now, pid = loaded
    now[0] = datetime(2026, 10, 21, 15, 59, tzinfo=timezone.utc)
    attempt(c, pid, 'before')
    now[0] += timedelta(minutes=2)
    assert attempt(c, pid, 'after').json()['state']['review_step'] == 1
    for n in range(2, 8):
        now[0] += timedelta(days=1)
        state = attempt(c, pid, str(n)).json()['state']
    assert state['review_step'] == 4
    assert state['next_review_date'] == (now[0].astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai')).date() + timedelta(days=30)).isoformat()


def test_request_id_collision_state_conflict_and_legacy(loaded):
    c, _, _, pid = loaded
    attempt(c, pid, 'collision')
    other = next(p['id'] for p in c.get('/api/v1/problems').json()['items'] if p['id'] != pid)
    assert attempt(c, other, 'collision').status_code == 409
    assert attempt(c, pid, 'collision', 'hint').status_code == 409
    assert c.patch(f'/api/v1/problems/{pid}/state', json={'revision': 0, 'mastery': 2}).status_code == 409
    payload = {'notes': {'1681': {'content': '旧笔记'}}, 'progress': {'1681': {'done': True, 'mastery': 2}}}
    r = c.post('/api/v1/imports/preview', files={'file': ('legacy.json', __import__('json').dumps(payload).encode())}, data={'kind': 'legacy', 'source_name': 'algotop'})
    assert r.status_code == 200, r.text
    assert c.post(f"/api/v1/imports/{r.json()['id']}/apply").status_code == 200
    assert c.get(f'/api/v1/problems/{pid}').json()['note']['body_md'] == '旧笔记'


def test_concurrent_note_revisions_and_attempt_retries(loaded):
    from concurrent.futures import ThreadPoolExecutor
    c,_,_,pid=loaded
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda text:c.put(f'/api/v1/problems/{pid}/note/body',json={'revision':0,'body_md':text}),['tab one','tab two']))
    assert sorted(r.status_code for r in results)==[200,409]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:attempt(c,pid,'parallel'),range(2)))
    assert all(r.status_code==200 for r in results)
    assert sum(not r.json()['duplicate'] for r in results)==1
    assert len(c.get(f'/api/v1/problems/{pid}').json()['attempts'])==1
