import json

from fastapi.testclient import TestClient

from app.main import create_app


def test_html_is_never_cached_when_switching_frontend_releases(tmp_path):
    releases = tmp_path / 'releases'
    for name in ('old', 'new'):
        build = releases / name
        build.mkdir(parents=True)
        (build / 'index.html').write_text(f'<title>{name}</title>', encoding='utf-8')

    manifest = releases / 'current.json'
    app = create_app(root=tmp_path, data_dir=tmp_path / 'data', bootstrap=False)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        for name in ('old', 'new'):
            manifest.write_text(json.dumps({'path': f'releases/{name}'}), encoding='utf-8')
            for url in ('/', '/index.html', '/practice'):
                response = client.get(url)
                assert response.text == f'<title>{name}</title>'
                assert response.headers.get('Cache-Control') == 'no-store'
