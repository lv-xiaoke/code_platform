import json
import zipfile

import pytest

from app.backups import restore_backup
from app.db import Database


def test_backup_roundtrip(loaded, tmp_path):
    c, app, _, pid = loaded
    c.put(f'/api/v1/problems/{pid}/note', json={'revision': 0, 'body_md': 'restore me', 'code_text': '', 'language': 'python'})
    r = c.post('/api/v1/backups')
    assert r.status_code == 200, r.text
    path = app.state.db.data_dir / 'backups' / r.json()['filename']
    dest = tmp_path / 'restored'
    result = restore_backup(path, dest)
    assert result['notes'] == 1 and result['problems'] == 4
    db = Database(dest)
    with db.engine.connect() as conn:
        assert conn.exec_driver_sql('PRAGMA quick_check').scalar() == 'ok'
    assert (dest / 'sources').is_dir()


def test_restore_rejects_traversal_and_hash_mismatch(loaded, tmp_path):
    c, app, _, _ = loaded
    name = c.post('/api/v1/backups').json()['filename']
    source = app.state.db.data_dir / 'backups' / name
    for filename, member, data in [('evil.zip', '../outside', b'bad'), ('tamper.zip', 'study.sqlite3', b'bad')]:
        target = tmp_path / filename
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(target, 'w') as changed:
            for info in original.infolist():
                changed.writestr(info.filename, data if info.filename == member else original.read(info.filename))
            if member == '../outside': changed.writestr(member, data)
        with pytest.raises(ValueError): restore_backup(target, tmp_path / 'dest')
    assert not (tmp_path / 'outside').exists()


def test_restore_into_existing_directory_preserves_rollback(loaded):
    c, app, _, pid = loaded
    c.put(f'/api/v1/problems/{pid}/note', json={'revision':0,'body_md':'original','code_text':'','language':'python'})
    name=c.post('/api/v1/backups').json()['filename']
    source=app.state.db.data_dir/'backups'/name
    c.put(f'/api/v1/problems/{pid}/note', json={'revision':1,'body_md':'newer','code_text':'','language':'python'})
    app.state.db.engine.dispose()
    result=restore_backup(source, app.state.db.data_dir)
    assert result['notes']==1
    assert __import__('pathlib').Path(result['rollback_file']).exists()
    import sqlite3
    conn=sqlite3.connect(app.state.db.path)
    try: assert conn.execute('SELECT body_md FROM notes').fetchone()[0]=='original'
    finally: conn.close()


def test_failed_sidecar_move_restores_original_database(loaded, monkeypatch):
    c,app,_,pid=loaded
    source=app.state.db.data_dir/'backups'/c.post('/api/v1/backups').json()['filename']
    app.state.db.engine.dispose()
    from pathlib import Path
    live=app.state.db.path
    original=Path.rename
    def interrupted(path,target):
        if path==live:
            result=original(path,target)
            live.with_name(live.name+'-shm').write_bytes(b'')
            return result
        if path.name==live.name+'-shm': raise PermissionError('simulated sidecar lock')
        return original(path,target)
    monkeypatch.setattr(Path,'rename',interrupted)
    with pytest.raises(PermissionError): restore_backup(source,app.state.db.data_dir)
    assert live.exists(), 'The original database filename must survive a partial move failure'
