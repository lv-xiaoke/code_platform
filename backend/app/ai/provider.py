import json
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

ENDPOINT = 'https://api.deepseek.com/chat/completions'


class ProviderError(Exception): pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError('AI 接口发生重定向，已停止连接')


class DeepSeekProvider:
    def stream(self, key, model, messages, stop):
        body = json.dumps({'model':model,'messages':messages,'stream':True,
                           'thinking':{'type':'disabled'},'max_tokens':4096}).encode()
        request = Request(ENDPOINT,data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
        started = time.monotonic()
        try:
            with build_opener(NoRedirect()).open(request,timeout=15) as response:
                while not stop.is_set():
                    if time.monotonic()-started > 120: raise ProviderError('回答时间较长，已停止。可以缩短问题后重试。')
                    line = response.readline(1024*1024+1)
                    if len(line)>1024*1024: raise ProviderError('AI 响应过大，已停止')
                    if not line: raise ProviderError('AI 连接中断，已保留收到的内容，请重试')
                    if not line.startswith(b'data:'): continue
                    data = line[5:].strip()
                    if data == b'[DONE]': return
                    try:
                        event = json.loads(data)
                        if event.get('error'): raise ProviderError('AI 服务返回错误，请稍后重试')
                        for choice in event.get('choices',[]):
                            text = choice.get('delta',{}).get('content')
                            if isinstance(text,str): yield text
                            if choice.get('finish_reason') == 'length':
                                yield '\n\n（本次回答已达到长度上限，可继续追问。）'
                    except (ValueError,TypeError,AttributeError): raise ProviderError('AI 响应格式异常，请重试') from None
        except HTTPError as error:
            messages = {401:'API Key 无效，请在 AI 设置中检查',402:'DeepSeek 余额不足，请检查账户',429:'请求过于频繁，请稍后重试'}
            raise ProviderError(messages.get(error.code,'AI 服务暂时不可用，请稍后重试')) from None
        except (URLError,TimeoutError,OSError):
            raise ProviderError('连接 DeepSeek 失败或超时，请检查网络后重试') from None
