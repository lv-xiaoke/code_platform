import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from conftest import load
from app import models as m
from app.imports import preview_import, apply_import
from sqlalchemy import select, func


def test_actual_snapshot_counts_and_references(env):
    _, app, now = env
    path = Path(__file__).resolve().parents[2] / 'vendor/algoTop-main/public/data/codetop.json'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == 'BC496564C4939EAE1173636DEC05B358B0A46B0B6DD1797D3FF10416DBC81AC9'
    result = preview_import(app.state.db,raw,'algotop','algotop',now[0])
    assert result['questions'] == 1153
    assert result['missing_content'] == 21
    assert result['missing_url'] == 7
    apply_import(app.state.db,result['id'],now[0])
    with app.state.db.engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(m.stats)).scalar() == 21906
        assert conn.exec_driver_sql('PRAGMA foreign_key_check').all() == []
        for typ,count in [('company',22),('department',571),('job',8),('tag',38)]:
            assert conn.execute(select(func.count()).select_from(m.taxonomies).where(m.taxonomies.c.type==typ,m.taxonomies.c.is_internal==0)).scalar() == count


def test_apply_failure_rolls_back_every_table(loaded,snapshot,monkeypatch):
    c,app,now,pid = loaded
    updated=copy.deepcopy(snapshot)
    updated['questions']['1681']['title']='new title'
    p=preview_import(app.state.db,json.dumps(updated).encode(),'algotop','algotop',now[0])
    from sqlalchemy import event
    def fail(conn,cursor,statement,parameters,context,executemany):
        if statement.startswith('INSERT INTO scope_stats'): raise ValueError('simulated interrupted import')
    event.listen(app.state.db.engine,'before_cursor_execute',fail)
    try:
        import pytest
        with pytest.raises(ValueError): apply_import(app.state.db,p['id'],now[0])
    finally: event.remove(app.state.db.engine,'before_cursor_execute',fail)
    assert len(c.get('/api/v1/catalog/datasets').json())==1
    assert c.get(f'/api/v1/problems/{pid}').json()['title']=='最长子串'


def test_first_practice_enables_review_after_mastery_mark(loaded):
    c,_,_,pid=loaded
    assert c.patch(f'/api/v1/problems/{pid}/state',json={'revision':0,'mastery':2}).status_code==200
    r=c.post(f'/api/v1/problems/{pid}/attempts',json={'request_id':'first-after-mastery','outcome':'independent'})
    assert r.json()['state']['review_enabled'] is True


def test_unsafe_manual_url_rejected(env):
    c,_,_=env
    raw='platform,display_id,title,difficulty,url\nmanual,x,X,easy,javascript:alert(1)\n'
    r=c.post('/api/v1/imports/preview',files={'file':('bad.csv',raw.encode())},data={'kind':'manual','source_name':'my-list'})
    assert r.status_code==422
