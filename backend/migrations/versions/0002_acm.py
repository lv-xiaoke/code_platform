"""Persist ACM test suites and execution history without modifying learning data."""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE problem_test_suites (
        problem_id VARCHAR PRIMARY KEY REFERENCES problems(id),
        revision INTEGER NOT NULL, cases_json TEXT NOT NULL, updated_at VARCHAR NOT NULL
    )''')
    op.execute('''CREATE TABLE code_runs (
        id VARCHAR PRIMARY KEY, problem_id VARCHAR NOT NULL REFERENCES problems(id),
        request_id VARCHAR NOT NULL UNIQUE, request_hash VARCHAR NOT NULL,
        source_code TEXT NOT NULL, tests_json TEXT NOT NULL, results_json TEXT,
        status VARCHAR NOT NULL, error TEXT, image_ref VARCHAR,
        created_at VARCHAR NOT NULL, finished_at VARCHAR
    )''')
    op.execute('CREATE INDEX ix_problem_runs ON code_runs(problem_id, created_at)')


def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore a verified backup.')
