from concurrent.futures import ThreadPoolExecutor


def test_language_drafts_are_independent_and_saved_empty_is_not_missing(loaded):
    c, _, _, pid = loaded
    url = f'/api/v1/problems/{pid}/code/drafts'
    assert c.get(url + '/java').json()['exists'] is False
    assert c.put(url + '/python', json={'revision': 0, 'code_text': 'print(1)'}).status_code == 200
    java = c.put(url + '/java', json={'revision': 0, 'code_text': ''})
    assert java.status_code == 200
    assert java.json()['exists'] is True
    assert c.get(url + '/python').json()['code_text'] == 'print(1)'
    stale = c.put(url + '/python', json={'revision': 0, 'code_text': 'lost'})
    assert stale.status_code == 409
    assert stale.json()['detail']['current']['code_text'] == 'print(1)'


def test_shared_body_and_draft_revisions_do_not_interfere(loaded):
    c, _, _, pid = loaded
    base = f'/api/v1/problems/{pid}'
    assert c.put(base + '/note/body', json={'revision': 0, 'body_md': 'shared'}).status_code == 200
    assert c.put(base + '/code/drafts/java', json={'revision': 0, 'code_text': 'class Main {}'}).status_code == 200
    pref = c.put(base + '/code/preference', json={'revision': 0, 'language': 'java'})
    assert pref.status_code == 200
    detail = c.get(base).json()['note']
    assert detail['body_md'] == 'shared'
    assert detail['revision'] == 1
    assert detail['code_text'] == 'class Main {}'
    assert detail['language'] == 'java'
    legacy = c.put(base + '/note', json={'revision': 1, 'code_text': 'overwrite'})
    assert legacy.status_code == 409
    assert c.get(base + '/code/drafts/java').json()['code_text'] == 'class Main {}'


def test_rewrite_only_touches_target_language_and_is_atomic(loaded):
    c, _, _, pid = loaded
    base = f'/api/v1/problems/{pid}/code'
    for language, code in [('python', 'print(1)'), ('java', 'class Main {}')]:
        assert c.put(base + '/drafts/' + language, json={'revision': 0, 'code_text': code}).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: c.post(base + '/rewrite', json={'language': 'java', 'revision': 1}), range(2)))
    assert sorted(r.status_code for r in replies) == [200, 409]
    versions = c.get(base + '/history', params={'language': 'java'}).json()
    assert len(versions) == 1
    assert c.get(base + '/drafts/python').json()['code_text'] == 'print(1)'
    restored = c.post(base + '/rewrite', json={'language': 'java', 'revision': 2, 'history_id': versions[0]['id']})
    assert restored.status_code == 200
    assert restored.json()['draft']['code_text'] == 'class Main {}'
    assert c.get(base + '/preference').json()['language'] == 'java'


def test_unknown_problem_and_path_language_rejected(loaded):
    c, _, _, pid = loaded
    assert c.get('/api/v1/problems/missing/code/drafts/python').status_code == 404
    assert c.put(f'/api/v1/problems/{pid}/code/drafts/'+('x'*51), json={'revision': 0, 'code_text': 'x'}).status_code == 422


def test_legacy_language_names_remain_editable_and_discoverable(loaded):
    from urllib.parse import quote
    c,_,_,pid=loaded
    base=f'/api/v1/problems/{pid}/code'
    for language in ('Go','C++','kotlin','a/b',''):
        url=base+'/draft?language='+quote(language,safe='')
        response=c.put(url,json={'revision':0,'code_text':'original '+language})
        assert response.status_code==200,response.text
        assert c.get(url).json()['code_text']=='original '+language
        pref=c.get(base+'/preference').json()
        assert c.put(base+'/preference',json={'revision':pref['revision'],'language':language}).status_code==200
    assert set(c.get(base+'/languages').json())>={'Go','C++','kotlin','a/b',''}
    pref=c.get(base+'/preference').json()
    assert c.put(base+'/preference',json={'revision':pref['revision'],'language':'python'}).status_code==200
    assert 'kotlin' in c.get(base+'/languages').json()
