from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH).parent
hidden = collect_submodules('app') + collect_submodules('alembic')
hidden += ['uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.h11_impl',
           'uvicorn.protocols.websockets.websockets_sansio_impl',
           'sqlalchemy.dialects.sqlite.pysqlite', 'sqlalchemy.sql.default_comparator']
datas = []
for name in ('alembic', 'sqlalchemy', 'fastapi', 'pydantic', 'uvicorn'):
    datas += copy_metadata(name)
a = Analysis([str(root/'packaging/desktop_entry.py')], pathex=[str(root/'backend')],
             binaries=[], datas=datas, hiddenimports=hidden, hookspath=[],
             excludes=['pytest', 'tkinter', 'unittest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CodeTop', console=False,
          debug=False, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='CodeTop')
