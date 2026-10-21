import hashlib
from contextlib import closing
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
from uuid import uuid4
import zipfile

from .db import SCHEMA_VERSION
from . import __version__
from .runtime import RuntimeLock

COUNT_TABLES = ('problems', 'catalog_entries', 'notes', 'practice_logs', 'study_state', 'source_datasets')
SUPPORTED_SCHEMAS = ('0001', '0002')


def digest(path):
    with open(path, 'rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def inspect_database(path):
    with closing(sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)) as conn:
        if conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok': raise ValueError('数据库完整性校验失败')
        if conn.execute('PRAGMA foreign_key_check').fetchone(): raise ValueError('数据库外键校验失败')
        row = conn.execute('SELECT version_num FROM alembic_version').fetchone()
        if not row or row[0] not in SUPPORTED_SCHEMAS: raise ValueError('备份数据库结构版本不兼容')
        tables = COUNT_TABLES + (('problem_test_suites', 'code_runs') if row[0]=='0002' else ())
        counts = {name:conn.execute(f'SELECT count(*) FROM {name}').fetchone()[0] for name in tables}
        sources = {row[0] for row in conn.execute('SELECT sha256 FROM source_datasets UNION SELECT sha256 FROM import_previews')}
    return counts, sources


def create_backup(db, reason='manual'):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    filename = f'{stamp}-{reason}-{uuid4().hex[:8]}.zip'
    target = db.data_dir / 'backups' / filename
    stage = db.data_dir / 'staging' / f'backup-{uuid4().hex}'
    stage.mkdir(parents=True)
    snapshot = stage / 'study.sqlite3'
    with closing(sqlite3.connect(db.path)) as source, closing(sqlite3.connect(snapshot)) as destination:
        source.backup(destination)
    counts, sources = inspect_database(snapshot)
    files = {'study.sqlite3':snapshot}
    for sha in sources:
        if len(sha)!=64 or any(c not in 'abcdef0123456789' for c in sha): raise ValueError('来源哈希格式错误')
        path = db.data_dir / 'sources' / sha
        if not path.is_file() or digest(path) != sha: raise ValueError(f'来源文件缺失或已损坏: {sha}')
        files[f'sources/{sha}'] = path
    with closing(sqlite3.connect(snapshot)) as conn:
        conn.row_factory = sqlite3.Row
        datasets = [dict(r) for r in conn.execute('SELECT * FROM source_datasets')]
        snapshot_schema = conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    manifest = {'app_version':__version__, 'schema_version':snapshot_schema, 'created_at':stamp, 'reason':reason,
                'counts':counts, 'datasets':datasets, 'files':{name:digest(path) for name,path in files.items()}}
    # Publish the archive only after all snapshots and hashes are available.
    partial = stage / filename
    with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for name,path in files.items(): archive.write(path, name)
    shutil.copy2(partial, target)
    return {'filename':filename, 'bytes':target.stat().st_size, 'counts':counts, 'download_url':f'/api/v1/backups/{filename}'}


def restore_backup(archive_path, data_dir):
    data_dir = Path(data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    with RuntimeLock(data_dir):
        return _restore(Path(archive_path), data_dir)


def _restore(archive_path, data_dir):
    stage = data_dir / 'staging' / f'restore-{uuid4().hex}'
    stage.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(set(names)) != len(names): raise ValueError('备份包含重复路径')
            if sum(i.file_size for i in archive.infolist()) > 256*1024*1024: raise ValueError('备份解包大小超过 256 MiB')
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename or stat.S_ISLNK(info.external_attr >> 16): raise ValueError('备份包含不安全路径')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('schema_version') not in SUPPORTED_SCHEMAS: raise ValueError('备份结构版本不兼容')
            files = manifest['files']
            if set(names) != {'manifest.json', *files}: raise ValueError('备份内容与清单不一致')
            if 'study.sqlite3' not in files: raise ValueError('备份缺少数据库')
            for name, sha in files.items():
                if name != 'study.sqlite3' and not __import__('re').fullmatch('sources/[a-f0-9]{64}', name): raise ValueError('备份文件类型无效')
                raw = archive.read(name)
                if hashlib.sha256(raw).hexdigest() != sha: raise ValueError('备份文件哈希校验失败')
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        counts, sources = inspect_database(stage / 'study.sqlite3')
        with closing(sqlite3.connect(stage/'study.sqlite3')) as check:
            if check.execute('SELECT version_num FROM alembic_version').fetchone()[0] != manifest['schema_version']:
                raise ValueError('备份清单与实际结构版本不一致')
        if counts != manifest['counts']: raise ValueError('数据库记录数量与清单不一致')
        for sha in sources:
            if f'sources/{sha}' not in files or files[f'sources/{sha}'] != sha: raise ValueError('备份缺少原始来源文件或来源哈希错误')
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, sqlite3.Error) as exc:
        raise ValueError('备份格式或数据库无效') from exc
    from .db import Database
    live = data_dir / 'study.sqlite3'
    rollback = None
    if live.exists():
        db = Database(data_dir)
        create_backup(db, reason='before-restore')
        db.engine.dispose()
        with closing(sqlite3.connect(live)) as conn:
            checkpoint = conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if checkpoint[0] != 0: raise ValueError('数据库仍被其他程序占用，请关闭所有连接后重试')
    # Check source collisions before touching the live database.
    for sha in sources:
        dest = data_dir / 'sources' / sha
        if dest.exists() and digest(dest) != sha: raise ValueError('当前目录存在损坏的来源文件，请手工保留并移走该明确文件后重试')
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists(): shutil.copy2(stage / 'sources' / sha, dest)
    database_moved = False
    wal_moved = False
    shm_moved = False
    wal = live.with_name(live.name+'-wal')
    shm = live.with_name(live.name+'-shm')
    try:
        if live.exists():
            rollback = live.with_name(f'study-before-restore-{uuid4().hex}.sqlite3')
            live.rename(rollback)
            database_moved = True
            if wal.exists():
                wal.rename(rollback.with_name(rollback.name+'-wal'))
                wal_moved = True
            if shm.exists():
                shm.rename(rollback.with_name(rollback.name+'-shm'))
                shm_moved = True
        shutil.copy2(stage / 'study.sqlite3', live)
        restored_counts, _ = inspect_database(live)
        if restored_counts != counts: raise ValueError('恢复后记录数量不一致')
    except BaseException:
        if database_moved:
            if live.exists(): live.rename(live.with_name(f'failed-restore-{uuid4().hex}.sqlite3'))
            if wal_moved:
                if wal.exists(): wal.rename(wal.with_name(f'failed-restore-{uuid4().hex}-wal'))
                rollback.with_name(rollback.name+'-wal').rename(wal)
            if shm_moved:
                if shm.exists(): shm.rename(shm.with_name(f'failed-restore-{uuid4().hex}-shm'))
                rollback.with_name(rollback.name+'-shm').rename(shm)
            rollback.rename(live)
        raise
    return {**counts, 'rollback_file':str(rollback) if rollback else None}
