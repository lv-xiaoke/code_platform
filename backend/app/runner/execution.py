"""Language-aware identities and server-side capability checks."""
import hashlib
import json
from fastapi import HTTPException


def execution_hash(problem_id, language, source_code, mode, cases, suite_revision=None):
    value = dict(problem_id=problem_id, language=language, source_code=source_code,
        mode=mode, cases=cases, suite_revision=suite_revision)
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode('utf-8')).hexdigest()


def require_environment(runner, language):
    if hasattr(runner, 'toolchains'):
        status = runner.toolchains().capability(language)
        if not status['available']:
            raise HTTPException(409, dict(language=language, state=status['state'], action='prepare',
                message=status.get('error', '请先准备此语言的运行环境')))
    elif language != 'python':
        raise HTTPException(409, dict(language=language, state='unsupported', action='native',
            message='Docker 模式首版仅支持 Python，请切换本机运行模式'))
