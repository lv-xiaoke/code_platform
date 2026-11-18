from fastapi import APIRouter, Request

from .schemas import SuiteWrite, RunWrite, TerminalStart, TerminalInput
from .service import acm_detail,save_suite
from .consent import consent_status, accept_native_execution
from pydantic import BaseModel
from typing import Literal

router=APIRouter(prefix='/api/v1')


@router.get('/runner/health')
def health(request:Request):
    runner = request.app.state.run_service.runner
    result = runner.health()
    kind = getattr(runner, 'kind', 'docker')
    return {**result, 'kind': kind, 'label': '本机 Python' if kind == 'native' else 'Docker',
            'consent_required': kind == 'native' and not consent_status(request.app.state.db.data_dir)}


class ConsentWrite(BaseModel):
    accepted: Literal[True]


@router.get('/runner/consent')
def consent(request: Request):
    return {'accepted': consent_status(request.app.state.db.data_dir)}


@router.post('/runner/consent')
def accept(payload: ConsentWrite, request: Request):
    return accept_native_execution(request.app.state.db.data_dir)


@router.get('/problems/{pid}/acm')
def acm(pid:str,request:Request): return acm_detail(request.app.state.db,pid)


@router.put('/problems/{pid}/test-cases')
def suite(pid:str,payload:SuiteWrite,request:Request): return save_suite(request.app.state.db,pid,payload,request.app.state.clock())


@router.post('/problems/{pid}/runs',status_code=202)
def run(pid:str,payload:RunWrite,request:Request): return request.app.state.run_service.submit(pid,payload)


@router.get('/problems/{pid}/runs')
def history(pid:str,request:Request): return request.app.state.run_service.history(pid)


@router.get('/runs/{run_id}')
def result(run_id:str,request:Request): return request.app.state.run_service.get(run_id)


@router.post('/problems/{pid}/terminals',status_code=202)
def terminal_start(pid:str,payload:TerminalStart,request:Request):
    return request.app.state.terminal_service.start(pid,payload)


@router.get('/terminals/{run_id}')
def terminal_get(run_id:str,request:Request): return request.app.state.terminal_service.get(run_id)


@router.post('/terminals/{run_id}/input')
def terminal_input(run_id:str,payload:TerminalInput,request:Request):
    return request.app.state.terminal_service.send(run_id,payload)


@router.post('/terminals/{run_id}/stop')
def terminal_stop(run_id:str,request:Request): return request.app.state.terminal_service.stop(run_id)


@router.post('/terminal-requests/{request_id}/stop')
def terminal_cancel_request(request_id:str,request:Request):
    return request.app.state.terminal_service.stop_request(request_id)
