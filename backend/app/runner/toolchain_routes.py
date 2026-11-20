from fastapi import APIRouter, Request, HTTPException

from .toolchains.registry import LANGUAGES

router = APIRouter(prefix='/api/v1/runner/languages')


@router.get('')
def languages(request: Request):
    from .factory import runner_kind
    if runner_kind() == 'docker':
        health = request.app.state.run_service.runner.health()
        return {'languages': [dict(language=language, kind='docker',
            available=language == 'python' and health['available'],
            state=('ready' if health['available'] else 'unprepared') if language == 'python' else 'unsupported',
            error=health.get('error', '') if language == 'python' else '请切换本机运行模式以执行此语言') for language in LANGUAGES]}
    return {'languages': [{**request.app.state.toolchains.capability(language), 'kind': 'native'} for language in LANGUAGES]}


@router.post('/{language}/prepare')
def prepare(language: str, request: Request):
    from .factory import runner_kind
    if runner_kind() != 'native': raise HTTPException(409, '请切换本机运行模式后准备语言环境')
    try:
        return request.app.state.toolchains.prepare(language)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/{language}/cancel')
def cancel(language: str, request: Request):
    if language not in LANGUAGES: raise HTTPException(422, '此语言暂不支持执行')
    return request.app.state.toolchains.cancel(language)
