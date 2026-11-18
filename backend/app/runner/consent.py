import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException


def consent_status(data_dir):
    try:
        value = json.loads((Path(data_dir) / 'native-consent.json').read_text(encoding='utf-8'))
        return value == {'version': 1, 'accepted': True, 'scope': 'native-current-user'}
    except (OSError, ValueError):
        return False


def accept_native_execution(data_dir):
    path = Path(data_dir) / 'native-consent.json'
    pending = path.with_name('native-consent-' + uuid4().hex + '.pending')
    pending.write_text(json.dumps({'version': 1, 'accepted': True, 'scope': 'native-current-user'}), encoding='utf-8')
    pending.replace(path)
    return {'accepted': True}


def require_native_consent(data_dir, runner):
    if getattr(runner, 'kind', 'docker') == 'native' and not consent_status(data_dir):
        raise HTTPException(403, '请先确认：本机代码可访问当前用户的文件和网络，请只运行你信任的代码')
