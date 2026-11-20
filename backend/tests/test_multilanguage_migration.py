import json
import sqlite3
import zipfile
from contextlib import closing

import pytest
from alembic import command
from alembic.config import Config

from app.db import Database, ROOT
from app.backups import inspect_database, create_backup, restore_backup


def legacy_database(path):
    db = Database(path)
    cfg = Config()
    cfg.set_main_option('script_location', str(ROOT / 'backend/migrations'))
    with db.engine.begin() as conn:
        cfg.attributes['connection'] = conn
        command.upgrade(cfg, '0003')
    return db


@pytest.mark.parametrize('language,code', [('python', 'print(1)'), ('java', ''), ('sql', 'SELECT 1;')])
def test_legacy_drafts_preserve_empty_and_unsupported_language(tmp_path, language, code):
    db = legacy_database(tmp_path)
    with closing(sqlite3.connect(db.path)) as conn:
        conn.execute("INSERT INTO problems(id,kind,created_at) VALUES('p','custom','2026-11-20')")
        conn.execute('INSERT INTO notes VALUES(?,?,?,?,?,?)', ('p', '共享笔记', code, language, 7, '2026-11-20'))
        conn.execute('INSERT INTO code_history(problem_id,code_text,language,created_at) VALUES(?,?,?,?)',
                     ('p', 'original history', language, '2026-11-19'))
        conn.execute('INSERT INTO code_runs(id,problem_id,request_id,request_hash,source_code,tests_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)',
                     ('run', 'p', 'req', 'hash', 'print(1)', '[]', 'completed', '2026-11-20'))
        conn.commit()
    db.migrate()
    with closing(sqlite3.connect(db.path)) as conn:
        assert conn.execute('SELECT language,code_text,revision FROM code_drafts').fetchone() == (language, code, 1)
        assert conn.execute('SELECT body_md,revision FROM notes').fetchone() == ('共享笔记', 7)
        assert conn.execute('SELECT language FROM problem_preferences').fetchone()[0] == language
        assert conn.execute('SELECT code_text,language FROM code_history').fetchall() == [('original history', language)]
        assert conn.execute('SELECT language FROM code_runs').fetchone()[0] == 'python'
    archives = list((tmp_path / 'backups').glob('*before-migration*.zip'))
    assert len(archives) == 1
    with zipfile.ZipFile(archives[0]) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['schema_version'] == '0003'


def test_new_backup_restores_all_drafts_and_preferences(tmp_path):
    db = legacy_database(tmp_path / 'source')
    with closing(sqlite3.connect(db.path)) as conn:
        conn.execute("INSERT INTO problems(id,kind,created_at) VALUES('p','custom','2026-11-20')")
        conn.commit()
    db.migrate()
    with closing(sqlite3.connect(db.path)) as conn:
        conn.executemany('INSERT INTO code_drafts VALUES(?,?,?,?,?,?)', [
            ('p', 'python', 'print(1)', 2, 'a', 'b'), ('p', 'java', '', 1, 'a', 'a')])
        conn.execute('INSERT INTO problem_preferences VALUES(?,?,?,?)', ('p', 'java', 3, 'b'))
        conn.commit()
    result = create_backup(db)
    target = tmp_path / 'restored'
    restore_backup(db.data_dir / 'backups' / result['filename'], target)
    counts, _ = inspect_database(target / 'study.sqlite3')
    assert counts['code_drafts'] == 2
    assert counts['problem_preferences'] == 1
    with closing(sqlite3.connect(target / 'study.sqlite3')) as conn:
        assert conn.execute('SELECT code_text FROM code_drafts WHERE language="java"').fetchone() == ('',)
        assert conn.execute('SELECT language,revision FROM problem_preferences').fetchone() == ('java', 3)
