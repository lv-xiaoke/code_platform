from fastapi import APIRouter, Request

from .schemas import SuiteWrite, RunWrite
from .service import acm_detail,save_suite

router=APIRouter(prefix='/api/v1')


@router.get('/runner/health')
def health(request:Request): return request.app.state.run_service.runner.health()


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
