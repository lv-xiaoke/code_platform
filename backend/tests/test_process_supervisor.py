import os
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform not in ('win32', 'darwin'), reason='native supported hosts')


def command(tmp_path, source, *, output=1024, stop=None, wall=3):
    from app.runner.native_process import execute_command
    from app.runner.process_types import ProcessBudget
    from app.paths import native_python
    python = native_python()
    env = {k: v for k, v in os.environ.items() if k.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
    return execute_command([str(python), '-I', '-S', '-B', '-c', source], tmp_path, env,
        budget=ProcessBudget(wall, 3, 256, output), stop_event=stop)


def test_command_argv_and_combined_output_budget(tmp_path):
    result = command(tmp_path, 'import sys;sys.stdout.write("a"*700);sys.stdout.flush();sys.stderr.write("b"*700)')
    assert result['status'] == 'output_limit'
    assert len((result['stdout'] + result['stderr']).encode()) <= 1024


def test_pre_cancelled_command_never_executes(tmp_path):
    stop = threading.Event()
    stop.set()
    result = command(tmp_path, 'open("ran", "w").write("bad")', stop=stop)
    assert result['status'] == 'stopped'
    assert not (tmp_path / 'ran').exists()


def test_truncated_unicode_is_valid_and_wall_limit_independent(tmp_path):
    result = command(tmp_path, 'print("你"*1000)', output=100)
    assert result['status'] == 'output_limit'
    assert '\ufffd' not in result['stdout']
    assert len(result['stdout'].encode()) <= 100
    result = command(tmp_path, 'import time;time.sleep(10)', wall=.15)
    assert result['status'] == 'time_limit'


def test_parent_exit_reaps_pipe_inheriting_children(tmp_path):
    result = command(tmp_path, 'import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]);print("parent")')
    assert result['status'] == 'executed'
    assert result['stdout'].strip() == 'parent'
    assert result['duration_ms'] < 6000
