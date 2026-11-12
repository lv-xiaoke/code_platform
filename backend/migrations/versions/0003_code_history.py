"""Keep immutable code snapshots when starting another practice."""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE code_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id VARCHAR NOT NULL REFERENCES problems(id),
        code_text TEXT NOT NULL, language VARCHAR NOT NULL,
        created_at VARCHAR NOT NULL
    )''')
    op.execute('CREATE INDEX ix_code_history_problem ON code_history(problem_id, id)')


def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore a verified backup.')
