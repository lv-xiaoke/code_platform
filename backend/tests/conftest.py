import copy
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_macos_credentials(monkeypatch, request):
    # Business tests must never touch a developer's real Keychain.
    import sys
    if sys.platform == 'darwin' and request.node.path.name != 'test_keystore.py':
        from app.ai.secrets import KeyStore
        values = {}
        monkeypatch.setattr(KeyStore, 'read', lambda self: values.get(self.account, ''))
        monkeypatch.setattr(KeyStore, 'write', lambda self, key: values.__setitem__(self.account, key))


@pytest.fixture
def tmp_path():
    # Retain test artifacts; pytest's default retention cleanup bulk-deletes.
    from pathlib import Path
    from uuid import uuid4
    path = Path(__file__).resolve().parents[2] / 'runtime' / 'tests' / uuid4().hex
    path.mkdir(parents=True)
    return path


@pytest.fixture
def snapshot():
    return {
        'generatedAt': '2026-07-18T14:29:48.365Z', 'source': {'baseUrl': 'https://codetop.cc'},
        'taxonomies': {'companies': [{'id': 1, 'name': '字节跳动'}],
                       'departments': [{'id': 2, 'name': '研发', 'company': 1}],
                       'jobs': [{'id': 3, 'name': '后端'}], 'tags': [{'id': 4, 'name': '数组'}]},
        'questions': {
            '1681': {'id': 1681, 'displayId': '3', 'questionId': 999, 'title': '最长子串', 'level': 2, 'content': '<p>题面</p>', 'slug': 'substring', 'expandedLink': False},
            '9': {'id': 9, 'displayId': '补充题 9', 'title': '排序补充', 'level': 2, 'slug': 'sort-an-array'},
            '10': {'id': 10, 'displayId': '补充题 10', 'title': '排序补充二', 'level': 3, 'slug': 'sort-an-array'},
            '11': {'id': 11, 'displayId': '11', 'title': '缺失题面', 'level': 1, 'slug': ''}},
        'indexes': {'overall': [{'questionId': i, 'frequency': 20-i%7, 'time': '2026-07-16T14:00:00Z'} for i in [1681, 9, 10, 11]],
                    'companies': {'1': [{'questionId': 1681, 'frequency': 5}, {'questionId': 9, 'frequency': 3}]},
                    'departments': {'2': [{'questionId': 1681, 'frequency': 2}]},
                    'jobs': {'3': [{'questionId': 1681, 'frequency': 8}, {'questionId': 10, 'frequency': 6}]},
                    'tags': {'4': [{'questionId': 1681, 'frequency': 1}]}}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    # Business fixtures use their fake Docker protocol runners; native execution
    # has separate real-process integration tests and explicit consent.
    monkeypatch.setenv('CODETOP_RUNNER', 'docker')
    now = [datetime(2026, 10, 21, 10, tzinfo=timezone.utc)]
    app = create_app(data_dir=tmp_path, clock=lambda: now[0], bootstrap=False)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        token = client.get('/api/v1/session').json()['token']
        client.headers.update({'X-Session-Token': token, 'Origin': 'http://127.0.0.1:8000'})
        yield client, app, now


def load(client, snapshot, source='algotop', kind='algotop'):
    r = client.post('/api/v1/imports/preview', files={'file': ('source.json', json.dumps(snapshot).encode(), 'application/json')}, data={'kind': kind, 'source_name': source})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/imports/{r.json()['id']}/apply")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def loaded(env, snapshot):
    client, app, now = env
    load(client, snapshot)
    pid = client.get('/api/v1/problems', params={'search': '最长子串'}).json()['items'][0]['id']
    return client, app, now, pid
