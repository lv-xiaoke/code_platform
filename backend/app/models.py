"""SQLite schema. Personal data only references stable problem UUIDs."""
from sqlalchemy import (MetaData, Table, Column, String, Text, Integer, Float,
                        ForeignKey, ForeignKeyConstraint, UniqueConstraint, Index, CheckConstraint)

metadata = MetaData()

datasets = Table('source_datasets', metadata,
    Column('id', String, primary_key=True), Column('source_name', String, nullable=False),
    Column('sha256', String, nullable=False), Column('generated_at', String),
    Column('imported_at', String, nullable=False), Column('source_url', String),
    Column('source_commit', String), Column('status', String, nullable=False),
    Column('summary_json', Text, nullable=False), UniqueConstraint('source_name', 'sha256'))
Index('uq_active_source', datasets.c.source_name, unique=True, sqlite_where=datasets.c.status == 'active')
problems = Table('problems', metadata,
    Column('id', String, primary_key=True), Column('canonical_platform', String),
    Column('canonical_key', String), Column('kind', String, nullable=False),
    Column('created_at', String, nullable=False), UniqueConstraint('canonical_platform', 'canonical_key'))
keys = Table('problem_source_keys', metadata,
    Column('source_name', String, primary_key=True), Column('source_record_id', String, primary_key=True),
    Column('problem_id', String, ForeignKey('problems.id'), nullable=False), Column('upstream_question_id', String))
entries = Table('catalog_entries', metadata,
    Column('dataset_id', String, ForeignKey('source_datasets.id'), primary_key=True),
    Column('problem_id', String, ForeignKey('problems.id'), primary_key=True),
    Column('display_id', String, nullable=False), Column('title', String, nullable=False),
    Column('difficulty', Integer, nullable=False), Column('content_html', Text),
    Column('slug', String), Column('expanded_link', Integer, nullable=False), Column('url', Text),
    CheckConstraint('difficulty BETWEEN 1 AND 3'))
taxonomies = Table('taxonomies', metadata,
    Column('dataset_id', String, ForeignKey('source_datasets.id'), primary_key=True),
    Column('type', String, primary_key=True), Column('source_key', String, primary_key=True),
    Column('name', String, nullable=False), Column('parent_company_key', String), Column('is_internal', Integer, nullable=False, server_default='0'))
stats = Table('scope_stats', metadata,
    Column('dataset_id', String, primary_key=True), Column('problem_id', String, primary_key=True),
    Column('scope_type', String, primary_key=True), Column('scope_key', String, primary_key=True),
    Column('window_key', String, primary_key=True), Column('frequency_value', Float),
    Column('frequency_kind', String, nullable=False), Column('last_seen', String), Column('comment_count', Integer),
    ForeignKeyConstraint(['dataset_id', 'problem_id'], ['catalog_entries.dataset_id', 'catalog_entries.problem_id']),
    ForeignKeyConstraint(['dataset_id', 'scope_type', 'scope_key'], ['taxonomies.dataset_id', 'taxonomies.type', 'taxonomies.source_key']))
Index('ix_scope_frequency', stats.c.dataset_id, stats.c.scope_type, stats.c.scope_key, stats.c.window_key, stats.c.frequency_value.desc())
state = Table('study_state', metadata,
    Column('problem_id', String, ForeignKey('problems.id'), primary_key=True),
    Column('mastery', Integer, nullable=False), Column('favorite', Integer, nullable=False),
    Column('review_enabled', Integer, nullable=False), Column('review_step', Integer, nullable=False),
    Column('next_review_date', String), Column('last_advanced_date', String),
    Column('revision', Integer, nullable=False), Column('updated_at', String, nullable=False),
    CheckConstraint('mastery BETWEEN 0 AND 3'))
Index('ix_due', state.c.next_review_date)
logs = Table('practice_logs', metadata,
    Column('id', String, primary_key=True), Column('problem_id', String, ForeignKey('problems.id'), nullable=False),
    Column('request_id', String, unique=True, nullable=False), Column('practiced_at', String, nullable=False),
    Column('outcome', String, nullable=False), Column('duration_seconds', Integer), Column('scheduler_version', String, nullable=False))
Index('ix_activity', logs.c.practiced_at)
Index('ix_problem_activity', logs.c.problem_id, logs.c.practiced_at)
notes = Table('notes', metadata,
    Column('problem_id', String, ForeignKey('problems.id'), primary_key=True),
    Column('body_md', Text, nullable=False), Column('code_text', Text, nullable=False),
    Column('language', String, nullable=False), Column('revision', Integer, nullable=False), Column('updated_at', String, nullable=False))
settings = Table('settings', metadata, Column('key', String, primary_key=True), Column('value_json', Text, nullable=False))
previews = Table('import_previews', metadata,
    Column('id', String, primary_key=True), Column('source_name', String, nullable=False), Column('sha256', String, nullable=False),
    Column('kind', String, nullable=False), Column('summary_json', Text, nullable=False), Column('created_at', String, nullable=False))
