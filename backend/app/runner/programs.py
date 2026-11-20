"""Prepare one isolated program once; samples only execute its final argv."""
from dataclasses import dataclass
from pathlib import Path
import os
from uuid import UUID

from .languages import get_language, COMPILE_BUDGET
from .native_process import execute_command
from .process_types import ProcessBudget
from .toolchains.registry import command_env


@dataclass(frozen=True)
class PreparedProgram:
    language: str
    argv: list[str]
    cwd: Path
    env: dict[str, str]
    runtime_version: str
    toolchain_id: str
    compile_result: dict | None
    limits: ProcessBudget


class PreparationError(Exception):
    def __init__(self, status, diagnostics, metadata):
        super().__init__(diagnostics.get('stderr') or status)
        self.status, self.diagnostics, self.metadata = status, diagnostics, metadata


class ProgramPreparer:
    def __init__(self, root, registry, *, supervisor=execute_command):
        self.root, self.registry, self.supervisor = Path(root).resolve(), registry, supervisor

    def prepare(self, job_id, language, source, stop_event, on_phase=None):
        if str(UUID(job_id)) != job_id: raise ValueError('运行编号无效')
        spec = get_language(language)
        toolchain = self.registry.resolve(language)
        entries = toolchain.executables
        directory = self.root / job_id
        directory.mkdir(parents=True, exist_ok=False)
        (directory / spec.filename).write_text(source, encoding='utf-8')
        env = command_env(entries)
        metadata = dict(language=language, runtime_version=toolchain.version, toolchain_id=toolchain.id)
        if on_phase: on_phase({'type': 'phase', 'status': 'preparing', **metadata})
        if stop_event.is_set(): raise PreparationError('stopped', {'stderr': '运行已停止'}, metadata)
        output = directory / ('main.exe' if os.name == 'nt' else 'main')
        compile_argv = None
        if language == 'python':
            argv = [str(entries['python']), '-I', '-S', '-B', '-u', '-X', 'utf8', spec.filename]
        elif language == 'javascript':
            argv = [str(entries['node']), '--max-old-space-size=128', spec.filename]
        elif language == 'java':
            compile_argv = [str(entries['javac']), '-J-Xmx128m', '-J-XX:ActiveProcessorCount=2',
                '-J-Dstdout.encoding=UTF-8', '-J-Dstderr.encoding=UTF-8', '-encoding', 'UTF-8', '-d', '.', spec.filename]
            argv = [str(entries['java']), '-Xmx128m', '-XX:ActiveProcessorCount=2', '-Dfile.encoding=UTF-8',
                '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', '-cp', '.', 'Main']
        else:
            compiler = entries['cc' if language == 'c' else 'cxx']
            compile_argv = [str(compiler), '-std=c17' if language == 'c' else '-std=c++17', '-O2', spec.filename, '-o', str(output)]
            if toolchain.sdk: compile_argv += ['-isysroot', str(toolchain.sdk)]
            argv = [str(output)]
        diagnostic = None
        if compile_argv:
            if on_phase: on_phase({'type': 'phase', 'status': 'compiling', **metadata})
            diagnostic = self.supervisor(compile_argv, directory, env, budget=COMPILE_BUDGET, stop_event=stop_event)
            if diagnostic['status'] != 'executed':
                status = {'runtime_error': 'compile_error', 'syntax_error': 'compile_error',
                          'time_limit': 'compile_time_limit'}.get(diagnostic['status'], diagnostic['status'])
                raise PreparationError(status, diagnostic, metadata)
            artifact = directory / 'Main.class' if language == 'java' else output
            if not artifact.is_file() or not artifact.resolve().is_relative_to(directory):
                raise PreparationError('compile_error', {**diagnostic, 'stderr': diagnostic['stderr'] +
                    '\n未找到本次编译产物；Java 请使用无 package 的 Main 类。'}, metadata)
        return PreparedProgram(language, argv, directory, env, toolchain.version, toolchain.id, diagnostic, spec.run_budget)
