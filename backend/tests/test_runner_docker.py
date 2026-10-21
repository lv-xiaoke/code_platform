"""Opt-in real Docker acceptance, without a host execution fallback."""
import os
from uuid import uuid4

import pytest

from app.runner.docker import DockerRunner

pytestmark=pytest.mark.skipif(os.environ.get('CODETOP_DOCKER_TESTS')!='1',reason='Set CODETOP_DOCKER_TESTS=1 to run actual Docker acceptance')


@pytest.mark.parametrize('code,cases,status',[
    ('print(input())',[{'stdin':'你好 ACM\n','expected_stdout':'你好 ACM','comparison':'tokens','name':'Unicode'}],'passed'),
    ('print(42)',[{'stdin':'','expected_stdout':'43','comparison':'tokens','name':'wrong'}],'wrong_answer'),
    ('print()', [{'stdin':'','expected_stdout':None,'comparison':'tokens','name':'run only'}],'executed'),
    ('if :', [{'stdin':'','expected_stdout':None,'comparison':'tokens','name':'syntax'}],'syntax_error'),
    ('raise ValueError("example")',[{'stdin':'','expected_stdout':None,'comparison':'tokens','name':'exception'}],'runtime_error'),
    ('while True: pass',[{'stdin':'','expected_stdout':None,'comparison':'tokens','name':'loop'}],'time_limit'),
    ('while True: print("x"*8192)',[{'stdin':'','expected_stdout':None,'comparison':'tokens','name':'output'}],'output_limit'),
    ('import socket\ntry:\n socket.create_connection(("1.1.1.1",80),timeout=0.2)\n print("connected")\nexcept OSError:\n print("blocked")',[{'stdin':'','expected_stdout':'blocked','comparison':'tokens','name':'network'}],'passed'),
    ('import os\nprint(os.getuid(), os.path.exists("/data/study.sqlite3"))',[{'stdin':'','expected_stdout':'65534 False','comparison':'tokens','name':'isolation'}],'passed'),
])
def test_actual_docker_limits_and_results(tmp_path,code,cases,status):
    result=DockerRunner(tmp_path).execute(str(uuid4()),code,cases)
    assert result['results'][0]['status']==status,result
    assert len(result['results'][0]['stdout'].encode('utf-8'))<=65536
    assert result['results'][0]['duration_ms']>=0
    assert '@sha256:' in result['image_ref']


@pytest.mark.parametrize('detached',[True,False])
def test_case_descendants_do_not_survive_or_exhaust_pids(tmp_path,detached):
    code='''import os, sys, time
from pathlib import Path
if input() == 'spawn':
    for _ in range(20):
        if os.fork() == 0:
            if DETACHED:
                os.setsid()
                os.close(1); os.close(2)
                time.sleep(20)
            os._exit(0)
    print('spawned')
else:
    others=[p for p in Path('/proc').iterdir() if p.name.isdigit() and int(p.name) not in (1,os.getpid())]
    print(len(others))
'''.replace('DETACHED',repr(detached))
    cases=[{'stdin':'spawn\n','expected_stdout':'spawned','comparison':'tokens','name':'fork'} for _ in range(2)]
    cases.append({'stdin':'inspect\n','expected_stdout':'0','comparison':'tokens','name':'no remaining processes'})
    result=DockerRunner(tmp_path).execute(str(uuid4()),code,cases)
    assert all(c['status']=='passed' for c in result['results']),result


def test_twenty_legal_escaped_outputs_fit_transport(tmp_path):
    cases=[{'stdin':'','expected_stdout':None,'comparison':'exact','name':str(i)} for i in range(20)]
    result=DockerRunner(tmp_path).execute(str(uuid4()),'import sys; sys.stdout.write(chr(0)*60000)',cases)
    assert all(c['status']=='executed' and c['stdout']=='\0'*60000 for c in result['results'])
