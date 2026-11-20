"""Prepare once, publish last. Selecting a language never downloads anything."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from uuid import uuid4

from ... import platforms
from ...paths import application_root, native_python, toolchains_dir, verify_bundled_runtime
from . import archive
from .manifest import load_manifest

LANGUAGES = ('python', 'c', 'cpp', 'java', 'javascript')


@dataclass(frozen=True)
class ResolvedToolchain:
    id: str
    version: str
    executables: dict[str, Path]
    sdk: Path | None = None


def command_env(executables):
    env = {k: v for k, v in os.environ.items() if k.upper() in
           ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'SYSTEMDRIVE', 'TMPDIR')}
    env['PATH'] = os.pathsep.join(dict.fromkeys(str(p.parent) for p in executables.values()))
    env.update(LANG='en_US.UTF-8', LC_CTYPE='UTF-8')
    return env


def probe_output(argv, env=None):
    result = subprocess.run(list(map(str, argv)), capture_output=True, timeout=10,
        env=env, **platforms.background_options())
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')[:4000].strip()
    if result.returncode: raise ValueError('语言工具探测失败：' + output[:500])
    return output


def publish_directory(source, target, stop_event):
    # Windows may hold a just-executed compiler/JVM mapped briefly after exit.
    deadline = time.monotonic() + 5
    while True:
        if stop_event.is_set(): raise InterruptedError('环境准备已取消')
        try:
            source.rename(target)
            return
        except PermissionError:
            if time.monotonic() >= deadline: raise
            stop_event.wait(.1)


class ToolchainRegistry:
    def __init__(self, root=None, manifest_path=None):
        self.root = Path(root if root is not None else toolchains_dir()).resolve()
        self.manifest = load_manifest(Path(manifest_path or application_root() / 'packaging/toolchains.json'))
        self.lock = threading.RLock()
        self.states, self.ready, self.stops = {}, {}, {}
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='toolchain')
        self.closed = False

    def artifact(self, language):
        return next((item for item in self.manifest['artifacts'] if language in item['languages']
            and item['os'] == platforms.system_name() and item['arch'] == platforms.architecture()), None)

    def key(self, language):
        item = self.artifact(language)
        return item['id'] if item else 'system-' + ('clt' if language in ('c', 'cpp') else language)

    def _system(self, language):
        if language == 'python':
            verify_bundled_runtime()
            python = native_python()
            text = probe_output([python, '-I', '-S', '-B', '-c', 'import platform;print(platform.python_version())'])
            if not text.startswith('3.12.'): raise ValueError('需要内置 Python 3.12')
            return ResolvedToolchain('bundled-python-' + text, text, {'python': python})
        if platforms.system_name() != 'macos' or language not in ('c', 'cpp'):
            raise ValueError('此平台暂不支持该语言工具链')
        developer = Path(probe_output(['/usr/bin/xcode-select', '-p']))
        if not developer.is_dir(): raise ValueError('请安装 Apple Command Line Tools 后重新检查')
        candidates = (developer / 'usr/bin', developer / 'Toolchains/XcodeDefault.xctoolchain/usr/bin')
        directory = next((p for p in candidates if (p / 'clang').is_file() and (p / 'clang++').is_file()), None)
        if directory is None: raise ValueError('所选 Apple 开发工具缺少 clang/clang++')
        sdk = Path(probe_output(['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path']))
        if not sdk.is_dir(): raise ValueError('缺少 macOS SDK，请重新安装 Command Line Tools')
        version = probe_output([directory / 'clang', '--version']).splitlines()[0]
        return ResolvedToolchain('apple-clt-' + hashlib.sha256(version.encode()).hexdigest()[:12],
            version, {'cc': directory / 'clang', 'cxx': directory / 'clang++'}, sdk)

    def _resolve_installed(self, item):
        pointer = self.root / ('ready-' + item['id'] + '.json')
        if not pointer.is_file(): raise ValueError('语言环境尚未准备')
        receipt = json.loads(pointer.read_text(encoding='utf-8'))
        if receipt.get('sha256') != item['sha256']: raise ValueError('语言环境版本已变化，请重新准备')
        directory = (self.root / receipt['directory']).resolve()
        if not directory.is_relative_to(self.root): raise ValueError('语言环境路径无效')
        return self._probe(item, directory)

    def _probe(self, item, directory):
        base = (directory / item['root']).resolve()
        if not base.is_relative_to(directory): raise ValueError('语言环境根路径无效')
        entries = {name: (base / relative).resolve() for name, relative in item['executables'].items()}
        if any(not path.is_relative_to(base) or not path.is_file() for path in entries.values()):
            raise ValueError('语言环境入口缺失，请重新准备')
        env = command_env(entries)
        for name, path in entries.items():
            text = probe_output([path, '-version' if name == 'java' else '--version'], env)
            if name in ('java', 'javac') and not re.search(r'\b21[.\s"]', text):
                raise ValueError('需要 Java 21 工具链')
            if name == 'node' and not text.startswith('v24.'):
                raise ValueError('需要 Node.js 24 工具链')
        return ResolvedToolchain(item['id'], item['version'], entries)

    def capability(self, language):
        if language not in LANGUAGES: return dict(language=language, available=False, state='unsupported', error='可编辑，暂不支持运行')
        key = self.key(language)
        with self.lock:
            state = self.states.get(key)
            if state: return {**state, 'language': language}
            try:
                resolved = self.ready.get(key)
                if resolved is None:
                    item = self.artifact(language)
                    resolved = self._resolve_installed(item) if item else self._system(language)
                    self.ready[key] = resolved
                result = dict(state='ready', available=True, runtime_version=resolved.version, toolchain_id=resolved.id,
                    sdk=str(resolved.sdk) if resolved.sdk else None)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                result = dict(state='needs_system_tool' if language in ('c', 'cpp') and platforms.system_name() == 'macos'
                    else 'unprepared', available=False, error=str(exc), runtime_version=self.artifact(language)['version'] if self.artifact(language) else '')
            return {**result, 'language': language}

    def resolve(self, language):
        status = self.capability(language)
        if not status['available']: raise ValueError(status.get('error', '语言环境尚未准备'))
        with self.lock: return self.ready[self.key(language)]

    def _state(self, key, **values):
        with self.lock: self.states[key].update(values)

    def prepare(self, language):
        if language not in LANGUAGES: raise ValueError('此语言暂不支持执行')
        key = self.key(language)
        with self.lock:
            if self.closed: raise ValueError('语言环境服务正在关闭')
            if key in self.states and self.states[key]['state'] in ('downloading', 'verifying', 'extracting'):
                return {**self.states[key], 'language': language}
            if not self.artifact(language):
                self.ready.pop(key, None)
                self.states.pop(key, None)
                return self.capability(language)
            if self.capability(language)['available']: return self.capability(language)
            job = uuid4().hex
            stop = self.stops[key] = threading.Event()
            self.states[key] = dict(job_id=job, state='downloading', available=False, error='')
            result = {**self.states[key], 'language': language}
            self.pool.submit(self._prepare, key, self.artifact(language), job, stop)
            return result

    def _prepare(self, key, item, job, stop):
        lock_path = self.root / ('lock-' + key)
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            # OS advisory lock is released after crashes, without deleting shared environments.
            with lock_path.open('a+b') as lock_file:
                if os.name == 'nt':
                    import msvcrt
                    if lock_file.tell() == 0: lock_file.write(b'0'); lock_file.flush()
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                stage = self.root / ('staging-' + job)
                stage.mkdir()
                package = stage / ('download.' + item['archive'])
                archive.download_archive(item['url'], package, item['sha256'], stop)
                self._state(key, state='verifying')
                if stop.is_set(): raise InterruptedError('环境准备已取消')
                self._state(key, state='extracting')
                extracted = stage / 'content'
                archive.extract_archive(package, extracted, item['archive'], stop)
                resolved = self._probe(item, extracted)
                self._smoke(resolved, stage, stop)
                if stop.is_set(): raise InterruptedError('环境准备已取消')
                target = self.root / (item['id'] + '-' + job)
                publish_directory(extracted, target, stop)
                receipt = dict(directory=target.name, sha256=item['sha256'], version=item['version'])
                temporary = self.root / ('receipt-' + job + '.json')
                temporary.write_text(json.dumps(receipt), encoding='utf-8')
                temporary.replace(self.root / ('ready-' + key + '.json'))
                with self.lock:
                    self.ready[key] = self._probe(item, target)
                    self.states[key].update(state='ready', available=True, error='', runtime_version=item['version'], toolchain_id=key)
        except Exception as exc:
            self._state(key, state='failed', available=False, error=str(exc)[:1000])

    def _smoke(self, resolved, stage, stop):
        from ..native_process import execute_command
        from ..process_types import ProcessBudget
        entries, directory = resolved.executables, stage / 'smoke'
        directory.mkdir()
        if 'node' in entries:
            commands = [[entries['node'], '-e', 'process.stdout.write("ok")']]
        elif 'java' in entries:
            (directory / 'Main.java').write_text('public class Main {public static void main(String[] a){System.out.print("ok");}}')
            commands = [[entries['javac'], '-J-Xmx128m', 'Main.java'], [entries['java'], '-Xmx128m', '-cp', '.', 'Main']]
        else:
            (directory / 'main.cpp').write_text('#include <iostream>\nint main(){std::cout<<"ok";}')
            output = directory / ('main.exe' if os.name == 'nt' else 'main')
            commands = [[entries['cxx'], '-std=c++17', 'main.cpp', '-o', output], [output]]
        result = None
        for argv in commands:
            result = execute_command(argv, directory, command_env(entries), budget=ProcessBudget(30, 20, 1024, 262144), stop_event=stop)
            if result['status'] != 'executed': raise ValueError('语言工具链基础测试失败：' + result['stderr'][:1000])
        if result['stdout'] != 'ok': raise ValueError('语言工具链基础输出不符')

    def cancel(self, language):
        with self.lock:
            stop = self.stops.get(self.key(language))
            if stop: stop.set()
        return self.capability(language)

    def close(self):
        with self.lock:
            self.closed = True
            for stop in self.stops.values(): stop.set()
        self.pool.shutdown(wait=True, cancel_futures=True)
