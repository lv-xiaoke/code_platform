import json
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import select

from app.db import Database
from app.backups import restore_backup


def old_database(path):
    path.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path/'study.sqlite3')) as conn:
        sql = (Path(__file__).resolve().parents[1]/'migrations/versions/0001_schema.sql').read_text(encoding='utf-8')
        conn.executescript(sql)
        conn.execute('CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)')
        conn.execute("INSERT INTO alembic_version VALUES ('0001')")
        conn.execute("INSERT INTO problems VALUES ('old-problem',NULL,NULL,'supplemental','2026-10-21')")
        conn.execute("INSERT INTO notes VALUES ('old-problem','old personal note','print(42)','python',7,'2026-10-21')")
        conn.commit()


def test_upgrade_0001_preserves_note_and_restorable_backup(tmp_path):
    path=tmp_path/'old'
    old_database(path)
    db=Database(path)
    db.migrate()
    with db.engine.connect() as conn:
        assert conn.exec_driver_sql('SELECT version_num FROM alembic_version').scalar()=='0002'
        assert conn.exec_driver_sql('SELECT body_md,code_text,revision FROM notes').one()==('old personal note','print(42)',7)
        assert conn.exec_driver_sql('SELECT count(*) FROM problem_test_suites').scalar()==0
        assert conn.exec_driver_sql('SELECT count(*) FROM code_runs').scalar()==0
    backups=list((path/'backups').glob('*before-migration*.zip'))
    assert len(backups)==1
    import zipfile
    with zipfile.ZipFile(backups[0]) as archive:
        assert json.loads(archive.read('manifest.json'))['schema_version']=='0001'
    restored=tmp_path/'restored-old'
    assert restore_backup(backups[0],restored)['notes']==1
    recovered=Database(restored)
    recovered.migrate()
    with recovered.engine.connect() as conn:
        assert conn.exec_driver_sql('SELECT revision FROM notes').scalar()==7
        assert conn.exec_driver_sql('SELECT version_num FROM alembic_version').scalar()=='0002'
    recovered.engine.dispose()
    db.engine.dispose()
