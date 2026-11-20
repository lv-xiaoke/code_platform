"""Bounded pipe transport; user output is never a supervisor protocol."""
import codecs
import os
import queue
import threading
import time
import select

from .. import platforms
from .process_types import ProcessBudget

LIMIT = 65536


def process_backend():
    if platforms.system_name() == 'macos':
        from .macos_process import MacProcess
        return MacProcess
    if platforms.system_name() == 'windows':
        from .windows_job import JobProcess
        return JobProcess
    raise ValueError('此系统暂不支持本机代码执行')


def execute_process(python, script, *, stdin=None, inputs=None, stop_event=None,
                    on_output=None, wall_seconds=2, cpu_seconds=3):
    env = {k: v for k, v in os.environ.items() if k.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'SYSTEMDRIVE')}
    env['PATH'] = str(python.parent)
    if platforms.system_name() == 'macos':
        for key in ('TMPDIR', 'LANG', 'LC_CTYPE'):
            if key in os.environ:
                env[key] = os.environ[key]
    return execute_command([python, '-I', '-S', '-B', '-u', '-X', 'utf8', script], script.parent, env,
        budget=ProcessBudget(wall_seconds, cpu_seconds, 256, LIMIT), stdin=stdin, inputs=inputs,
        stop_event=stop_event, on_output=on_output)


def execute_command(argv, cwd, env, *, budget, stdin=None, inputs=None, stop_event=None, on_output=None):
    stop_event = stop_event or threading.Event()
    if stop_event.is_set():
        return dict(status='stopped', stdout='', stderr='', exit_code=None, duration_ms=0)
    if stdin is not None and len(stdin.encode('utf-8')) > LIMIT:
        raise ValueError('输入超过 64 KiB')
    process = process_backend()(argv, cwd, env, memory_mb=budget.memory_mb,
        max_processes=budget.max_processes, cpu_seconds=budget.cpu_seconds)
    posix_pipes = os.name != 'nt'
    if posix_pipes:
        for stream in (process.stdin, process.stdout, process.stderr):
            os.set_blocking(stream.fileno(), False)
    events = queue.Queue(maxsize=32)
    done = threading.Event()
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    decoders = {name: codecs.getincrementaldecoder('utf-8')('replace') for name in buffers}
    status, total, started = 'executed', 0, time.monotonic()

    def post(item):
        while not done.is_set():
            try:
                events.put(item, timeout=.05)
                return
            except queue.Full:
                pass

    def read(name):
        try:
            stream = getattr(process, name)
            while not done.is_set():
                if posix_pipes:
                    if not select.select([stream.fileno()], [], [], .05)[0]:
                        continue
                    try:
                        data = os.read(stream.fileno(), 8192)
                    except BlockingIOError:
                        continue
                else:
                    data = stream.read(8192)
                if not data:
                    break
                post((name, data))
        except (OSError, ValueError):
            pass
        finally:
            post((name, None))

    def write_bytes(data):
        while data and not done.is_set() and not stop_event.is_set():
            if posix_pipes:
                if not select.select([], [process.stdin.fileno()], [], .05)[1]:
                    continue
                try:
                    written = os.write(process.stdin.fileno(), data[:8192])
                except BlockingIOError:
                    continue
            else:
                written = process.stdin.write(data)
            if not written:
                raise OSError('stdin pipe closed')
            data = data[written:]

    def write():
        try:
            if inputs is None:
                data = (stdin or '').encode('utf-8')
                if len(data) > LIMIT:
                    raise ValueError('输入超过 64 KiB')
                write_bytes(data)
            else:
                count = 0
                while not done.is_set() and not stop_event.is_set():
                    try:
                        message = inputs.get(timeout=.05)
                    except queue.Empty:
                        continue
                    data = message.get('text', '').encode('utf-8')
                    count += len(data)
                    if count > LIMIT:
                        raise ValueError('输入超过 64 KiB')
                    write_bytes(data)
                    if message.get('eof'):
                        break
        except (OSError, ValueError):
            pass
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    threads = [threading.Thread(target=read, args=(name,), daemon=True) for name in buffers]
    threads.append(threading.Thread(target=write, daemon=True))
    for thread in threads:
        thread.start()
    ended, exit_code, parent_done, drain_deadline = set(), None, False, None
    try:
        while len(ended) < 2 or exit_code is None:
            memory = process.limit_events()
            if status == 'executed':
                if stop_event.is_set():
                    status = 'stopped'
                elif memory:
                    status = 'memory_limit'
                elif time.monotonic() - started > budget.wall_seconds or process.cpu_seconds() > budget.cpu_seconds:
                    status = 'time_limit'
                if status != 'executed':
                    process.terminate()
            exit_code = process.poll()
            if exit_code is not None and not parent_done:
                parent_done = True
                process.terminate()  # reap children that inherited output pipe handles
                drain_deadline = time.monotonic() + 2
            if drain_deadline is not None and time.monotonic() > drain_deadline:
                break  # Detached children cannot hold this request's pipes indefinitely.
            try:
                name, data = events.get(timeout=.02)
            except queue.Empty:
                continue
            if data is None:
                ended.add(name)
                text = decoders[name].decode(b'', final=True) if total <= budget.output_bytes else ''
            else:
                kept = data[:max(0, budget.output_bytes - total)]
                total += len(data)
                buffers[name].extend(kept)
                # Do not manufacture a replacement character from a truncated codepoint.
                text = decoders[name].decode(kept, final=False)
                if total > budget.output_bytes and status == 'executed':
                    status = 'output_limit'
                    process.terminate()
            if text and on_output:
                on_output(name, text)
        process.limit_events()
        output = {name: value.decode('utf-8', errors='ignore') for name, value in buffers.items()}
        if status == 'executed':
            if process.memory_exceeded or (exit_code and 'MemoryError' in output['stderr']):
                status = 'memory_limit'
            elif platforms.system_name() == 'macos' and exit_code == -24:  # Darwin SIGXCPU
                status = 'time_limit'
            elif exit_code:
                status = 'syntax_error' if 'SyntaxError' in output['stderr'] or 'IndentationError' in output['stderr'] else 'runtime_error'
        return {**output, 'status': status, 'exit_code': exit_code,
                'duration_ms': round((time.monotonic() - started) * 1000, 2)}
    finally:
        done.set()
        process.terminate()
        for thread in threads:
            thread.join(timeout=3)
        process.close()
