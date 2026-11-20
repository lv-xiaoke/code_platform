"""Frozen desktop entry: no shell, PATH dependency, or user setup commands."""
import argparse
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager

from .paths import application_root, default_data_dir
from .runtime import RuntimeLock
from . import platforms


def health(port):
    # Ignore system proxies for loopback traffic.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{port}/api/v1/health', timeout=1) as response:
        return json.load(response)


def matches(value, data):
    if not isinstance(value, dict) or value.get('app') != 'codetop-local':
        return False
    if not all(isinstance(value.get(key), str) and value[key] for key in ('root', 'data_dir')):
        return False
    try:
        return (Path(value['root']).resolve() == application_root() and
                Path(value['data_dir']).resolve() == data.resolve())
    except (OSError, ValueError):
        return False


def free_port(preferred):
    for port in (preferred, 0):
        with socket.socket() as sock:
            if platforms.system_name() == 'macos':
                # Match Uvicorn's POSIX listener: the old service's TIME_WAIT
                # sockets must not force restore onto a different browser URL.
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', port))
                return sock.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError('无法找到可用的本机端口')


@contextmanager
def launcher_lock(data):
    guard = RuntimeLock(data, 'launcher.lock')
    deadline = time.monotonic() + 70
    while True:
        try:
            guard.__enter__()
            break
        except ValueError:
            if time.monotonic() > deadline:
                raise RuntimeError('另一个 CodeTop 正在启动，请稍后重试') from None
            time.sleep(.05)
    try:
        yield
    finally:
        guard.__exit__()


def launch(data, preferred=8000, browser=True):
    data.mkdir(parents=True, exist_ok=True)
    with launcher_lock(data):
        marker = data / 'desktop-service.json'
        ports = [preferred]
        try:
            saved = json.loads(marker.read_text())
            if isinstance(saved, dict) and isinstance(saved.get('port'), int) and 1024 <= saved['port'] <= 65535:
                ports.insert(0, saved['port'])
        except (OSError, ValueError, KeyError):
            pass
        for port in ports:
            try:
                if matches(health(port), data):
                    if browser:
                        platforms.open_browser(f'http://127.0.0.1:{port}/')
                    return port
            except (OSError, ValueError):
                pass
        for attempt in range(3):
            port = free_port(preferred)
            log_dir = data / 'logs'
            log_dir.mkdir(exist_ok=True)
            stamp = time.strftime('%Y%m%d-%H%M%S') + f'-{attempt}'
            with (log_dir / f'service-{stamp}.log').open('ab') as log:
                args = [sys.executable, '--serve', '--data-dir', str(data), '--port', str(port)]
                if not getattr(sys, 'frozen', False):
                    args[1:1] = ['-m', 'app.desktop']
                process = subprocess.Popen(args, stdout=log, stderr=log, **platforms.background_options())
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    value = health(port)
                    if matches(value, data) and value['process_id'] == process.pid:
                        pending = marker.with_suffix('.pending')
                        pending.write_text(json.dumps({'port': port, 'pid': process.pid}), encoding='utf-8')
                        pending.replace(marker)
                        if browser:
                            platforms.open_browser(f'http://127.0.0.1:{port}/')
                        return port
                except (OSError, ValueError):
                    pass
                time.sleep(.1)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        raise RuntimeError(f'启动失败，请查看日志：{data / "logs"}')


def serve(data, port):
    import asyncio
    import uvicorn
    from .main import create_app
    from .runtime import BrowserTabs
    from .serve import BrowserServer
    app = create_app(data_dir=data)
    tabs = BrowserTabs()
    app.state.browser_tabs = tabs
    server = BrowserServer(uvicorn.Config(app, host='127.0.0.1', port=port, ws='websockets-sansio', access_log=False), tabs)
    app.state.desktop_server, app.state.desktop_port = server, port
    if platforms.system_name() == 'windows':
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(server.serve())


def wait_parent(pid, timeout=60, identity=None):
    platforms.wait_for_process(pid, identity, timeout)


def wait_data_unlock(data, timeout=60):
    deadline = time.monotonic() + timeout
    while True:
        try:
            with RuntimeLock(data):
                return
        except ValueError:
            if time.monotonic() >= deadline:
                raise RuntimeError('数据仍在使用，取消恢复；原数据保留') from None
            time.sleep(.05)


def restore(data, ticket, parent, port, attempt, parent_identity=None):
    from .desktop_restore import ticket_path, write_status
    from .backups import restore_backup
    stage = ticket_path(data, ticket)
    status = stage / 'status.json'
    if json.loads(status.read_text()).get('attempt') != attempt:
        return
    (stage / ('helper-ready-' + attempt)).write_text('ready')
    deadline = time.monotonic() + 15
    while True:
        current = json.loads(status.read_text())
        if current.get('attempt') != attempt:
            return
        if current['state'] == 'restoring':
            break
        if time.monotonic() > deadline:
            return
        time.sleep(.05)
    value = json.loads(status.read_text())
    try:
        wait_parent(parent, identity=parent_identity)
        wait_data_unlock(data)
        restore_backup(stage / 'backup.zip', data)
        value.update(state='completed', error=None)
    except Exception as exc:
        value.update(state='failed', error=str(exc))
    write_status(stage, value)
    launch(data, port, browser=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--restore')
    parser.add_argument('--parent-pid', type=int)
    parser.add_argument('--parent-identity')
    parser.add_argument('--attempt')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    data = (args.data_dir or default_data_dir()).resolve()
    if sys.stdout is None or sys.stderr is None:
        (data / 'logs').mkdir(parents=True, exist_ok=True)
        stream = (data / 'logs' / 'desktop.log').open('a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream
    os.environ['CODETOP_DATA_DIR'] = str(data)
    os.environ['CODETOP_RUNNER'] = 'native'
    if args.serve:
        serve(data, args.port)
    elif args.restore:
        restore(data, args.restore, args.parent_pid, args.port, args.attempt, args.parent_identity)
    else:
        launch(data, args.port, browser=not args.no_browser)


def entry():
    try:
        main()
    except Exception as exc:
        if getattr(sys, 'frozen', False) and '--serve' not in sys.argv and '--restore' not in sys.argv:
            platforms.show_error(str(exc))
        else:
            raise


if __name__ == '__main__':
    entry()
