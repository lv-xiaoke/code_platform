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
