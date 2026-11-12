from contextlib import contextmanager
from contextlib import closing
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = '0003'


class Database:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir or ROOT / 'data').resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for directory in ['sources', 'backups', 'staging']:
            (self.data_dir / directory).mkdir(exist_ok=True)
        self.path = self.data_dir / 'study.sqlite3'
        self.engine = create_engine('sqlite:///' + self.path.as_posix(), connect_args={'check_same_thread': False, 'timeout': 10})

        @event.listens_for(self.engine, 'connect')
        def configure(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=10000')
            connection.execute('PRAGMA journal_mode=WAL')

    def migrate(self):
        if self.path.exists() and self.path.stat().st_size:
            import sqlite3
            with closing(sqlite3.connect(self.path)) as conn:
                version = conn.execute("SELECT name FROM sqlite_master WHERE name='alembic_version'").fetchone()
                current = conn.execute('SELECT version_num FROM alembic_version').fetchone() if version else None
            if current and current[0] == SCHEMA_VERSION:
                return
            if current:
                from .backups import create_backup
                create_backup(self, reason='before-migration')
        config = Config()
        config.set_main_option('script_location', str(ROOT / 'backend' / 'migrations'))
        config.set_main_option('sqlalchemy.url', 'sqlite:///' + self.path.as_posix())
        with self.engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')

    @contextmanager
    def write(self):
        # Serialize competing writers before checking revision/idempotency.
        with self.engine.connect() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
