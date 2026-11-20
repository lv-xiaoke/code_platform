import json
import os
from pathlib import Path
import subprocess
import threading
from uuid import UUID

from ..paths import native_python, verify_bundled_runtime
from .. import platforms
from .comparison import compare_output


class NativeRunner:
    kind = 'native'

    def __init__(self, artifact_root, registry=None):
        self.artifact_root = Path(artifact_root).resolve()
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.python = native_python()
        suffix = 'macos-' + platforms.architecture() if platforms.system_name() == 'macos' else 'windows-x64'
        self.image_ref = 'local-python@3.12-' + suffix
        self.python_version = '3.12'
        self.lock = threading.Lock()
        self.active = set()
        self.closed = False
        self.verified = False
        self.registry = registry
        self.owns_registry = False

    def toolchains(self):
        with self.lock:
            if self.registry is None:
                from .toolchains.registry import ToolchainRegistry
                self.registry = ToolchainRegistry()
                self.owns_registry = True
            return self.registry

    def health(self):
        try:
            if platforms.system_name() not in ('windows', 'macos') or not self.python.is_file():
                raise ValueError('内置 Python 不存在或此系统暂不支持，请重新安装完整桌面版')
            if not self.verified:
                verify_bundled_runtime()
                self.verified = True
            result = subprocess.run([str(self.python), '-I', '-S', '-B', '-X', 'utf8', '-c',
                                     'import json,sys; print(json.dumps(sys.version_info[:3]))'],
                                    capture_output=True, timeout=5, **platforms.background_options())
            version = json.loads(result.stdout)
            if result.returncode or version[:2] != [3, 12]:
                raise ValueError('本机运行需要随程序提供的 Python 3.12')
            self.python_version = '.'.join(map(str, version))
            suffix = 'windows-x64' if platforms.system_name() == 'windows' else 'macos-' + platforms.architecture()
            self.image_ref = 'local-python@' + self.python_version + '-' + suffix
            return {'available': True, 'kind': self.kind, 'label': '本机 Python', 'image_ref': self.image_ref,
                    'python_series': '3.12', 'limits': {'case_timeout_seconds': 2, 'memory_mb': 256, 'output_limit_bytes': 65536,
                    'memory_enforcement': 'rss-monitor' if platforms.system_name() == 'macos' else 'job-object'}}
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            return {'available': False, 'kind': self.kind, 'label': '本机 Python', 'image_ref': self.image_ref,
                    'python_series': '3.12', 'error': str(exc), 'limits': {}}

    def register(self, event):
        with self.lock:
            if self.closed:
                raise RuntimeError('运行环境正在关闭')
            self.active.add(event)

    def close(self):
        with self.lock:
            self.closed = True
            for event in self.active:
                event.set()
        if self.owns_registry: self.registry.close()

    def directory(self, run_id, source):
        if str(UUID(run_id)) != run_id:
            raise ValueError('运行编号无效')
        path = self.artifact_root / run_id
        path.mkdir(exist_ok=False)
        script = path / 'main.py'
        script.write_text(source, encoding='utf-8')
        return script

    def execute(self, job_id, source_code, cases, language='python', on_phase=None):
        from .native_process import execute_command
        from .programs import ProgramPreparer
        from dataclasses import asdict
        if not 1 <= len(cases) <= 20:
            raise ValueError('每次运行需要 1–20 组测试')
        if language == 'python':
            health = self.health()
            if not health['available']: raise RuntimeError(health['error'])
        event = threading.Event()
        self.register(event)
        try:
            program = ProgramPreparer(self.artifact_root, self.toolchains()).prepare(
                job_id, language, source_code, event, on_phase)
            if on_phase: on_phase({'type': 'phase', 'status': 'running', 'language': language})
            results = []
            for case in cases:
                if event.is_set():
                    raise RuntimeError('运行已停止')
                result = execute_command(program.argv, program.cwd, program.env, budget=program.limits,
                    stdin=case['stdin'], stop_event=event)
                if result['status'] == 'executed' and case.get('expected_stdout') is not None:
                    result['status'] = 'passed' if compare_output(result['stdout'], case['expected_stdout'], case.get('comparison', 'tokens')) else 'wrong_answer'
                results.append({**case, **result})
            return {'results': results, 'language': language, 'runtime_version': program.runtime_version,
                    'toolchain_id': program.toolchain_id, 'compile': program.compile_result,
                    'limits': asdict(program.limits),
                    **({'python_version': program.runtime_version} if language == 'python' else {})}
        finally:
            with self.lock:
                self.active.discard(event)
