"""Single-file execution contracts and portable starter programs."""
from dataclasses import asdict, dataclass
from .process_types import ProcessBudget


@dataclass(frozen=True)
class LanguageSpec:
    id: str
    label: str
    filename: str
    template: str
    compiled: bool
    run_budget: ProcessBudget


def budget(memory):
    return ProcessBudget(2, 3, memory, 65536)


SPECS = {
    'python': LanguageSpec('python', 'Python 3.12', 'main.py',
        '# 按行读取；交互提示请使用 flush=True\nimport sys\n\nfor line in sys.stdin:\n    print(line.rstrip("\\n"), flush=True)\n', False, budget(256)),
    'c': LanguageSpec('c', 'C17', 'main.c',
        '#include <stdio.h>\n\nint main(void) {\n    char line[4096];\n    /* 交互提示输出后调用 fflush(stdout); */\n    while (fgets(line, sizeof line, stdin)) {\n        fputs(line, stdout);\n        fflush(stdout);\n    }\n    return 0;\n}\n', True, budget(256)),
    'cpp': LanguageSpec('cpp', 'C++17', 'main.cpp',
        '#include <iostream>\n#include <string>\n\nint main() {\n    std::string line;\n    // std::endl 输出换行并刷新交互提示。\n    while (std::getline(std::cin, line)) {\n        std::cout << line << std::endl;\n    }\n}\n', True, budget(256)),
    'java': LanguageSpec('java', 'Java 21', 'Main.java',
        'import java.io.*;\n\n// 单文件入口必须为 Main，不写 package 声明。\npublic class Main {\n    public static void main(String[] args) throws Exception {\n        var reader = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));\n        String line;\n        while ((line = reader.readLine()) != null) {\n            System.out.println(line);\n            System.out.flush();\n        }\n    }\n}\n', True, budget(512)),
    'javascript': LanguageSpec('javascript', 'JavaScript · Node.js 24', 'main.js',
        '// CommonJS；readFileSync 会等待“结束输入”(EOF)后继续。\nconst fs = require("fs");\nconst input = fs.readFileSync(0, "utf8");\nprocess.stdout.write(input);\n', False, budget(512)),
}
COMPILE_BUDGET = ProcessBudget(30, 20, 1024, 262144)


def get_language(language):
    if language not in SPECS: raise ValueError('此语言可编辑，暂不支持执行')
    return SPECS[language]


def language_info(language):
    spec = get_language(language)
    return dict(label=spec.label, template=spec.template, compiled=spec.compiled,
        limits={**asdict(spec.run_budget), 'interactive_wall_seconds': 300,
                'heap_mb': 128 if language in ('java', 'javascript') else None,
                'compile': asdict(COMPILE_BUDGET) if spec.compiled else None})
