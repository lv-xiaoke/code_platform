"""Offline administration. Restore never runs inside the web process."""
import argparse
import json
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .db import Database, ROOT
from .runtime import RuntimeLock


def main():
    parser = argparse.ArgumentParser(description='CodeTop Local administration')
    parser.add_argument('command', choices=['init','backup','restore','counts','environment'])
    parser.add_argument('--data-dir', type=Path, default=ROOT/'data')
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    if args.command == 'restore':
        if not args.archive: parser.error('--archive is required')
        from .backups import restore_backup
        print(json.dumps(restore_backup(args.archive,args.data_dir), ensure_ascii=True, indent=2))
        return
    if args.command == 'environment':
        import importlib.metadata as metadata
        print(json.dumps({'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,
                          'packages':{d.metadata['Name']:d.version for d in metadata.distributions()}},indent=2))
        return
    db = Database(args.data_dir)
    try:
        if args.command == 'init':
            with RuntimeLock(db.data_dir):
                db.migrate()
                from sqlalchemy import select,func
                from .models import datasets
                with db.engine.connect() as conn: empty = conn.execute(select(func.count()).select_from(datasets)).scalar()==0
                if empty:
                    from .imports import preview_import, apply_import
                    raw = (ROOT/'vendor/algoTop-main/public/data/codetop.json').read_bytes()
                    now = datetime.now(timezone.utc)
                    preview = preview_import(db,raw,'algotop','algotop',now)
                    print(json.dumps(apply_import(db,preview['id'],now),ensure_ascii=True,indent=2))
                else: print('Database already initialized; existing data retained.')
        elif args.command == 'backup':
            from .backups import create_backup
            print(json.dumps(create_backup(db),indent=2))
        elif args.command == 'counts':
            from .backups import inspect_database
            print(json.dumps(inspect_database(db.path)[0],indent=2))
    finally: db.engine.dispose()


if __name__ == '__main__': main()
