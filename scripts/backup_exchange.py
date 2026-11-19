"""Generate/restore synthetic learning backups for cross-OS CI exchange."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def database_summary(path):
    result = {}
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for name in sorted(names):
            escaped = name.replace('"', '""')
            rows = sorted(json.dumps(dict(row), ensure_ascii=False, sort_keys=True)
                          for row in conn.execute(f'SELECT * FROM "{escaped}"'))
            result[name] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
    return result


def import_fixture(fixture, target):
    from app.backups import restore_backup
    expected = json.loads((fixture / 'summary.json').read_text(encoding='utf-8'))
    restore_backup(fixture / 'backup.zip', target)
    if database_summary(target / 'study.sqlite3') != expected:
        raise ValueError('Cross-platform backup contents differ after restoration')


def export_fixture(output):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.backups import create_backup
    output.mkdir(parents=True, exist_ok=False)
    data = ROOT / 'runtime' / ('exchange-source-' + uuid4().hex[:8])
    app = create_app(data_dir=data)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        token = client.get('/api/v1/session').json()['token']
        client.headers.update({'X-Session-Token': token, 'Origin': 'http://127.0.0.1:8000'})
        pid = client.get('/api/v1/problems').json()['items'][0]['id']
        actions = [
            client.put(f'/api/v1/problems/{pid}/note', json={'revision': 0, 'body_md': '跨平台笔记 🍎', 'code_text': 'print("你好")'}),
            client.post(f'/api/v1/problems/{pid}/code/rewrite', json={'revision': 1}),
            client.patch(f'/api/v1/problems/{pid}/state', json={'revision': 0, 'favorite': True, 'done': True}),
            client.put(f'/api/v1/problems/{pid}/test-cases', json={'revision': 0, 'cases': [{'stdin': '你好\n', 'expected_stdout': '你好\n'}]}),
        ]
        for response in actions:
            response.raise_for_status()
        backup = create_backup(app.state.db)
        shutil.copy2(data / 'backups' / backup['filename'], output / 'backup.zip')
        (output / 'summary.json').write_text(json.dumps(database_summary(app.state.db.path), indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export')
    export.add_argument('--output', type=Path, required=True)
    load = sub.add_parser('import')
    load.add_argument('--fixtures-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'export':
        export_fixture(args.output)
    else:
        fixtures = sorted(args.fixtures_dir.rglob('backup.zip'))
        if not fixtures:
            raise ValueError('No cross-platform backup fixtures found')
        for archive in fixtures:
            target = ROOT / 'runtime' / ('exchange-target-' + uuid4().hex[:8])
            import_fixture(archive.parent, target)
            print('Restored and verified:', archive.parent.name)


if __name__ == '__main__':
    main()
