from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.backups import restore_backup
from app.db import Database
from app.main import create_app


def save(c, pid, revision, code, language='python'):
    response = c.put(f'/api/v1/problems/{pid}/note', json={
        'revision': revision, 'body_md': '保留思路', 'code_text': code, 'language': language})
    assert response.status_code == 200, response.text
    return response.json()


def rewrite(c, pid, revision, history_id=None):
    return c.post(f'/api/v1/problems/{pid}/code/rewrite', json={
        'revision': revision, 'history_id': history_id})


def history(c, pid):
    response = c.get(f'/api/v1/problems/{pid}/code/history')
    assert response.status_code == 200, response.text
    return response.json()


def test_rewrite_archives_versions_and_restart_keeps_draft(loaded):
    c, app, now, pid = loaded
    assert history(c, pid) == []
    save(c, pid, 0, 'print(1)')
    first = rewrite(c, pid, 1)
    assert first.status_code == 200, first.text
    assert first.json()['code_text'] == ''
    assert first.json()['body_md'] == '保留思路'
    save(c, pid, 2, 'print(2)')
    now[0] += timedelta(seconds=1)
    assert rewrite(c, pid, 3).status_code == 200
    versions = history(c, pid)
    assert [v['code_text'] for v in versions] == ['print(2)', 'print(1)']
    assert versions[0]['created_at'] > versions[1]['created_at']
    save(c, pid, 4, 'unfinished = 3')
    with TestClient(create_app(data_dir=app.state.db.data_dir, bootstrap=False),
                    base_url='http://127.0.0.1:8000') as restarted:
        assert history(restarted, pid) == versions
        assert restarted.get(f'/api/v1/problems/{pid}').json()['note']['code_text'] == 'unfinished = 3'


def test_blank_rewrite_does_not_create_history(loaded):
    c, _, _, pid = loaded
    assert rewrite(c, pid, 0).status_code == 200
    save(c, pid, 1, ' \n\t')
    assert rewrite(c, pid, 2).status_code == 200
    assert history(c, pid) == []


def test_restore_archives_current_and_keeps_original_history_immutable(loaded):
    c, _, _, pid = loaded
    save(c, pid, 0, 'console.log(1)', 'javascript')
    assert rewrite(c, pid, 1).status_code == 200
    original = history(c, pid)[0]
    save(c, pid, 2, 'print(2)')
    response = rewrite(c, pid, 3, original['id'])
    assert response.status_code == 200, response.text
    assert response.json()['code_text'] == 'console.log(1)'
    assert response.json()['language'] == 'javascript'
    assert response.json()['body_md'] == '保留思路'
    versions = history(c, pid)
    assert versions[0]['code_text'] == 'print(2)'
    assert versions[1] == original


def test_stale_rewrite_cannot_clear_or_archive_newer_code(loaded):
    c, _, _, pid = loaded
    save(c, pid, 0, 'newer code')
    assert rewrite(c, pid, 0).status_code == 409
    assert history(c, pid) == []
    assert c.get(f'/api/v1/problems/{pid}').json()['note']['code_text'] == 'newer code'


def test_parallel_rewrites_archive_only_once(loaded):
    from concurrent.futures import ThreadPoolExecutor
    c, _, _, pid = loaded
    save(c, pid, 0, 'keep me')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: rewrite(c, pid, 1), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert [v['code_text'] for v in history(c, pid)] == ['keep me']


def test_invalid_or_other_problem_history_preserves_current_code(loaded):
    c, _, _, pid = loaded
    save(c, pid, 0, 'original')
    assert rewrite(c, pid, 1).status_code == 200
    version = history(c, pid)[0]
    other = next(p['id'] for p in c.get('/api/v1/problems').json()['items'] if p['id'] != pid)
    save(c, other, 0, 'other draft')
    for history_id in [version['id'], 999999]:
        assert rewrite(c, other, 1, history_id).status_code == 404
    assert history(c, other) == []
    assert c.get(f'/api/v1/problems/{other}').json()['note']['code_text'] == 'other draft'
    assert c.get('/api/v1/problems/missing/code/history').status_code == 404
    assert rewrite(c, 'missing', 0).status_code == 404


def test_archive_and_clear_roll_back_together(loaded):
    c, app, _, pid = loaded
    save(c, pid, 0, 'must survive')

    def fail_update(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('UPDATE notes'):
            raise RuntimeError('simulated storage failure')

    event.listen(app.state.db.engine, 'before_cursor_execute', fail_update)
    try:
        with pytest.raises(RuntimeError, match='simulated storage failure'):
            rewrite(c, pid, 1)
    finally:
        event.remove(app.state.db.engine, 'before_cursor_execute', fail_update)
    assert history(c, pid) == []
    assert c.get(f'/api/v1/problems/{pid}').json()['note']['code_text'] == 'must survive'


def test_history_survives_full_backup_restore(loaded, tmp_path):
    c, app, _, pid = loaded
    save(c, pid, 0, 'archived code')
    assert rewrite(c, pid, 1).status_code == 200
    save(c, pid, 2, 'current draft')
    backup = c.post('/api/v1/backups')
    assert backup.status_code == 200, backup.text
    assert backup.json()['counts']['code_history'] == 1
    dest = tmp_path / 'restored-history'
    restore_backup(app.state.db.data_dir / 'backups' / backup.json()['filename'], dest)
    with TestClient(create_app(data_dir=dest, bootstrap=False), base_url='http://127.0.0.1:8000') as restored:
        assert history(restored, pid)[0]['code_text'] == 'archived code'
        assert restored.get(f'/api/v1/problems/{pid}').json()['note']['code_text'] == 'current draft'


def test_upgrade_0002_preserves_existing_code_and_creates_backup(tmp_path):
    from alembic import command
    from alembic.config import Config
    from app.db import ROOT
    db = Database(tmp_path / 'old-schema')
    config = Config()
    config.set_main_option('script_location', str(ROOT / 'backend' / 'migrations'))
    with db.engine.begin() as conn:
        config.attributes['connection'] = conn
        command.upgrade(config, '0002')
        conn.exec_driver_sql("INSERT INTO problems VALUES ('p',NULL,NULL,'standard','now')")
        conn.exec_driver_sql("INSERT INTO notes VALUES ('p','notes','old code','python',1,'now')")
    db.migrate()
    with db.engine.connect() as conn:
        assert conn.exec_driver_sql('SELECT code_text FROM notes').scalar() == 'old code'
        assert conn.exec_driver_sql('SELECT count(*) FROM code_history').scalar() == 0
    assert list((db.data_dir / 'backups').glob('*before-migration*.zip'))
    db.engine.dispose()
