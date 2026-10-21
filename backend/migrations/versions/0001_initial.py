"""Initial local study schema."""
from alembic import op
from pathlib import Path

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).with_name('0001_schema.sql').read_text(encoding='utf-8')
    for statement in sql.split(';'):
        if statement.strip(): op.execute(statement.strip())


def downgrade():
    raise RuntimeError('Automatic destructive downgrade is disabled; restore a verified backup instead.')
