from .native import NativeRunner


class NativeTerminalRunner(NativeRunner):
    def execute(self, session):
        from .native_process import execute_command
        from .programs import ProgramPreparer
        from .languages import COMPILE_BUDGET
        from dataclasses import replace, asdict
        self.register(session.stop_event)
        try:
            program = ProgramPreparer(self.artifact_root, self.toolchains()).prepare(
                session.id, session.language, session.source_code, session.stop_event, on_phase=session.emit)
            limits = replace(program.limits, wall_seconds=300)
            metadata = dict(language=program.language, runtime_version=program.runtime_version,
                toolchain_id=program.toolchain_id, compile=program.compile_result,
                limits={**asdict(limits), 'compile': asdict(COMPILE_BUDGET) if program.compile_result is not None else None})
            if program.language == 'python': metadata['python_version'] = program.runtime_version
            session.emit({'type': 'ready', **metadata})
            result = execute_command(program.argv, program.cwd, program.env, budget=limits,
                inputs=session.inputs, stop_event=session.stop_event,
                on_output=lambda name, text: session.emit({'type': name, 'text': text}))
            return {**metadata, **{key: value for key, value in result.items() if key not in ('stdout', 'stderr')}}
        finally:
            with self.lock:
                self.active.discard(session.stop_event)
