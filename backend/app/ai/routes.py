from fastapi import APIRouter, Request
from .schemas import Ask, ConfigWrite

router=APIRouter(prefix='/api/v1')

@router.get('/ai/settings')
def settings(request:Request): return request.app.state.ai_service.config()

@router.put('/ai/settings')
def configure(payload:ConfigWrite,request:Request): return request.app.state.ai_service.configure(payload)

@router.post('/ai/test')
def test(request:Request): return request.app.state.ai_service.test_connection()

@router.get('/problems/{pid}/ai')
def history(pid:str,request:Request): return request.app.state.ai_service.get(pid)

@router.post('/problems/{pid}/ai',status_code=202)
def ask(pid:str,payload:Ask,request:Request): return request.app.state.ai_service.ask(pid,payload)

@router.post('/problems/{pid}/ai/stop')
def stop(pid:str,request:Request): return request.app.state.ai_service.stop(pid)
