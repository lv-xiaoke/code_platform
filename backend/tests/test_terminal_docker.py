import os
import subprocess
import time
from uuid import uuid4

import pytest

from app.runner.terminal_docker import InteractiveDockerRunner
from test_terminal_api import start,wait_terminal


def test_terminal_command_keeps_container_isolation(tmp_path):
    runner=InteractiveDockerRunner(tmp_path)
    run_id=str(uuid4())
    command=runner.command(run_id,tmp_path/run_id)
    joined=' '.join(command)
    for value in ['--network none','--read-only','--user 65534:65534','--cap-drop ALL','--pids-limit 32','--memory 256m','--cpus 1','no-new-privileges']:
        assert value in joined
    assert '-i' in command and '-t' not in command and '--pid=host' not in command
    assert '@sha256:' in joined and 'docker.sock' not in joined
    assert command[-1]=='/opt/codetop-interactive.py'


docker=pytest.mark.skipif(os.environ.get('CODETOP_TERMINAL_TESTS')!='1',reason='explicit real terminal Docker tests')


@docker
def test_real_terminal_prompts_unicode_multiple_input_eof_and_history(loaded):
    c,app,_,pid=loaded
    run=start(c,pid,'a=input("第一行> "); print("收到",a); b=input("第二行> "); print("合计",a+b); print("余下",repr(__import__("sys").stdin.read()))')
    wait_terminal(c,run['id'],lambda r:'第一行> ' in r['stdout'])
    time.sleep(2.2)
    assert c.get('/api/v1/terminals/'+run['id']).json()['status']=='running'
    for line,prompt in [('你好\n','第二行> '),('世界\n','合计 你好世界')]:
        response=c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'text':line})
        assert response.status_code==200,response.text
        wait_terminal(c,run['id'],lambda r:prompt in r['stdout'])
    c.post('/api/v1/terminals/'+run['id']+'/input',json={'request_id':str(uuid4()),'eof':True})
    final=wait_terminal(c,run['id'])
    assert final['status']=='executed',final
    assert "余下 ''" in final['stdout'] and final['stdin']=='你好\n世界\n'
    assert '你好\n' in final['transcript']
    assert c.get('/api/v1/runs/'+run['id']).json()['results'][0]['status']=='executed'


@docker
def test_real_terminal_stop_isolation_descendant_cleanup(loaded):
    c,app,_,pid=loaded
    source='''import os,socket,subprocess,sys
assert os.getuid()==65534
assert not os.path.exists('/work/study.sqlite3')
try:
    socket.create_connection(('1.1.1.1',80),timeout=.2)
    raise AssertionError('network available')
except OSError: pass
subprocess.Popen([sys.executable,'-c','import time; time.sleep(100)'],start_new_session=True)
print('READY',flush=True)
input()
'''
    run=start(c,pid,source)
    wait_terminal(c,run['id'],lambda r:'READY' in r['stdout'])
    response=c.post('/api/v1/terminals/'+run['id']+'/stop')
    assert response.status_code==200,response.text
    assert response.json()['status']=='stopped',response.json()
    check=subprocess.run([app.state.terminal_service.runner.docker,'inspect','codetop-run-'+run['id']],capture_output=True,timeout=10)
    assert check.returncode!=0


@docker
@pytest.mark.parametrize('source,status',[
    ('raise ValueError("visible error")','runtime_error'),
    ('while True: print("x"*8192)','output_limit'),
    ('while True: pass','time_limit'),
])
def test_real_terminal_errors_and_limits(loaded,source,status):
    c,_,_,pid=loaded
    run=start(c,pid,source)
    final=wait_terminal(c,run['id'],timeout=20)
    assert final['status']==status,final
    assert len(final['stdout'].encode())<=65536


@docker
def test_real_terminal_supervisor_fds_are_private(loaded):
    c,_,_,pid=loaded
    source='''import os
for path,mode in [('/proc/1/fd/1',os.O_WRONLY),('/proc/1/fd/0',os.O_RDONLY)]:
    try: fd=os.open(path,mode)
    except PermissionError: pass
    else:
        os.close(fd)
        raise AssertionError('supervisor file descriptor accessible: '+path)
print('PRIVATE')
'''
    final=wait_terminal(c,start(c,pid,source)['id'])
    assert final['status']=='executed',final
    assert 'PRIVATE' in final['stdout']


@docker
def test_real_terminal_cpu_budget_includes_subprocesses(loaded):
    c,_,_,pid=loaded
    source='''import subprocess,sys
child='import time; end=time.process_time()+0.7\\nwhile time.process_time()<end: pass'
for _ in range(8): subprocess.run([sys.executable,'-c',child],check=True)
print('UNLIMITED')
'''
    final=wait_terminal(c,start(c,pid,source)['id'],timeout=20)
    assert final['status']=='time_limit',final
