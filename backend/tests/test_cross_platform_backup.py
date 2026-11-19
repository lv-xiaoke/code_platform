import json
import zipfile
from fastapi.testclient import TestClient
from app.main import create_app
from app.backups import create_backup, restore_backup, inspect_database


def test_backup_preserves_learning_at_unrelated_path(loaded, tmp_path):
    c, app, _, pid = loaded
    assert c.put(f'/api/v1/problems/{pid}/note', json={
        'revision': 0, 'body_md': '跨平台笔记', 'code_text': 'print("历史")'}).status_code == 200
    assert c.post(f'/api/v1/problems/{pid}/code/rewrite', json={'revision': 1}).status_code == 200
    state = c.get(f'/api/v1/problems/{pid}').json()['state']
    assert c.patch(f'/api/v1/problems/{pid}/state', json={
        'revision': state['revision'], 'favorite': True}).status_code == 200
    before = c.get(f'/api/v1/problems/{pid}').json()
    versions = c.get(f'/api/v1/problems/{pid}/code/history').json()
    backup = create_backup(app.state.db)
    archive = app.state.db.data_dir / 'backups' / backup['filename']
    with zipfile.ZipFile(archive) as bundle:
        assert not any('key' in name.lower() or 'consent' in name.lower() for name in bundle.namelist())
    target = tmp_path / '另一台电脑 中文' / 'data'
    restore_backup(archive, target)
    counts, _ = inspect_database(target / 'study.sqlite3')
    assert counts['problems'] == 4
    with TestClient(create_app(data_dir=target, bootstrap=False), base_url='http://127.0.0.1:8000') as restored:
        after = restored.get(f'/api/v1/problems/{pid}').json()
        assert after['note'] == before['note']
        assert after['state'] == before['state']
        assert restored.get(f'/api/v1/problems/{pid}/code/history').json() == versions


def test_exchange_fixture_checks_database_contents(loaded, tmp_path):
    from scripts.backup_exchange import database_summary, import_fixture
    import shutil
    _, app, _, _ = loaded
    fixture = tmp_path / 'exchange'
    fixture.mkdir()
    backup = create_backup(app.state.db)
    shutil.copy2(app.state.db.data_dir / 'backups' / backup['filename'], fixture / 'backup.zip')
    (fixture / 'summary.json').write_text(json.dumps(database_summary(app.state.db.path)))
    import_fixture(fixture, tmp_path / 'new-machine')
