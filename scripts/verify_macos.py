"""Exercise a packaged Mac app using fresh data; emit truthful machine evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4


def verify_app(app, report_path, toolchains_root=None):
    app = app.resolve()
    report_path = report_path.resolve()
    executable = app / 'Contents/MacOS/CodeTop'
    resources = app / 'Contents/Resources'
    data = report_path.parent / ('macos-smoke-中文 ' + uuid4().hex[:8])
    data.mkdir(parents=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {'Origin': base}
    def request(path, payload=None, *, raw=None, content_type=None):
        body = json.dumps(payload).encode() if payload is not None else raw
        local_headers = dict(headers)
        if body is not None:
            local_headers['Content-Type'] = content_type or 'application/json'
        value = urllib.request.Request(base + path, data=body, headers=local_headers)
        with opener.open(value, timeout=5) as response:
            return json.load(response)
    def healthy(expected_pid=None, timeout=40):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                health = request('/api/v1/health')
                if (health.get('app') == 'codetop-local' and Path(health['data_dir']).resolve() == data
                        and Path(health['root']).resolve() == resources
                        and (expected_pid is None or health['process_id'] == expected_pid)):
                    return health
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(.1)
        raise RuntimeError('Packaged application did not become healthy')

    report = {'at': datetime.now(timezone.utc).isoformat(), 'os': platform.mac_ver()[0],
              'architecture': platform.machine(), 'app': str(app), 'data': str(data), 'checks': [],
              'manual_checks_pending': ['Finder launch', 'Safari/Chrome multi-tab refresh and close',
                                        'Keychain authorization/denial', 'clean-machine DMG installation',
                                        'minimum macOS 13 compatibility'], 'passed': False}
    process = None
    try:
        with executable.open('rb') as stream:
            report['executable_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(Path.home()), 'TMPDIR': str(data), 'CODETOP_DATA_DIR': str(data)}
        if toolchains_root: env['CODETOP_TOOLCHAINS_DIR'] = str(toolchains_root.resolve())
        with (data / 'service.log').open('ab') as log:
            process = subprocess.Popen([str(executable), '--serve', '--data-dir', str(data), '--port', str(port)],
                                       env=env, cwd=data, stdout=log, stderr=log, start_new_session=True)
        healthy(process.pid)
        report['checks'].append('isolated startup without developer PATH')
        headers['X-Session-Token'] = request('/api/v1/session')['token']
        catalog = request('/api/v1/problems')
        if catalog['count'] != 1153:
            raise ValueError('Built-in catalog count mismatch')
        pid = catalog['items'][0]['id']
        runner = request('/api/v1/runner/health')
        if not runner.get('available') or runner.get('kind') != 'native':
            raise ValueError('Bundled native Python unavailable')
        request('/api/v1/runner/consent', {'accepted': True})
        job = request(f'/api/v1/problems/{pid}/runs', {'request_id': uuid4().hex,
                      'source_code': 'print(input())', 'cases': [{'stdin': '你好\n', 'expected_stdout': '你好\n'}]})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            result = request('/api/v1/runs/' + job['id'])
            if result['status'] not in ('queued', 'preparing', 'compiling', 'running'):
                break
            time.sleep(.1)
        if result['status'] != 'completed' or not result['results'] or result['results'][0]['status'] != 'passed':
            raise ValueError('Packaged Python execution failed: ' + result['status'])
        report['checks'].extend(['built-in catalog', 'native Python Unicode input and comparison'])
        if toolchains_root:
            from multilanguage_smoke import verify_server
            report['multilanguage'] = verify_server(base, expected_data_dir=data, require_all=True)
            report['checks'].append('five languages: compiled batch, interactive Unicode input/EOF and compile diagnostics')
        backup = request('/api/v1/backups', {})
        with opener.open(urllib.request.Request(base + backup['download_url'], headers=headers), timeout=10) as response:
            raw_backup = response.read()
        boundary = 'CodeTop' + uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="backup.zip"\r\n'
                'Content-Type: application/zip\r\n\r\n').encode() + raw_backup + f'\r\n--{boundary}--\r\n'.encode()
        preview = request('/api/v1/desktop/restore/preview', raw=body, content_type='multipart/form-data; boundary=' + boundary)
        request('/api/v1/desktop/restore/' + preview['ticket'] + '/confirm', {})
        process.wait(timeout=30)
        healthy(timeout=50)
        headers['X-Session-Token'] = request('/api/v1/session')['token']
        status = request('/api/v1/desktop/restore/' + preview['ticket'])
        if status['state'] != 'completed' or request('/api/v1/problems')['count'] != 1153:
            raise ValueError('Packaged restore/restart failed')
        report['checks'].append('backup validation, restore helper and service restart')
        report['passed'] = True
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        # A restored service is a different process. Verify data+root before stopping it.
        try:
            health = healthy(timeout=1)
            import psutil
            current = psutil.Process(health['process_id'])
            if Path(current.exe()).resolve() == executable.resolve():
                current.terminate()
                current.wait(timeout=10)
        except Exception as exc:
            report['cleanup_note'] = type(exc).__name__
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--toolchains-root', type=Path)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Packaged Mac validation requires macOS')
    verify_app(args.app, args.report, args.toolchains_root)
