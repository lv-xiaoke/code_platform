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
