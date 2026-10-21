"""Manual checklist progress must remain separate from recorded practice."""
from fastapi.testclient import TestClient

from app.backups import restore_backup
from app.main import create_app


def listed(client,pid,**params):
    return next(p for p in client.get('/api/v1/problems',params=params).json()['items'] if p['id']==pid)


def test_check_and_uncheck_without_creating_practice_or_review(loaded):
    c,_,_,pid=loaded
    initial=listed(c,pid)
    assert not initial['done']
    result=c.patch(f'/api/v1/problems/{pid}/state',json={'revision':0,'done':True})
    assert result.status_code==200,result.text
    assert result.json()['done'] is True and result.json()['revision']==1
    assert listed(c,pid,completion='done')['state_revision']==1
    assert c.get('/api/v1/problems',params={'completion':'todo'}).json()['count']==3
    result=c.patch(f'/api/v1/problems/{pid}/state',json={'revision':1,'done':False})
    assert result.status_code==200 and result.json()['done'] is False
    assert c.get('/api/v1/problems',params={'completion':'done'}).json()['count']==0
    detail=c.get(f'/api/v1/problems/{pid}').json()
    assert detail['done'] is False and detail['attempts']==[]
    assert detail['state']['review_enabled'] is False and detail['state']['next_review_date'] is None
    assert c.get('/api/v1/activity').json()['attempts']==0


def test_unchecking_preserves_existing_practice_and_review(loaded):
    c,_,_,pid=loaded
    before=c.post(f'/api/v1/problems/{pid}/attempts',json={'request_id':'historical','outcome':'independent'}).json()
    assert listed(c,pid)['done'] is True
    result=c.patch(f'/api/v1/problems/{pid}/state',json={'revision':before['state']['revision'],'done':False})
    assert result.status_code==200,result.text
    after=c.get(f'/api/v1/problems/{pid}').json()
    assert after['done'] is False and after['attempts']==[before['attempt']]
    assert after['state']['next_review_date']==before['state']['next_review_date']
    assert after['state']['review_enabled']==before['state']['review_enabled']
    c.post(f'/api/v1/problems/{pid}/attempts',json={'request_id':'new-practice','outcome':'independent'})
    assert listed(c,pid)['done'] is True


def test_stale_completion_write_cannot_undo_newer_state(loaded):
    c,_,_,pid=loaded
    first=c.patch(f'/api/v1/problems/{pid}/state',json={'revision':0,'favorite':True})
    assert first.status_code==200
    assert c.patch(f'/api/v1/problems/{pid}/state',json={'revision':0,'done':True}).status_code==409
    assert listed(c,pid)['done'] is False
    changed=c.patch(f'/api/v1/problems/{pid}/state',json={'revision':1,'done':True})
    assert changed.status_code==200 and changed.json()['favorite'] is True
    changed=c.patch(f'/api/v1/problems/{pid}/state',json={'revision':2,'favorite':False})
    assert changed.status_code==200 and changed.json()['done'] is True


def test_completion_survives_backup_restore_and_restart(loaded,tmp_path):
    c,app,_,pid=loaded
    assert c.patch(f'/api/v1/problems/{pid}/state',json={'revision':0,'done':True}).status_code==200
    archive=c.post('/api/v1/backups').json()['filename']
    target=tmp_path/'restored-checklist'
    restore_backup(app.state.db.data_dir/'backups'/archive,target)
    with TestClient(create_app(data_dir=target,bootstrap=False),base_url='http://127.0.0.1:8000') as restored:
        assert listed(restored,pid)['done'] is True
        assert listed(restored,pid)['state_revision']==1
        assert restored.get(f'/api/v1/problems/{pid}').json()['attempts']==[]
