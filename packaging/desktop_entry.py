import sys

# Alembic loads bundled .py migrations; never mutate a signed/read-only app.
sys.dont_write_bytecode = True

from app.desktop import entry

entry()
