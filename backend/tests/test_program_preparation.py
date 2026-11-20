import threading
from pathlib import Path
from uuid import uuid4

import pytest


def test_compile_failure_never_returns_runnable_program(tmp_path):
    from app.runner.programs import ProgramPreparer, PreparationError
    from app.runner.toolchains.registry import ResolvedToolchain
    class Registry:
        def resolve(self, language):
            return ResolvedToolchain('clang-test', '23', {'cc': Path('/compiler/clang'), 'cxx': Path('/compiler/clang++')})
    calls = []
    def failed(argv, cwd, env, **kwargs):
        calls.append(argv)
        return dict(status='runtime_error', exit_code=1, stdout='', stderr='missing semicolon', duration_ms=1)
    preparer = ProgramPreparer(tmp_path, Registry(), supervisor=failed)
    with pytest.raises(PreparationError) as error:
        preparer.prepare(str(uuid4()), 'c', 'bad source', threading.Event())
    assert error.value.status == 'compile_error'
    assert error.value.diagnostics['stderr'] == 'missing semicolon'
    assert len(calls) == 1
    assert '-std=c17' in calls[0]


def test_java_preparation_uses_main_and_separate_heap_budget(tmp_path):
    from app.runner.programs import ProgramPreparer
    from app.runner.toolchains.registry import ResolvedToolchain
    class Registry:
        def resolve(self, language):
            return ResolvedToolchain('jdk-test', '21', {'java': Path('/jdk/java'), 'javac': Path('/jdk/javac')})
    calls = []
    def compile_ok(argv, cwd, env, **kwargs):
        calls.append((argv, kwargs['budget']))
        (cwd / 'Main.class').write_bytes(b'class')
        return dict(status='executed', exit_code=0, stdout='', stderr='', duration_ms=1)
    program = ProgramPreparer(tmp_path, Registry(), supervisor=compile_ok).prepare(
        str(uuid4()), 'java', 'public class Main {}', threading.Event())
    assert program.cwd.joinpath('Main.java').read_text() == 'public class Main {}'
    assert '-Xmx128m' in program.argv
    assert program.limits.memory_mb == 512
    assert calls[0][1].wall_seconds == 30
    assert calls[0][1].memory_mb == 1024


def test_saved_source_has_unique_job_directory_and_no_shell(tmp_path):
    from app.runner.programs import ProgramPreparer
    from app.runner.toolchains.registry import ResolvedToolchain
    class Registry:
        def resolve(self, language):
            return ResolvedToolchain('node-test', '24', {'node': Path('/node/node')})
    preparer = ProgramPreparer(tmp_path, Registry())
    first = preparer.prepare(str(uuid4()), 'javascript', 'console.log(1)', threading.Event())
    second = preparer.prepare(str(uuid4()), 'javascript', 'console.log(1)', threading.Event())
    assert first.cwd != second.cwd
    assert first.argv[1:] == ['--max-old-space-size=128', 'main.js']
    assert Path(first.argv[0]).as_posix() == '/node/node'
    assert first.compile_result is None
    with pytest.raises(ValueError):
        preparer.prepare('../escape', 'javascript', '', threading.Event())
