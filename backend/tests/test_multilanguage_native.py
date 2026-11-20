import os
from pathlib import Path
from uuid import uuid4

import pytest

SOURCES = {
    'python': 'print(input())',
    'c': '#include <stdio.h>\nint main(void){char s[256];if(fgets(s,sizeof s,stdin))fputs(s,stdout);return 0;}',
    'cpp': '#include <iostream>\n#include <string>\nint main(){std::string s;std::getline(std::cin,s);std::cout<<s<<"\\n";}',
    'java': 'import java.io.*; public class Main {public static void main(String[] a)throws Exception{System.out.println(new BufferedReader(new InputStreamReader(System.in,"UTF-8")).readLine());}}',
    'javascript': 'process.stdout.write(require("fs").readFileSync(0,"utf8"))',
}
LIMIT_SOURCES = {
    'python': ('while True: pass', 'while True: print("x"*8192)', 'a=[]\nwhile True:a.append(bytearray(20*1024*1024))'),
    'c': ('int main(void){volatile unsigned n=0;for(;;)n++;}', '#include <stdio.h>\nint main(void){for(;;)puts("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx");}', '#include <stdlib.h>\nint main(void){for(;;){volatile char*p=(volatile char*)malloc(20*1024*1024);if(!p)return 2;for(int i=0;i<20*1024*1024;i+=4096)p[i]=1;}}'),
    'cpp': ('int main(){volatile unsigned n=0;for(;;)n++;}', '#include <iostream>\nint main(){for(;;)std::cout<<"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"<<std::endl;}', '#include <vector>\nint main(){std::vector<char> a(400*1024*1024,1);return a[0];}'),
    'java': ('public class Main{public static void main(String[]a){while(true){}}}', 'public class Main{public static void main(String[]a){while(true)System.out.println("x".repeat(8192));}}', 'public class Main{public static void main(String[]a){byte[] x=new byte[256*1024*1024];System.out.println(x.length);}}'),
    'javascript': ('while(true){}', 'while(true)require("fs").writeSync(1,"x".repeat(8192))', 'let a=[];while(true)a.push(new Array(1e6).fill(1))'),
}


@pytest.fixture
def language_registry():
    from app.runner.toolchains.registry import ToolchainRegistry
    root = os.environ.get('CODETOP_TEST_TOOLCHAINS') or str(Path(__file__).resolve().parents[2] / 'runtime/toolchains-ci')
    registry = ToolchainRegistry(root)
    yield registry
    registry.close()


@pytest.mark.parametrize('language', SOURCES)
def test_five_languages_unicode_and_batch_compile_once(tmp_path, language_registry, language):
    from app.runner.native import NativeRunner
    state = language_registry.capability(language)
    if not state['available']:
        if os.environ.get('CODETOP_REQUIRE_LANGUAGES') == '1': pytest.fail(str(state))
        pytest.skip(str(state))
    phases = []
    runner = NativeRunner(tmp_path / '中文 空格', registry=language_registry)
    try:
        result = runner.execute(str(uuid4()), SOURCES[language], [
            dict(stdin='你好\n', expected_stdout='你好\n', comparison='exact'),
            dict(stdin='second\n', expected_stdout='second\n', comparison='exact')], language=language, on_phase=phases.append)
        assert [r['status'] for r in result['results']] == ['passed', 'passed'], result
        assert result['language'] == language
        assert result['runtime_version']
        assert sum(p['status'] == 'compiling' for p in phases) == int(language in ('c', 'cpp', 'java'))
    finally:
        runner.close()


@pytest.mark.parametrize('language', SOURCES)
@pytest.mark.parametrize('index,status', [(0,'time_limit'),(1,'output_limit'),(2,'memory_limit')])
def test_each_language_enforces_runtime_limits(tmp_path, language_registry, language, index, status):
    from app.runner.native import NativeRunner
    capability=language_registry.capability(language)
    if not capability['available']:
        if os.environ.get('CODETOP_REQUIRE_LANGUAGES')=='1': pytest.fail(str(capability))
        pytest.skip(str(capability))
    runner=NativeRunner(tmp_path,registry=language_registry)
    try:
        result=runner.execute(str(uuid4()),LIMIT_SOURCES[language][index],[{'stdin':''}],language=language)['results'][0]
        assert result['status']==status, result
        assert len((result['stdout']+result['stderr']).encode())<=65536
    finally:
        runner.close()
