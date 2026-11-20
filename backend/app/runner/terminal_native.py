from .native import NativeRunner


class NativeTerminalRunner(NativeRunner):
    def execute(self, session):
        from .native_process import execute_process
        health = self.health()
        if not health['available']:
            raise RuntimeError(health['error'])
        self.register(session.stop_event)
        try:
            script = self.directory(session.id, session.source_code)
            session.emit({'type': 'ready', 'python_version': self.python_version})
            result = execute_process(self.python, script, inputs=session.inputs, stop_event=session.stop_event,
                                     on_output=lambda name, text: session.emit({'type': name, 'text': text}), wall_seconds=300)
            return {key: value for key, value in result.items() if key not in ('stdout', 'stderr')}
        finally:
            with self.lock:
                self.active.discard(session.stop_event)
