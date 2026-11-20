from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH).parent
hidden = collect_submodules('app', filter=lambda name: name != 'app.runner.windows_job') + collect_submodules('alembic')
hidden += ['psutil', 'uvicorn.logging', 'uvicorn.protocols.http.h11_impl',
           'uvicorn.protocols.websockets.websockets_sansio_impl',
           'sqlalchemy.dialects.sqlite.pysqlite', 'sqlalchemy.sql.default_comparator']
datas = []
for name in ('alembic', 'sqlalchemy', 'fastapi', 'pydantic', 'uvicorn', 'psutil'):
    datas += copy_metadata(name)
a = Analysis([str(root / 'packaging/desktop_entry.py')], pathex=[str(root / 'backend')],
             binaries=[], datas=datas, hiddenimports=hidden,
             excludes=['pytest', 'tkinter', 'unittest', 'app.runner.windows_job', 'msvcrt'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='CodeTop', console=False,
          debug=False, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='CodeTop', strip=False, upx=False)
app = BUNDLE(coll, name='CodeTop.app', bundle_identifier='local.codetop.CodeTop',
             info_plist={'CFBundleDisplayName': 'CodeTop 刷题', 'LSUIElement': True,
                         'NSHighResolutionCapable': True})
