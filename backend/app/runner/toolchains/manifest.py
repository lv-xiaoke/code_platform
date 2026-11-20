import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


def safe_relative(value):
    path = PurePosixPath(value.replace('\\', '/'))
    if not value or path.is_absolute() or '..' in path.parts or ':' in value:
        raise ValueError('工具链清单路径无效')
    return path


def load_manifest(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema') != 1 or not data.get('artifacts'):
        raise ValueError('工具链清单版本无效')
    ids = set()
    for item in data['artifacts']:
        try:
            url = urlsplit(item['url'])
            if url.scheme != 'https' or url.hostname not in ('github.com', 'nodejs.org') or 'latest' in item['url'].lower():
                raise ValueError('工具链必须锁定官方发行版')
            if not re.fullmatch('[a-f0-9]{64}', item['sha256']) or not item['license'] or not item['version']:
                raise ValueError('工具链校验或许可证信息缺失')
            if item['id'] in ids or not re.fullmatch(r'[a-zA-Z0-9_.+\-]+', item['id']):
                raise ValueError('工具链编号无效')
            ids.add(item['id'])
            safe_relative(item['root'])
            for executable in item['executables'].values(): safe_relative(executable)
            if item['archive'] not in ('zip', 'tar.gz') or not item['languages']:
                raise ValueError('工具链归档类型无效')
        except (KeyError, TypeError) as exc:
            raise ValueError('工具链清单字段不完整') from exc
    return data
