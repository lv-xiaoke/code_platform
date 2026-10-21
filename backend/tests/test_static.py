import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app


def test_old_hashed_assets_survive_release_switch(tmp_path):
    releases=tmp_path/'releases'
    old=releases/'old'/'assets';old.mkdir(parents=True)
    (old/'old-editor-AbC123.js').write_text('old editor',encoding='utf-8')
    current=releases/'new';current.mkdir()
    (current/'index.html').write_text('<h1>new</h1>',encoding='utf-8')
    (releases/'current.json').write_text(json.dumps({'path':'releases/new'}),encoding='utf-8')
    app=create_app(root=tmp_path,data_dir=tmp_path/'data',bootstrap=False)
    with TestClient(app,base_url='http://127.0.0.1:8000') as c:
        r=c.get('/assets/old-editor-AbC123.js')
        assert r.status_code==200 and r.text=='old editor'
        assert c.get('/assets/missing.js').status_code==404
