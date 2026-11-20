from pathlib import Path

import pytest

from app.runner.comparison import compare_output
from app.runner.docker import DockerRunner


@pytest.mark.parametrize('actual,expected,mode,passed',[
    ('1  2\n','1\n2','tokens',True),('1 2','2 1','tokens',False),
    ('','', 'exact',True),('\n','', 'exact',False),('a\r\n','a\n','exact',True),
    ('a\nb\na\n','b\na\na','unordered_lines',True),('a\nb','a\na\nb','unordered_lines',False),
    ('2','2.0','float',True),('0.333333333','0.333333','float',True),('nan','nan','float',False),
    ('1e10000','1e10000','float',False),('','0','float',False),
])
def test_output_comparisons(actual,expected,mode,passed):
    assert compare_output(actual,expected,mode) is passed


def test_command_is_pinned_and_isolated(tmp_path):
    runner=DockerRunner(tmp_path)
    job=tmp_path/'12345678-1234-1234-1234-123456789abc'
    job.mkdir()
    command=runner.command(job.name,job)
    joined=' '.join(command)
    for required in ['--network none','--read-only','--cap-drop ALL','--pids-limit 32','--memory 256m','--cpus 1','--user 65534:65534','no-new-privileges']:
        assert required in joined
    assert '@sha256:' in joined
    assert 'docker.sock' not in joined
    assert 'shell' not in command
    assert sum('type=bind' in arg for arg in command)==2
    assert str(job.resolve()) in joined
    with pytest.raises(ValueError): runner.command(job.name,tmp_path.parent)


def test_docker_batch_transport_stops_without_waiting_for_all_cases(tmp_path,monkeypatch):
    import sys
    import threading
    import time
    import subprocess
    from uuid import uuid4
    runner=DockerRunner(tmp_path)
    monkeypatch.setattr(runner,'command',lambda *args:[sys.executable,'-c','import time;time.sleep(30)'])
    monkeypatch.setattr(runner,'_control',lambda *args:subprocess.CompletedProcess([],0))
    stop=threading.Event()
    timer=threading.Timer(.15,stop.set)
    timer.start()
    started=time.monotonic()
    try:
        result=runner.execute(str(uuid4()),'while True: pass',[{'stdin':''} for _ in range(10)],stop_event=stop)
        assert time.monotonic()-started<5
        assert [case['status'] for case in result['results']]==['stopped']
    finally:
        timer.join()
