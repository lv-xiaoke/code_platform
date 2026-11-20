"""Separate language drafts and persist execution metadata without rewriting history."""
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE code_drafts (
        problem_id VARCHAR NOT NULL REFERENCES problems(id), language VARCHAR NOT NULL,
        code_text TEXT NOT NULL, revision INTEGER NOT NULL,
        created_at VARCHAR NOT NULL, updated_at VARCHAR NOT NULL,
        PRIMARY KEY(problem_id, language))''')
    op.execute('''CREATE TABLE problem_preferences (
        problem_id VARCHAR PRIMARY KEY REFERENCES problems(id), language VARCHAR NOT NULL,
        revision INTEGER NOT NULL, updated_at VARCHAR NOT NULL)''')
    op.execute('''INSERT INTO code_drafts SELECT problem_id,language,code_text,1,updated_at,updated_at FROM notes''')
    op.execute('''INSERT INTO problem_preferences SELECT problem_id,language,1,updated_at FROM notes''')
    op.execute("ALTER TABLE code_runs ADD COLUMN language VARCHAR NOT NULL DEFAULT 'python'")
    for name in ('runtime_version', 'toolchain_id', 'compile_json', 'limits_json'):
        op.execute(f'ALTER TABLE code_runs ADD COLUMN {name} TEXT')


def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore a verified backup.')
