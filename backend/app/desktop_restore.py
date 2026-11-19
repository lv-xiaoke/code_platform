"""Validate into a separate database; commit restoration only after service exit."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from .backups import restore_backup
from . import platforms

router = APIRouter(prefix='/api/v1/desktop')
_confirm_lock = threading.Lock()


def ticket_path(data_dir, ticket):
    try:
        if str(UUID(ticket)) != ticket:
            raise ValueError()
    except ValueError:
        raise HTTPException(422, '恢复编号无效')
    return Path(data_dir) / 'desktop-restore' / ticket


def write_status(stage, value):
    pending = stage / ('status-' + uuid4().hex + '.pending')
    pending.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    pending.replace(stage / 'status.json')


def start_restore_helper(stage, argv, timeout=5):
    value = json.loads((stage / 'status.json').read_text(encoding='utf-8'))
    attempt = uuid4().hex
    value.update(state='starting', attempt=attempt)
    write_status(stage, value)
    process = None
    try:
        process = subprocess.Popen([*argv, '--attempt', attempt], **platforms.background_options())
        deadline = time.monotonic() + timeout
        while not (stage / ('helper-ready-' + attempt)).exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('恢复助手未能及时启动')
            time.sleep(.03)
        return value
    except (OSError, RuntimeError):
        # Invalidate before termination: a late old helper can never commit this attempt.
        value.update(state='preview', attempt=None)
        write_status(stage, value)
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        raise HTTPException(503, '恢复助手未能启动，原数据和服务保持可用，请重试') from None


@router.get('/capabilities')
def capabilities():
    return {'restore': bool(getattr(sys, 'frozen', False))}


@router.post('/restore/preview')
async def preview(request: Request, file: UploadFile = File(...)):
    data_dir = request.app.state.db.data_dir
    ticket = str(uuid4())
    stage = ticket_path(data_dir, ticket)
    stage.mkdir(parents=True)
    archive = stage / 'backup.zip'
    size = 0
    with archive.open('xb') as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 256 * 1024 * 1024:
                raise HTTPException(413, '备份上传不能超过 256 MiB')
            output.write(chunk)
    try:
        # Reuse the exact existing validation/rollback engine on an empty scratch DB.
        # Keep SHA-named source extraction below Windows' legacy MAX_PATH boundary.
        result = restore_backup(archive, data_dir / 'rp' / ticket[:12])
    except (ValueError, OSError) as exc:
        raise HTTPException(422, '备份校验失败：' + str(exc)) from None
    metadata = {'ticket': ticket, 'counts': {k: v for k, v in result.items() if k != 'rollback_file'}, 'state': 'preview'}
    (stage / 'status.json').write_text(json.dumps(metadata), encoding='utf-8')
    return metadata


@router.get('/restore/{ticket}')
def status(ticket: str, request: Request):
    path = ticket_path(request.app.state.db.data_dir, ticket) / 'status.json'
    if not path.is_file():
        raise HTTPException(404, '恢复请求不存在')
    return json.loads(path.read_text(encoding='utf-8'))


@router.post('/restore/{ticket}/confirm')
def confirm(ticket: str, request: Request):
    if not getattr(sys, 'frozen', False) or not hasattr(request.app.state, 'desktop_server'):
        raise HTTPException(409, '请在完整桌面版中使用恢复入口；源码版可使用原恢复脚本')
    stage = ticket_path(request.app.state.db.data_dir, ticket)
    path = stage / 'status.json'
    if not path.is_file():
        raise HTTPException(404, '恢复请求不存在')
    with _confirm_lock:
        if getattr(request.app.state, 'restore_pending', False):
            raise HTTPException(409, '已有恢复正在处理')
        value = json.loads(path.read_text(encoding='utf-8'))
        if value['state'] != 'preview':
            raise HTTPException(409, '恢复请求已处理')
        port = request.app.state.desktop_port
        argv = [sys.executable, '--restore', ticket, '--parent-pid', str(os.getpid()),
                '--data-dir', str(request.app.state.db.data_dir), '--port', str(port)]
        identity = platforms.process_identity(os.getpid())
        if identity is not None:
            argv.extend(['--parent-identity', identity])
        value = start_restore_helper(stage, argv)
        value['state'] = 'restoring'
        write_status(stage, value)
        request.app.state.restore_pending = True
        def stop():
            request.app.state.desktop_server.should_exit = True
        threading.Timer(.8, stop).start()
        return {'state': 'restoring', 'ticket': ticket}
