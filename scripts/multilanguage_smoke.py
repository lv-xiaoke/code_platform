"""Exercise a running source/packaged server, using an explicitly isolated data path."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

SOURCES = {
    'python': 'import sys\nfor line in sys.stdin: print(line.rstrip("\\n"),flush=True)',
    'c': '#include <stdio.h>\nint main(void){char s[256];while(fgets(s,sizeof s,stdin)){fputs(s,stdout);fflush(stdout);}return 0;}',
    'cpp': '#include <iostream>\n#include <string>\nint main(){std::string s;while(std::getline(std::cin,s))std::cout<<s<<std::endl;}',
    'java': 'import java.io.*;public class Main{public static void main(String[] a)throws Exception{var r=new BufferedReader(new InputStreamReader(System.in,"UTF-8"));String s;while((s=r.readLine())!=null){System.out.println(s);System.out.flush();}}}',
    'javascript': 'process.stdout.write(require("fs").readFileSync(0,"utf8"))',
}
ACTIVE = {'queued','starting','preparing','compiling','running','stopping'}


def verify_server(base_url, *, expected_data_dir, require_all=True):
    base_url = base_url.rstrip('/')
    parts = urllib.parse.urlsplit(base_url)
    if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('Smoke validation requires a loopback server')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {'Origin': base_url}
    def request(path, payload=None, method=None):
        body = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(base_url + '/api/v1' + path, data=body,
            headers={**headers, 'Content-Type': 'application/json'}, method=method)
        with opener.open(req, timeout=15) as response: return json.load(response)
    def wait(path, timeout=50):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = request(path)
            if value['status'] not in ACTIVE: return value
            time.sleep(.05)
        raise TimeoutError('Execution did not finish: ' + path)
    health = request('/health')
    if health.get('app') != 'codetop-local' or Path(health['data_dir']).resolve() != Path(expected_data_dir).resolve():
        raise ValueError('Server must use the explicitly named validation data directory')
    headers['X-Session-Token'] = request('/session')['token']
    pid = request('/problems')['items'][0]['id']
    request('/runner/consent', {'accepted': True})
    capabilities = request('/runner/languages')['languages']
    report = dict(health={k:health.get(k) for k in ('app','schema_version','process_id')}, languages=[], passed=False)
    for capability in capabilities:
        language = capability['language']
        if not capability['available']:
            if require_all: raise ValueError('Required language unavailable: ' + json.dumps(capability))
            report['languages'].append(dict(language=language, skipped=capability))
            continue
        source = SOURCES[language]
        job = request(f'/problems/{pid}/runs', dict(request_id=uuid4().hex, source_code=source, language=language,
            cases=[dict(stdin='你好\n', expected_stdout='你好\n'), dict(stdin='two\n', expected_stdout='two\n')]))
        run = wait('/runs/' + job['id'])
        if run['status'] != 'completed' or [case['status'] for case in run['results']] != ['passed','passed']:
            raise ValueError('Batch failed: ' + json.dumps(run, ensure_ascii=False))
        terminal = request(f'/problems/{pid}/terminals', dict(request_id=uuid4().hex, source_code=source, language=language))
        deadline = time.monotonic() + 40
        while terminal['status'] != 'running' and time.monotonic() < deadline:
            if terminal['status'] not in ACTIVE: raise ValueError('Terminal preparation failed: ' + json.dumps(terminal))
            time.sleep(.05)
            terminal = request('/terminals/' + terminal['id'])
        request('/terminals/' + terminal['id'] + '/input', dict(request_id=uuid4().hex, text='交互你好\n'))
        request('/terminals/' + terminal['id'] + '/input', dict(request_id=uuid4().hex, eof=True))
        final = wait('/terminals/' + terminal['id'])
        if final['status'] != 'executed' or final['stdout'].replace('\r\n','\n') != '交互你好\n':
            raise ValueError('Terminal/EOF failed: ' + json.dumps(final, ensure_ascii=False))
        if language in ('c','cpp','java'):
            bad = request(f'/problems/{pid}/runs', dict(request_id=uuid4().hex, source_code='invalid source {', language=language, cases=[{'stdin':''}]))
            failure = wait('/runs/' + bad['id'])
            if failure['status'] != 'compile_error' or not failure['compile']['stderr']:
                raise ValueError('Compile diagnostics missing: ' + language)
        report['languages'].append(dict(language=language, runtime_version=run['runtime_version'], toolchain_id=run['toolchain_id'],
            batch='passed', terminal='passed', compile_error='passed' if language in ('c','cpp','java') else 'not-applicable', limits=run['limits']))
    report['passed'] = True
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--require-all', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = verify_server(args.base_url, expected_data_dir=args.data_dir, require_all=args.require_all)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
