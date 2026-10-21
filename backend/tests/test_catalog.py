import copy
import json
import sqlite3

from conftest import load


def test_identity_scope_and_missing_fields(env, snapshot):
    c, app, _ = env
    result = load(c, snapshot)
    assert result['summary']['questions'] == 4
    data = c.get('/api/v1/problems', params={'company': '1', 'job': '3'}).json()
    assert data['count'] == 1
    assert data['items'][0]['display_id'] == '3'
    assert data['items'][0]['frequency'] == 5
    assert data['ranking_scope'] == 'company'
    assert '交集' in data['scope_label']
    ids = [p['id'] for p in c.get('/api/v1/problems').json()['items']]
    assert len(set(ids)) == 4
    missing = c.get('/api/v1/problems', params={'search': '缺失'}).json()['items'][0]
    detail = c.get('/api/v1/problems/' + missing['id']).json()
    assert detail['url'] is None and detail['content_html'] is None
    assert c.get('/api/v1/problems', params={'tag': '4', 'company': '1'}).json()['count'] == 1
    assert c.get('/api/v1/problems', params={'department': '2', 'company': 'wrong'}).json()['count'] == 0


def test_repeat_update_and_rollback_preserve_learning(loaded, snapshot):
    c, app, _, pid = loaded
    c.put(f'/api/v1/problems/{pid}/note', json={'revision': 0, 'body_md': 'keep me', 'code_text': '', 'language': 'python'})
    first = load(c, snapshot)
    assert len(c.get('/api/v1/catalog/datasets').json()) == 1
    updated = copy.deepcopy(snapshot)
    updated['questions']['1681']['title'] = '改标题'
    second = load(c, updated)
    assert first['id'] != second['id']
    detail = c.get(f'/api/v1/problems/{pid}').json()
    assert detail['title'] == '改标题' and detail['note']['body_md'] == 'keep me'
    assert c.post(f"/api/v1/catalog/datasets/{first['id']}/activate").status_code == 200
    assert c.get(f'/api/v1/problems/{pid}').json()['title'] == '最长子串'
    omitted = copy.deepcopy(snapshot)
    del omitted['questions']['1681']
    for k,v in omitted['indexes'].items():
        if isinstance(v, list): omitted['indexes'][k] = [r for r in v if r['questionId'] != 1681]
        else:
            for key, rows in v.items(): v[key] = [r for r in rows if r['questionId'] != 1681]
    load(c, omitted)
    assert c.get(f'/api/v1/problems/{pid}').json()['note']['body_md'] == 'keep me'
    assert c.get('/api/v1/problems', params={'history': True, 'search': '最长'}).json()['count'] == 1


def test_bad_import_leaves_active_unchanged(loaded, snapshot):
    c, app, _, _ = loaded
    broken = copy.deepcopy(snapshot)
    broken['indexes']['companies']['1'].append({'questionId': 99999, 'frequency': 2})
    r = c.post('/api/v1/imports/preview', files={'file': ('bad.json', json.dumps(broken).encode())}, data={'kind': 'algotop', 'source_name': 'algotop'})
    assert r.status_code == 422
    assert len(c.get('/api/v1/catalog/datasets').json()) == 1
    assert c.get('/api/v1/problems').json()['count'] == 4


def test_manual_csv_merge_and_units(loaded):
    c, _, _, pid = loaded
    raw = 'platform,display_id,title,difficulty,url,tags,collection,frequency\nleetcode,3,三,medium,https://leetcode.cn/problems/substring/,字符串|滑动窗口,准备,95\nmanual,extra,补充,easy,,,准备,\n'
    r = c.post('/api/v1/imports/preview', files={'file': ('extra.csv', raw.encode())}, data={'kind': 'manual', 'source_name': 'my-list'})
    assert r.status_code == 200, r.text
    assert c.post(f"/api/v1/imports/{r.json()['id']}/apply").status_code == 200
    data = c.get('/api/v1/problems', params={'source': 'my-list'}).json()
    assert data['count'] == 2 and data['frequency_kind'] == 'source_score'
    assert data['items'][0]['id'] == pid


def test_unknown_api_validation_and_write_security(env):
    c, _, _ = env
    assert c.get('/api/v1/no-such-api').status_code == 404
    assert c.get('/api/v1/problems?page=0').status_code == 422
    assert c.post('/api/v1/backups', headers={'Origin': 'https://evil.test'}).status_code == 403
    assert c.post('/api/v1/backups', headers={'X-Session-Token': 'wrong'}).status_code == 403
    assert c.get('/api/v1/session', headers={'Host': 'evil.test'}).status_code in [400,403]
