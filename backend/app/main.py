import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Query, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import OperationalError, IntegrityError

from . import __version__
from .db import Database, ROOT, SCHEMA_VERSION
from .schemas import NoteWrite, StateWrite, AttemptWrite, CodeRewrite, DraftWrite, NoteBodyWrite, LanguagePreferenceWrite
from . import catalog, imports, learning, code_drafts
from .backups import create_backup
from .runtime import RuntimeLock
from .scheduler import TZ
from .paths import default_data_dir


def is_loopback_host(host: str) -> bool:
    try:
        return urlsplit('http://'+host).hostname in ('127.0.0.1', 'localhost', '::1')
    except ValueError:
        return False


def create_app(root=None, data_dir=None, clock=None, bootstrap=True):
    root = Path(root or ROOT).resolve()
    db = Database(data_dir or os.environ.get('CODETOP_DATA_DIR') or (default_data_dir() if root == ROOT else root / 'data'))
    now = clock or (lambda: datetime.now(timezone.utc))
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        lock = RuntimeLock(db.data_dir) if bootstrap else None
        if lock: lock.__enter__()
        try:
            db.migrate()
            from .runner.service import RunService
            app.state.run_service=RunService(db,now)
            from .runner.terminal import TerminalService
            app.state.terminal_service=TerminalService(db,now)
            from .ai.service import AiService
            app.state.ai_service=AiService(db,now)
            if bootstrap:
                from sqlalchemy import select, func
                from .models import datasets
                with db.engine.connect() as conn: empty = conn.execute(select(func.count()).select_from(datasets)).scalar() == 0
                if empty:
                    path = root / 'vendor' / 'algoTop-main' / 'public' / 'data' / 'codetop.json'
                    if path.exists():
                        preview = imports.preview_import(db, path.read_bytes(), 'algotop', 'algotop', now())
                        imports.apply_import(db, preview['id'], now())
                today = now().astimezone(TZ).date().isoformat()
                if not any((db.data_dir/'backups').glob(f'*-daily-{today}-*.zip')): create_backup(db, reason=f'daily-{today}')
            yield
        finally:
            if hasattr(app.state,'ai_service'): app.state.ai_service.close()
            if hasattr(app.state,'terminal_service'): app.state.terminal_service.close()
            if hasattr(app.state,'run_service'): app.state.run_service.close()
            db.engine.dispose()
            if lock: lock.__exit__()

    app = FastAPI(title='CodeTop Local', version=__version__, lifespan=lifespan)
    app.state.db = db
    app.state.clock = now
    app.state.browser_tabs = None
    from .runner.routes import router as runner_router
    app.include_router(runner_router)
    from .ai.routes import router as ai_router
    app.include_router(ai_router)
    from .desktop_restore import router as desktop_router
    app.include_router(desktop_router)

    from fastapi.exceptions import RequestValidationError
    from fastapi.exception_handlers import request_validation_exception_handler

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Pydantic includes rejected input by default; never echo credentials.
        if request.url.path == '/api/v1/ai/settings':
            return JSONResponse({'detail':'AI 设置格式无效，请检查 Key 和模型'},status_code=422)
        return await request_validation_exception_handler(request,exc)

    @app.middleware('http')
    async def local_boundary(request: Request, call_next):
        host = request.headers.get('host', '')
        if not is_loopback_host(host):
            return JSONResponse({'detail':'只接受本机回环地址'}, status_code=403)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            if origin != f'http://{host}' or not secrets.compare_digest(request.headers.get('x-session-token',''), token):
                return JSONResponse({'detail':'同源或本机会话校验失败，请刷新本地页面'}, status_code=403)
            upload_limit = 256*1024*1024 if request.url.path == '/api/v1/desktop/restore/preview' else 16*1024*1024
            if int(request.headers.get('content-length') or 0) > upload_limit:
                return JSONResponse({'detail':'上传上限为 16 MiB'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/') or response.headers.get('Content-Type', '').startswith('text/html'):
            response.headers['Cache-Control'] = 'no-store'
        if not request.url.path.startswith('/api/'):
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def invalid(_, exc): return JSONResponse({'detail':str(exc)}, status_code=422)

    @app.exception_handler(OperationalError)
    async def busy(_, exc):
        if 'locked' in str(exc).lower() or 'busy' in str(exc).lower(): return JSONResponse({'detail':'数据库暂时繁忙，请稍后重试'}, status_code=503, headers={'Retry-After':'2'})
        return JSONResponse({'detail':'数据库操作失败，请查看服务日志'}, status_code=500)

    @app.exception_handler(IntegrityError)
    async def conflict(_, exc): return JSONResponse({'detail':'数据约束冲突，事务已回滚'}, status_code=409)

    @app.get('/api/v1/health')
    def health():
        # Windows PowerShell 5 otherwise decodes non-ASCII install paths as ANSI.
        return JSONResponse({'app':'codetop-local', 'version':__version__, 'schema_version':SCHEMA_VERSION, 'data_dir':str(db.data_dir), 'root':str(root), 'process_id':os.getpid()}, media_type='application/json; charset=utf-8')

    @app.get('/api/v1/session')
    def session(): return {'token':token}

    @app.websocket('/api/v1/browser-tab')
    async def browser_tab(socket: WebSocket):
        host = socket.headers.get('host', '')
        if not is_loopback_host(host) or socket.headers.get('origin') != f'http://{host}':
            await socket.close(code=1008)
            return
        tabs = app.state.browser_tabs
        if tabs is None:
            await socket.accept()
            await socket.close()
            return
        with tabs.connected():
            await socket.accept()
            while (await socket.receive())['type'] != 'websocket.disconnect':
                pass

    @app.get('/api/v1/catalog/datasets')
    def datasets(): return catalog.list_datasets(db)

    @app.post('/api/v1/catalog/datasets/{dataset_id}/activate')
    def activate(dataset_id: str): return imports.activate(db, dataset_id)

    @app.get('/api/v1/catalog/taxonomies')
    def taxonomies(source: str | None=None, dataset_id: str | None=None): return catalog.get_taxonomies(db, source, dataset_id)

    @app.get('/api/v1/problems')
    def problems(source: str | None=None, dataset_id: str | None=None, page:int=Query(1, ge=1), page_size:int=Query(20,ge=1,le=2000), search:str='', company:str='', department:str='', job:str='', tag:str='', collection:str='', difficulty:int | None=Query(None,ge=1,le=3), completion:str='', mastery:int | None=Query(None,ge=0,le=3), favorite:bool=False, recent_days:int | None=Query(None,ge=1,le=3650), history:bool=False, ordering:str='-frequency'):
        return catalog.list_problems(db, now(), **locals_without({'db','now'}, locals()))

    @app.get('/api/v1/problems/{pid}')
    def problem(pid:str, dataset_id:str | None=None): return catalog.detail(db,pid,dataset_id)

    @app.put('/api/v1/problems/{pid}/note')
    def note(pid:str, payload:NoteWrite): return learning.put_note(db,pid,payload,now())

    @app.put('/api/v1/problems/{pid}/note/body')
    def note_body(pid:str, payload:NoteBodyWrite): return code_drafts.put_body(db,pid,payload,now())

    @app.get('/api/v1/problems/{pid}/code/drafts/{language}')
    def draft_get(pid:str, language:str): return code_drafts.get_draft(db,pid,language)

    @app.put('/api/v1/problems/{pid}/code/drafts/{language}')
    def draft_put(pid:str, language:str, payload:DraftWrite): return code_drafts.put_draft(db,pid,language,payload,now())

    @app.get('/api/v1/problems/{pid}/code/preference')
    def preference_get(pid:str): return code_drafts.get_preference(db,pid)

    @app.put('/api/v1/problems/{pid}/code/preference')
    def preference_put(pid:str, payload:LanguagePreferenceWrite): return code_drafts.put_preference(db,pid,payload,now())

    @app.patch('/api/v1/problems/{pid}/state')
    def state(pid:str, payload:StateWrite): return learning.patch_state(db,pid,payload,now())

    @app.get('/api/v1/problems/{pid}/code/history')
    def code_history(pid:str, language:str | None=None): return learning.get_code_history(db,pid,language)

    @app.post('/api/v1/problems/{pid}/code/rewrite')
    def code_rewrite(pid:str, payload:CodeRewrite): return learning.rewrite_code(db,pid,payload,now())

    @app.post('/api/v1/problems/{pid}/attempts')
    def attempt(pid:str,payload:AttemptWrite): return learning.record_attempt(db,pid,payload,now())

    @app.get('/api/v1/reviews/due')
    def due(page:int=Query(1,ge=1),page_size:int=Query(2000,ge=1,le=2000)): return catalog.list_problems(db,now(),due=True,history=True,page=page,page_size=page_size)

    @app.get('/api/v1/activity')
    def activity(): return learning.activity(db,now())

    @app.post('/api/v1/imports/preview')
    async def preview(file:UploadFile=File(...),kind:str=Form('algotop'),source_name:str=Form('algotop')):
        raw = await file.read(16*1024*1024+1)
        if len(raw)>16*1024*1024: raise HTTPException(413,'上传上限为 16 MiB')
        try: return imports.preview_import(db,raw,kind,source_name,now())
        except (KeyError, TypeError, UnicodeDecodeError, AttributeError) as exc: raise HTTPException(422,'导入结构无效: '+str(exc)) from exc

    @app.post('/api/v1/imports/{pid}/apply')
    def apply(pid:str, links:dict[str,str] | None=None): return imports.apply_import(db,pid,now(),links)

    @app.get('/api/v1/backups')
    def backups():
        files = sorted((db.data_dir/'backups').glob('*.zip'), reverse=True)
        return {'count':len(files),'bytes':sum(p.stat().st_size for p in files),'items':[{'filename':p.name,'bytes':p.stat().st_size,'download_url':f'/api/v1/backups/{p.name}'} for p in files]}

    @app.post('/api/v1/backups')
    def backup(): return create_backup(db)

    @app.get('/api/v1/backups/{filename}')
    def download(filename:str):
        if Path(filename).name != filename or not filename.endswith('.zip'): raise HTTPException(404,'备份不存在')
        path = db.data_dir/'backups'/filename
        if not path.is_file(): raise HTTPException(404,'备份不存在')
        return FileResponse(path,media_type='application/zip',filename=filename)

    @app.api_route('/api/{path:path}', methods=['GET','POST','PUT','PATCH','DELETE'])
    def unknown_api(path:str): raise HTTPException(404,'API 不存在')

    @app.get('/{path:path}')
    def static(path:str):
        marker = root/'releases'/'current.json'
        release = (root/json.loads(marker.read_text(encoding='utf-8-sig'))['path']).resolve() if marker.exists() else root/'frontend'/'dist'
        if not release.is_relative_to(root): raise HTTPException(500,'前端发布路径无效')
        target = (release/path).resolve()
        if not target.is_relative_to(release): raise HTTPException(404)
        if target.is_file(): return FileResponse(target)
        if path.startswith('assets/'):
            # Retained hashed chunks must remain available to already-open tabs.
            import re
            releases = (root/'releases').resolve()
            if re.fullmatch(r'assets/[A-Za-z0-9_.-]+',path) and releases.is_dir():
                for previous in releases.iterdir():
                    candidate = (previous/path).resolve()
                    if previous.is_dir() and candidate.is_relative_to(releases) and candidate.is_file():
                        return FileResponse(candidate)
            raise HTTPException(404)
        if (release/'index.html').exists(): return FileResponse(release/'index.html')
        raise HTTPException(503,'请先运行 scripts/build.ps1 构建前端')

    return app


def locals_without(excluded, values):
    return {k:v for k,v in values.items() if k not in excluded}


app = create_app()
