import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.response import addinfourl

import pytest
from app.ai import provider


@pytest.mark.skipif(os.name != 'nt', reason='Windows system proxy')
@pytest.mark.parametrize(('system_proxy', 'explicit_proxy', 'expected_host'), [
    ('http://127.0.0.1:7877', None, 'api.deepseek.com'),
    ('http://[::1]:7877', None, 'api.deepseek.com'),
    ('http://127.0.0.1:7877', 'http://127.0.0.1:8899', '127.0.0.1:8899'),
    ('http://proxy.example:8080', None, 'proxy.example:8080'),
])
def test_deepseek_proxy_routing(monkeypatch, system_proxy, explicit_proxy, expected_host):
    for name in os.environ:
        if name.lower().endswith('_proxy'):
            monkeypatch.delenv(name)
    if explicit_proxy:
        monkeypatch.setenv('HTTPS_PROXY', explicit_proxy)
    monkeypatch.setattr(urllib.request, 'getproxies_registry', lambda: {'https': system_proxy})
    monkeypatch.setattr(urllib.request, 'proxy_bypass_registry', lambda host: False)

    def respond(handler, request):
        assert request.host == expected_host
        body = BytesIO(b'data: {"choices":[{"delta":{"content":"OK"}}]}\n\ndata: [DONE]\n\n')
        response = addinfourl(body, {}, request.full_url, 200)
        response.msg = 'OK'
        return response

    monkeypatch.setattr(urllib.request.HTTPSHandler, 'https_open', respond)
    reply = provider.DeepSeekProvider().stream('sk-test', 'deepseek-flash', [], threading.Event())
    assert ''.join(reply) == 'OK'


def test_real_http_stream_unicode_and_redacted_errors(monkeypatch):
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            received.append(body)
            if body['model']=='redirect':
                self.send_response(307)
                self.send_header('Location','https://example.com/do-not-send-key')
                self.end_headers();return
            self.send_response(401 if body['model']=='unauthorized' else 200)
            self.end_headers()
            if body['model']=='unauthorized':
                self.wfile.write(b'sk-private-do-not-display');return
            self.wfile.write(b': keepalive\n\n')
            for text in ['你好','，世界']:
                event={'choices':[{'delta':{'content':text}}]}
                self.wfile.write(('data: '+json.dumps(event,ensure_ascii=False)+'\n\n').encode())
                self.wfile.flush()
            self.wfile.write(b'data: [DONE]\n\n')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setattr(provider,'ENDPOINT',f'http://127.0.0.1:{server.server_port}/chat/completions')
    try:
        client=provider.DeepSeekProvider()
        result=''.join(client.stream('sk-test','deepseek-flash',[{'role':'user','content':'hello'}],threading.Event()))
        assert result=='你好，世界'
        assert received[0]['stream'] is True
        with pytest.raises(provider.ProviderError,match='API Key 无效') as error:
            list(client.stream('sk-private','unauthorized',[],threading.Event()))
        assert 'sk-private' not in str(error.value)
        with pytest.raises(provider.ProviderError,match='重定向'):
            list(client.stream('sk-private','redirect',[],threading.Event()))
    finally: server.shutdown();server.server_close();thread.join()


def test_failed_reply_is_persisted_and_retry_creates_new_turn(loaded):
    from test_ai import configure,ask,wait_chat
    c,app,_,pid=loaded
    configure(c)
    def broken(key,model,messages,stop):
        yield '已收到部分'
        raise provider.ProviderError('连接中断')
    app.state.ai_service.provider.stream=broken
    assert ask(c,pid).status_code==202
    final=wait_chat(c,pid)
    assert final['messages'][-1]['status']=='failed'
    assert final['messages'][-1]['content']=='已收到部分'
    def working(key,model,messages,stop): yield 'retry works'
    app.state.ai_service.provider.stream=working
    assert ask(c,pid).status_code==202
    assert wait_chat(c,pid)['messages'][-1]['content']=='retry works'
    # A fresh service sees saved conversations and marks interrupted replies.
    from app.ai.service import AiService
    chat=app.state.ai_service._chat(pid)
    chat['messages'][-1]['status']='generating'
    app.state.ai_service._save('ai.chat:'+pid,chat)
    restarted=AiService(app.state.db,app.state.clock)
    assert restarted.get(pid)['messages'][-1]['status']=='interrupted'
    restarted.close()


def test_storage_failure_releases_worker_capacity(loaded,monkeypatch):
    from test_ai import configure,ask
    c,app,_,pid=loaded
    configure(c)
    gate=threading.Event()
    def stream(key,model,messages,stop):
        gate.wait(2)
        yield 'reply'
    service=app.state.ai_service
    service.provider.stream=stream
    assert ask(c,pid).status_code==202
    worker=service.active[pid][1]
    def fail(*args,**kwargs): raise OSError('disk full')
    monkeypatch.setattr(service,'_save',fail)
    gate.set();worker.join(3)
    assert pid not in service.active
    final=service.get(pid)
    assert not final['busy']
    assert final['messages'][-1]['status']=='failed'
