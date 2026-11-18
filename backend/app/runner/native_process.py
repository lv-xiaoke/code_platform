"""Bounded pipe transport; user output is never a supervisor protocol."""
import codecs
import os
import queue
import threading
import time

from .windows_job import JobProcess

LIMIT = 65536


def execute_process(python, script, *, stdin=None, inputs=None, stop_event=None,
                    on_output=None, wall_seconds=2, cpu_seconds=3):
    stop_event = stop_event or threading.Event()
    env = {k: v for k, v in os.environ.items() if k.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'COMSPEC', 'SYSTEMDRIVE')}
    env['PATH'] = str(python.parent)
    process = JobProcess([python, '-I', '-S', '-B', '-u', '-X', 'utf8', script], script.parent, env)
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
            while data := getattr(process, name).read(8192):
                post((name, data))
        except (OSError, ValueError):
            pass
        finally:
            post((name, None))

    def write():
        try:
            if inputs is None:
                data = (stdin or '').encode('utf-8')
                if len(data) > LIMIT:
                    raise ValueError('输入超过 64 KiB')
                while data:
                    written = process.stdin.write(data)
                    data = data[written:]
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
                    # Raw FileIO writes can be partial on Windows pipes.
                    while data:
                        written = process.stdin.write(data)
                        data = data[written:]
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
    ended, exit_code, parent_done = set(), None, False
    try:
        while len(ended) < 2 or exit_code is None:
            memory = process.limit_events()
            if status == 'executed':
                if stop_event.is_set():
                    status = 'stopped'
                elif memory:
                    status = 'memory_limit'
                elif time.monotonic() - started > wall_seconds or process.cpu_seconds() > cpu_seconds:
                    status = 'time_limit'
                if status != 'executed':
                    process.terminate()
            exit_code = process.poll()
            if exit_code is not None and not parent_done:
                parent_done = True
                process.terminate()  # reap children that inherited output pipe handles
            try:
                name, data = events.get(timeout=.02)
            except queue.Empty:
                continue
            if data is None:
                ended.add(name)
                text = decoders[name].decode(b'', final=True) if total <= LIMIT else ''
            else:
                kept = data[:max(0, LIMIT - total)]
                total += len(data)
                buffers[name].extend(kept)
                # Do not manufacture a replacement character from a truncated codepoint.
                text = decoders[name].decode(kept, final=False)
                if total > LIMIT and status == 'executed':
                    status = 'output_limit'
                    process.terminate()
            if text and on_output:
                on_output(name, text)
        process.limit_events()
        output = {name: value.decode('utf-8', errors='ignore') for name, value in buffers.items()}
        if status == 'executed':
            if process.memory_exceeded or (exit_code and 'MemoryError' in output['stderr']):
                status = 'memory_limit'
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
