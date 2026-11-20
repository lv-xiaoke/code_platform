# Multi-language Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current session. Steps use checkbox (`- [ ]`) syntax for tracking. The user's existing native execution preference is preserved.

**Goal:** 在 Windows x64、macOS arm64 和 macOS x86_64 提供五种语言的完整程序练习，保留已有代码、笔记、历史和备份。

**Architecture:** 先将共享笔记和语言草稿分离，再将 Python 专用运行器拆成语言定义、工具链管理、程序准备、进程监督四层。批量样例和管道交互共用一次程序准备；前端按语言保存、查询能力和展示运行结果。工具链按需准备，应用和学习备份保持轻量。

**Tech Stack:** FastAPI、Pydantic、SQLAlchemy、Alembic、SQLite；Windows Job Object、macOS process group/rlimit；React、TypeScript、CodeMirror；PyInstaller、GitHub Actions。

**Spec:** [2026-11-20-multilanguage-design.md](../specs/2026-11-20-multilanguage-design.md)。规格和计划均已确认，已按当前会话方式执行。自动验收已完成，人工界面检查和已知次要问题见 [验收记录](../../multilanguage-acceptance.md)。

## Global Constraints

- 首版以单文件完整算法程序和标准输入/输出为约定：Python 3.12、C17、C++17、Java 21、Node.js 24。
- 不默认承诺 GNU 专有头文件或编译扩展在所有平台一致，不静默改写用户源码。
- Java 使用不带 package 声明的 Main 类和 main 入口；Node.js 使用普通 JavaScript CommonJS 脚本，不提供浏览器 DOM。
- 选择语言不会自动下载；用户点击“准备环境”才下载对应包。
- 不写 PATH、JAVA_HOME 或其他全局设置；启动使用经过校验的绝对路径。
- 编译期默认墙钟 30 秒、CPU 20 秒、总内存目标 1 GiB、诊断输出 256 KiB。
- 普通样例默认墙钟 2 秒、CPU 3 秒；交互程序墙钟 300 秒、CPU 3 秒，输入与输出各 64 KiB。
- Python、C、C++ 总内存目标 256 MiB；Java、JavaScript 总内存目标 512 MiB，Java 堆上限和 Node 堆上限初始各 128 MiB。
- 不能在线程化服务中使用 preexec_fn。调用编译器/运行时均使用参数数组，不拼接 shell 命令。
- 不批量删除文件/目录，不自动删除旧工具链、备份或发布。
- 本阶段不自动申请系统权限、安装 Mac 系统工具或发布新 Release。
- 前端测试及类型检查通过后执行 scripts/build.ps1 更新本地 release，从 Start-CodeTop.cmd 验证语言切换、环境准备、编译和运行。

## Review Focus

1. 旧数据包含空白代码及 Go/SQL 等语言：迁移保留“草稿存在”和原语言，不套用模板；由任务 1、2、8 测试约束。
2. 切换语言恰逢保存冲突、连续点击或迟到响应：留在原语言并保留输入，不将响应写到另一草稿；由任务 8 测试约束。
3. 编译失败、停止或父进程退出后后代持有管道：不启动程序，不无限等待，关页释放本次作业；由任务 3、5、7 测试约束。
4. 同一源码用不同语言运行或重试：不同语言不能复用运行 ID、终端、能力缓存或编译产物；由任务 5、6、7、8 测试约束。
5. 下载中断、错误哈希、恶意归档、并发准备和断网：已就绪环境仍可用，学习数据和全局环境不改变；由任务 4、9 测试约束。

---

## 执行约定与文件职责

在现有 `codex/multilanguage` 分支执行，起点为 main 的 `6510299`，设计提交 `5571ed8`。不切换或覆盖用户已有未提交改动。每个任务完成后记录验证结果和提交；阶段验证遇到失败先查根因，不用扩大跳过条件代替修复。

后端新增文件：

| 文件 | 单一职责 |
| --- | --- |
| `backend/migrations/versions/0004_multilanguage.py` | 草稿、偏好、运行元数据的无损迁移 |
| `backend/app/code_drafts.py` | 草稿和选择偏好的事务、revision 和历史恢复 |
| `backend/app/runner/languages.py` | 五种执行语言、文件名、模板、预算 |
| `backend/app/runner/process_types.py` | ProcessBudget 和 ProcessResult 类型 |
| `backend/app/runner/programs.py` | 写源码、编译一次、形成 PreparedProgram |
| `backend/app/runner/toolchains/manifest.py` | 固定清单解析和平台匹配 |
| `backend/app/runner/toolchains/archive.py` | 有界下载、哈希及安全解压 |
| `backend/app/runner/toolchains/registry.py` | 探测、准备状态、并发锁和原子发布 |
| `backend/app/runner/toolchains/__init__.py` | 包声明 |
| `backend/app/runner/toolchain_routes.py` | 环境能力和准备/停止接口 |

前端新增 `CodeEditor.tsx`、`codeDraftState.ts`、`useCodeDraft.ts`、`languageTypes.ts`、`LanguageEnvironment.tsx`；分别负责编辑器、可测试的切换状态机、草稿保存、能力类型、环境准备面板。保留 `useNote.ts` 负责共享 Markdown，避免将两套 revision 再次合并。

发布新增 `packaging/toolchains.json`、`scripts/lock_toolchains.py`、`scripts/prepare_toolchains.py`、`scripts/multilanguage_smoke.py` 和 `docs/multilanguage-acceptance.md`。清单是发布输入，下载脚本不在运行时解析 latest。

Windows 命令均从仓库根目录运行：

```powershell
& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests -q --tb=short
& tools/node_modules/node/bin/node.exe --test frontend/tests/*.test.mjs
& tools/node_modules/node/bin/node.exe frontend/node_modules/typescript/bin/tsc -b frontend
```

TestClient 若受当前沙箱网络管道限制，使用已授权的受控沙箱外命令运行，不修改测试来绕过业务校验。沿用 `conftest.py` 保留临时目录的做法。

## Task 1: schema 0004 与旧备份无损升级

**Files:**
- Create: `backend/migrations/versions/0004_multilanguage.py`
- Modify: `backend/app/models.py`, `backend/app/db.py`, `backend/app/backups.py`
- Test: `backend/tests/test_multilanguage_migration.py`, `backend/tests/test_backups.py`, `backend/tests/test_cross_platform_backup.py`

**Interfaces:**
- Consumes: `Database(data_dir)`, `Database.migrate()`, `create_backup(db, reason='manual')`, `inspect_database(path)`。
- Produces: `m.code_drafts`，主键 `(problem_id, language)`，列 `code_text/revision/created_at/updated_at`；`m.problem_preferences`，主键 `problem_id`，列 `language/revision/updated_at`。
- Produces: `m.runs` 增加 `language`（旧记录默认 python）、`runtime_version`、`toolchain_id`、`compile_json`、`limits_json`；已有 `results_json` 不改格式。
- Produces: `SCHEMA_VERSION='0004'`，支持恢复 `0001/0002/0003/0004`；备份按实际 schema 统计表。

- [x] **Step 1: 写迁移失败测试。** 使用 Alembic 显式建 0003 数据库，写入 Python 非空、Java 空白、SQL 原样代码和旧运行/历史后执行 `db.migrate()`。测试直接查询 SQLite，验证旧字段逐字相同、历史不增、运行语言为 python，并打开 before-migration ZIP 验证其中仍为 0003。测试的 Alembic 设置沿用 `Database.migrate`：

```python
from alembic import command
from alembic.config import Config
from app.db import Database, ROOT
from app.backups import inspect_database
import sqlite3
import pytest

def test_fresh_schema_records_draft_counts(tmp_path):
    db = Database(tmp_path)
    db.migrate()
    counts, _ = inspect_database(db.path)
    assert counts['code_drafts'] == 0
    assert counts['problem_preferences'] == 0

def create_legacy_database(path):
    cfg = Config()
    cfg.set_main_option('script_location', str(ROOT / 'backend/migrations'))
    cfg.set_main_option('sqlalchemy.url', 'sqlite:///' + path.as_posix())
    command.upgrade(cfg, '0003')

@pytest.mark.parametrize('language,code', [('python', 'print(1)'), ('java', ''), ('sql', 'SELECT 1;')])
def test_legacy_draft_keeps_language_and_empty_value(tmp_path, language, code):
    path = tmp_path / 'study.sqlite3'
    create_legacy_database(path)
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO problems(id,kind,created_at) VALUES('p','custom','2026-11-20')")
        conn.execute('INSERT INTO notes VALUES(?,?,?,?,?,?)',
            ('p', '共享笔记', code, language, 7, '2026-11-20'))
    db = Database(tmp_path)
    db.migrate()
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT language,code_text,revision FROM code_drafts').fetchone() == (language, code, 1)
        assert conn.execute('SELECT body_md FROM notes').fetchone()[0] == '共享笔记'
        assert conn.execute('SELECT count(*) FROM code_history').fetchone()[0] == 0
    assert list((tmp_path / 'backups').glob('*before-migration*.zip'))
```

为旧运行和旧历史补充同样的参数化数据验证；所有记录先插入有效的 problems 父记录，不伪造缺失外键的数据库。

- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_multilanguage_migration.py -q`，预期缺少 `code_drafts`。
- [x] **Step 3: 实现迁移及分版本备份统计。** 新表外键指向 problems；从所有 notes 迁入，包括空字符串，草稿 revision 从 1 开始；偏好沿用旧 language。运行旧值不丢弃，新元数据为空；禁止 downgrade 删除。核心 SQL：

```sql
INSERT INTO code_drafts
    (problem_id, language, code_text, revision, created_at, updated_at)
SELECT problem_id, language, code_text, 1, updated_at, updated_at FROM notes;
INSERT INTO problem_preferences (problem_id, language, revision, updated_at)
SELECT problem_id, language, 1, updated_at FROM notes;
```

`inspect_database` 的运行/样例统计覆盖 0002–0004，历史覆盖 0003–0004，草稿与偏好仅 0004。不要给旧快照统计不存在的表。未知新版本错误文案包含“请升级应用”。
- [x] **Step 4: 跑绿。** 执行本任务三个测试文件；增加 0001–0003 恢复后升级、0004 新备份往返和排除 toolchains/Key 的断言。
- [x] **Step 5: 提交。** 显式暂存本任务文件，`git commit -m "feat: migrate language drafts and preserve legacy backups"`。

## Task 2: 独立草稿、笔记和语言偏好 API

**Files:**
- Create: `backend/app/code_drafts.py`, `backend/tests/test_code_drafts.py`
- Modify: `backend/app/schemas.py`, `backend/app/learning.py`, `backend/app/main.py`, `backend/app/catalog.py`, `backend/tests/test_code_history.py`, `backend/tests/test_learning.py`

**Interfaces:**
- Consumes: 任务 1 的表，`Database.write()` 的 BEGIN IMMEDIATE。
- Produces: `get_draft(db, pid, language) -> dict`；未存返回 `{exists:false, revision:0, code_text:'', language}`，已存空白返回 exists=true。
- Produces: `put_draft(db, pid, language, payload, now) -> dict`，payload 为 `DraftWrite(revision:int, code_text:str)`；revision 冲突返回 409 和 current。
- Produces: `put_body(db, pid, payload, now) -> dict`，payload 为 `NoteBodyWrite(revision:int, body_md:str)`。
- Produces: GET/PUT `/api/v1/problems/{pid}/code/drafts/{language}`；PUT `.../note/body`；GET/PUT `.../code/preference`，偏好写入也带 revision。
- Produces: 历史查询可选 `language`；rewrite 请求必须有 `language/revision`，恢复还带 `history_id`，revision 指向目标语言草稿。响应包含目标 draft 与 preference。

- [x] **Step 1: 写 API 行为测试。**

```python
def test_language_drafts_are_independent_and_empty_is_saved(loaded):
    c, _, _, pid = loaded
    url = f'/api/v1/problems/{pid}/code/drafts'
    assert c.get(url + '/java').json()['exists'] is False
    py = c.put(url + '/python', json={'revision': 0, 'code_text': 'print(1)'})
    assert py.status_code == 200
    java = c.put(url + '/java', json={'revision': 0, 'code_text': ''})
    assert java.status_code == 200
    assert java.json()['exists'] is True
    assert c.get(url + '/python').json()['code_text'] == 'print(1)'
    stale = c.put(url + '/python', json={'revision': 0, 'code_text': 'lost'})
    assert stale.status_code == 409
    assert stale.json()['detail']['current']['code_text'] == 'print(1)'
```

另测旧合并 note 写入返回 409 且不覆盖新草稿；正文与草稿并发写不互相冲突；恢复 Java 历史只归档 Java 当前代码，Python 保持原值；并发 rewrite 仅成功一次。语言 ID 限制为 1–32 个小写字母、数字、下划线和连字符，保留旧非执行语言。
- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_code_drafts.py -q`，预期新接口 404。
- [x] **Step 3: 实现独立事务。** 先确认题目存在，再在同一 write 事务读取 revision、比较并更新；首次写入 revision=1。正文写只更新 notes.body_md/revision。旧详情 note 的 code_text/language 由偏好和草稿投影，不能回写旧列。冲突结构沿用现有客户端恢复约定：

```python
from fastapi import HTTPException

def require_revision(expected, current):
    if expected != current['revision']:
        raise HTTPException(409, detail={
            'message': '内容已更新，请保留输入并刷新后重试',
            'current': current,
        })
```

修改既有历史测试走新接口；旧合并接口测试保留并改为明确验证拒绝，不能删掉历史并发及崩溃回滚测试。
- [x] **Step 4: 跑绿。** 本任务三个测试文件通过；验证修改代码不改变 Markdown revision，历史载入失败不更新偏好。
- [x] **Step 5: 提交。** `git commit -m "feat: separate code drafts from shared notes"`（先显式暂存本任务文件）。

## Task 3: 通用受管进程与分阶段预算

**Files:**
- Create: `backend/app/runner/process_types.py`, `backend/tests/test_process_supervisor.py`
- Modify: `backend/app/runner/native_process.py`, `backend/app/runner/windows_job.py`, `backend/app/runner/macos_process.py`, `backend/runner/native_bootstrap.py`, `backend/tests/test_native_runner.py`, `backend/tests/test_macos_runner.py`

**Interfaces:**
- Produces: `ProcessBudget(wall_seconds:float, cpu_seconds:float, memory_mb:int, output_bytes:int, max_processes:int=32)`。
- Produces: `execute_command(argv, cwd, env, *, budget, stdin=None, inputs=None, stop_event=None, on_output=None) -> ProcessResult`，结果维持 `status/stdout/stderr/exit_code` 及现有耗时字段。
- Consumes/Preserves: `execute_process(python, script, *, stdin=None, inputs=None, stop_event=None, on_output=None, wall_seconds=2, cpu_seconds=3)` 保留 Python 兼容包装。
- Produces: 两平台进程构造均接受显式 `cpu_seconds`；Mac 通过内置 Python 引导 `--cpu-seconds N -- argv...`，引导设置 rlimit 后 `os.execve(argv[0], argv, env)`。

- [x] **Step 1: 写任意 argv、诊断上限与停止测试。**

```python
import sys
import threading
from app.runner.native_process import execute_command
from app.runner.process_types import ProcessBudget

def test_command_has_its_own_argv_and_output_budget(tmp_path):
    result = execute_command(
        [sys.executable, '-I', '-S', '-B', '-c', 'print("x" * 100000)'],
        tmp_path, {}, budget=ProcessBudget(5, 3, 256, 1024))
    assert result['status'] == 'output_limit'
    assert len((result['stdout'] + result['stderr']).encode()) <= 1024

def test_pre_cancelled_command_never_runs(tmp_path):
    stop = threading.Event()
    stop.set()
    result = execute_command([sys.executable, '-c', 'raise Exception("ran")'],
        tmp_path, {}, budget=ProcessBudget(5, 3, 256, 1024), stop_event=stop)
    assert result['status'] == 'stopped'
```

另测 stdout/stderr 合并计数按字节截断、多字节末尾、未发 EOF、快速退出、子进程继承管道、编译器样式父子进程、CPU/墙钟/内存独立超限。Windows 测试传入系统白名单环境；Mac 测试核对 exec 后 argv 不附带 Python flags。
- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_process_supervisor.py -q`，预期缺少 execute_command。
- [x] **Step 3: 抽取通用传输。** 保留现有有界事件队列、非阻塞 Mac 管道、停止与退出排空期限；将 LIMIT 和固定 argv 换为参数。预算定义：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessBudget:
    wall_seconds: float
    cpu_seconds: float
    memory_mb: int
    output_bytes: int
    max_processes: int = 32
```

Windows 继续 suspended spawn→Job 指派→resume，按预算设置组 CPU/内存；Mac 引导用可信内置 Python 绝对路径，设置 CPU soft=ceil(budget)、hard=soft+1、FSIZE 和 CORE=0 后 exec。组 RSS 采样和 PID 身份防复用保留；编译期 FSIZE 允许受限产物，不能沿用会截断链接产物的 1 MiB。
- [x] **Step 4: 跑绿。** 新测试和既有 native/platform/Mac 测试；必须保留 Python SIGXCPU、EOF、输出伪造协议等回归。
- [x] **Step 5: 提交。** `git commit -m "refactor: supervise arbitrary commands with explicit budgets"`。

## Task 4: 可核验、可重试的按需工具链

**Files:**
- Create: `backend/app/runner/toolchains/{__init__.py,manifest.py,archive.py,registry.py}`, `backend/app/runner/toolchain_routes.py`, `packaging/toolchains.json`, `scripts/lock_toolchains.py`, `scripts/prepare_toolchains.py`, `backend/tests/test_toolchains.py`
- Modify: `backend/app/paths.py`, `backend/app/main.py`, `backend/app/runner/routes.py`

**Interfaces:**
- Produces: `ToolchainRegistry(root, manifest_path)`；`capability(language)->dict`、`prepare(language)->dict`、`cancel(language)->dict`、`resolve(language)->ResolvedToolchain`、`close()`。
- Produces: `ResolvedToolchain(id:str, version:str, executables:dict[str,Path], sdk:Path|None)`，必需入口 Python=python、C=cc、C++=cxx、Java=javac/java、JavaScript=node。
- Produces: GET `/api/v1/runner/languages`；POST `/runner/languages/{language}/prepare`、`/cancel`。准备状态为 unprepared/downloading/verifying/extracting/ready/failed/needs_system_tool；同工具链准备返回相同 job_id。
- Produces: `CODETOP_TOOLCHAINS_DIR` 显式测试覆盖；默认按当前用户应用路径定位，独立于 data_dir。

- [x] **Step 1: 写下载和状态失败测试。** 内存 zip/tar 测试中放入 `../escape`、绝对路径、Windows 盘符、符号/硬链接和正常文件。测试下载器使用本地注入流，不能依赖公共网络。核心状态断言：

```python
from app.runner.toolchains.registry import ToolchainRegistry

def test_selection_does_not_start_download(tmp_path):
    registry = ToolchainRegistry(tmp_path, 'packaging/toolchains.json')
    status = registry.capability('javascript')
    assert status['state'] == 'unprepared'
    assert list(tmp_path.iterdir()) == []
    registry.close()
```

补测同 LLVM 清单 C/C++ 共用锁，重复 prepare 同 job_id、取消、错误哈希/超大内容、断点失败不触碰 ready、离线重启 probe；Mac 无 CLT 时不调用 `/usr/bin/clang` 占位程序。
- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_toolchains.py -q`，预期模块不存在。
- [x] **Step 3: 锁清单后实现准备流程。** 开发期 `lock_toolchains.py --output runtime/toolchains-candidate.json` 查询官方 LLVM-MinGW、Temurin 21、Node 24 资产及官方校验信息，产出固定候选；核对来源、版本、架构、许可证并下载核验，再将确定值写入 `packaging/toolchains.json`。运行时清单字段必须全部存在且 SHA 是 64 位十六进制；禁止 latest URL、动态版本和空哈希。仅收录 Windows x64 与两种 Mac 架构对应资产，Mac C/C++ 标记 system-clt。下载包上限 1 GiB，解压总量上限 4 GiB，成员数上限 100000。拒绝越界及硬链接；合法发行包符号链接须解析并证明目标在新 staging 根内，先落普通文件再创建内部链接，Windows zip 不创建链接。

```python
from pathlib import PurePosixPath

def checked_member(name):
    normalized = name.replace('\\', '/')
    path = PurePosixPath(normalized)
    if path.is_absolute() or '..' in path.parts or ':' in normalized:
        raise ValueError('工具链归档包含越界路径')
    return path
```

每次新建 UUID staging，下载哈希通过→解压→入口/架构/版本及编译运行 smoke 通过→写 receipt→同文件系统原子 rename 到版本目录→原子更新 ready 指针。失败保留 staging 和诊断，不批量清理。旧版本 ready 指针最后才更新；恢复/升级不删目录。

Mac 用 `/usr/bin/xcode-select -p` 及已选目录内实际工具/SDK 探测，必要时用绝对 xcrun 查询 SDK；缺失返回 needs_system_tool 和 Apple 官方文档，不执行 `xcode-select --install`。任何语言就绪不能依赖用户 PATH。
- [x] **Step 4: 跑绿。** 工具链测试通过；手动运行锁定脚本核验清单，保存 URL/版本/SHA 的核对记录（不含本机私密路径）。
- [x] **Step 5: 提交。** `git commit -m "feat: prepare pinned language toolchains on demand"`。

## Task 5: 五语言定义与一次编译的程序准备

**Files:**
- Create: `backend/app/runner/languages.py`, `backend/app/runner/programs.py`, `backend/tests/test_program_preparation.py`, `backend/tests/test_multilanguage_native.py`
- Modify: `backend/app/runner/native.py`, `backend/app/runner/factory.py`

**Interfaces:**
- Consumes: `ProcessBudget`、`execute_command`、`ToolchainRegistry.resolve`。
- Produces: `LanguageSpec(id, filename, template, compiled, run_budget)`、`get_language(language)->LanguageSpec`。
- Produces: `PreparedProgram(language, argv, cwd, env, runtime_version, toolchain_id, compile_result, limits)`；`ProgramPreparer(root, registry).prepare(job_id, language, source, stop_event, on_phase=None)->PreparedProgram`。
- Produces: `PreparationError(status, diagnostics, metadata)`；编译失败不可返回可运行 argv。
- Produces: `NativeRunner.execute(job_id, source_code, cases, language='python')`，返回 results、language、runtime_version、toolchain_id、compile、limits，Python 附带 python_version。

- [x] **Step 1: 写编译参数与编译一次测试。** 给 preparer 注入记录调用的 supervisor 和固定 ResolvedToolchain，检验两组样例只有一条编译调用；编译返回非零后零条运行调用。实际五语言 smoke 用下面表中的源码参数化：

```python
SOURCES = {
 'python': 'print(input())',
 'c': '#include <stdio.h>\nint main(void){char s[256];if(fgets(s,sizeof s,stdin))fputs(s,stdout);return 0;}',
 'cpp': '#include <iostream>\n#include <string>\nint main(){std::string s;std::getline(std::cin,s);std::cout<<s<<"\\n";}',
 'java': 'import java.io.*; public class Main {public static void main(String[] a)throws Exception{System.out.println(new BufferedReader(new InputStreamReader(System.in,"UTF-8")).readLine());}}',
 'javascript': 'process.stdout.write(require("fs").readFileSync(0,"utf8"))',
}
```

另测合法嵌套 Java 类、空白和中文路径、C17/C++17 标准头文件、Java 主类错误、JS 语法错误、Python 原样语法状态。两个 job 使用相同源码仍产生不同目录。
- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_program_preparation.py -q`，预期无 ProgramPreparer。
- [x] **Step 3: 实现语言参数规则。** 源码文件名固定，作业 ID 必须 UUID，新目录必须不存在；不从源码猜语言。编译参数以绝对入口组装：

```python
compile_c = [str(cc), '-std=c17', '-O2', 'main.c', '-o', str(output)]
compile_cpp = [str(cxx), '-std=c++17', '-O2', 'main.cpp', '-o', str(output)]
compile_java = [str(javac), '-J-Xmx128m', '-encoding', 'UTF-8', '-d', '.', 'Main.java']
run_java = [str(java), '-Xmx128m', '-Dfile.encoding=UTF-8', '-cp', '.', 'Main']
run_js = [str(node), '--max-old-space-size=128', 'main.js']
```

Mac 编译显式使用已探测 SDK 的 `-isysroot` 参数；Windows C/C++ 使用完整 LLVM-MinGW root 的绝对入口。每阶段生成独立白名单 env，所需相邻工具目录仅放入此子进程 PATH。验证产物 main(.exe)/Main.class 存在且处于本作业目录，拒绝链接产物逃逸。编译 wall/cpu 超限映射 compile_time_limit，非零映射 compile_error，保留256KiB诊断；内存、输出、停止仍保留对应原因和 compile 阶段。

Python run argv 保持 `-I -S -B -u -X utf8`；比较器只读运行 stdout。模板包含 Java Main、Node EOF、C/C++ flush 提示；参考包仍只标注 Python，不更改1153题面或批量生成解答。
- [x] **Step 4: 跑绿。** 参数和编译一次单测；准备好本机工具链后跑真实五语言测试。缺工具链的本机用例明确 skip 原因；CI 必需五语言就绪时任何 skip 都算验收失败。
- [x] **Step 5: 提交。** `git commit -m "feat: compile and run five single-file languages"`。

## Task 6: 运行 API、元数据及语言幂等性

**Files:**
- Modify: `backend/app/runner/schemas.py`, `backend/app/runner/service.py`, `backend/app/runner/routes.py`, `backend/app/runner/factory.py`, `backend/app/runner/docker.py`, `backend/app/ai/service.py`
- Test: `backend/tests/test_multilanguage_api.py`, `backend/tests/test_acm_api.py`, `backend/tests/test_ai.py`

**Interfaces:**
- Consumes: `NativeRunner.execute(..., language='python')`，任务 1 运行列和任务 4 能力。
- Produces: RunWrite.language 五种 Literal，默认 python；未知或非执行语言 422。环境未准备 409，detail 包含 language/state/action，且不占队列或写运行记录。
- Produces: run_dict 显示实际 language/runtime_version/toolchain_id/compile/limits；历史 GET 可选 language；省略语言保留 Python 客户端语义。
- Preserves: GET `/runner/health` 的 Python 字段；GET `/runner/languages` 才是前端按语言能力入口。Docker 只有 python 可用。

- [x] **Step 1: 写请求和历史断言。**

```python
from app.runner.schemas import RunWrite

def test_retry_payload_includes_language():
    base = dict(request_id='same', source_code='x', mode='custom', cases=[{'stdin': ''}])
    py = RunWrite(**base)
    js = RunWrite(**base, language='javascript')
    assert py.language == 'python'
    assert py.model_dump(exclude={'request_id'}) != js.model_dump(exclude={'request_id'})
```

真实 submit 测试复用同 request_id 换语言返回409，不得返回旧 job；新 request_id 正常创建另一作业。环境未准备不写 code_runs；Docker Java 返回明确不可用。AI 输入断言同时包含实际语言、编译错误和版本，不包含 Key、工具链绝对用户路径。
- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_multilanguage_api.py -q`。
- [x] **Step 3: 串接服务。** 规范 hash 包含 problem_id、language、source_code、mode、解析后的 cases（含 suite revision）；禁止同 request_id 在不同题复用。提交前校验 consent/能力，再取队列槽；异常路径 release 仍执行。持久化准备/编译/运行阶段，任务结束保存诊断和预算；启动时将全部未完成阶段标 interrupted。AI 从存储元数据读取，编译诊断与答案输出分开。

```python
import hashlib
import json

def execution_hash(problem_id, language, source_code, mode, cases, suite_revision=None):
    value = dict(problem_id=problem_id, language=language, source_code=source_code,
                 mode=mode, cases=cases, suite_revision=suite_revision)
    return hashlib.sha256(json.dumps(value, ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
```

- [x] **Step 4: 跑绿。** 本任务测试和全部 runner/API/AI 回归；确认旧运行仍显示 Python，非 Python 不带误导的 python_version。
- [x] **Step 5: 提交。** `git commit -m "feat: persist language-aware runs and compile diagnostics"`。

## Task 7: 多语言交互、编译停止与 EOF

**Files:**
- Modify: `backend/app/runner/terminal.py`, `backend/app/runner/terminal_native.py`, `backend/app/runner/terminal_docker.py`, `backend/app/runner/schemas.py`
- Test: `backend/tests/test_terminal_api.py`, `backend/tests/test_multilanguage_terminal.py`

**Interfaces:**
- Consumes: `ProgramPreparer.prepare`，任务 6 execution_hash。
- Produces: `TerminalStart.language='python'`；`TerminalSession(..., language='python')` 保持现有三位置参数兼容。
- Produces: snapshot 与 phase/ready 事件含 language/runtime_version/toolchain_id/compile/limits；ready 表示可读写程序已准备完成。compile_error 作为终态，不等待 stdin。
- Preserves: stop_request(request_id) 对丢失响应请求仍有效，输入 request_id 去重和 EOF 只发送一次。

- [x] **Step 1: 写语言终端和取消测试。**

```python
from app.runner.schemas import TerminalStart

def test_terminal_language_defaults_and_explicit_language():
    assert TerminalStart(request_id='a', source_code='x').language == 'python'
    assert TerminalStart(request_id='b', source_code='x', language='java').language == 'java'
```

真实进程测五语言输入→输出→EOF；Java/C++ 的模板提示强制 flush。注入慢编译 command 后 stop_request，断言 stop_event 终止编译、没有 run argv、会话槽释放；close/service shutdown 同样断言。迟到输出只属于原 session ID。
- [x] **Step 2: 跑红。** `& backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_multilanguage_terminal.py -q`。
- [x] **Step 3: 共用 preparer 和 supervisor。** 从 session 取 language，用同一个 stop_event 贯穿 prepare/run；编译输出进入 compile diagnostics，不能作为 terminal stdout。交互 run budget wall=300，其余按语言；队列在 preparing/compiling 也有明确状态，ready 前不误发输入。

```python
program = self.preparer.prepare(session.id, session.language,
    session.source_code, session.stop_event, on_phase=session.emit)
session.emit({'type': 'ready', 'language': program.language,
              'runtime_version': program.runtime_version,
              'toolchain_id': program.toolchain_id})
```

捕获 PreparationError 并持久化终态和编译元数据；finally 移除 active event。旧 Python version 仅在 Python 会话补齐。
- [x] **Step 4: 跑绿。** terminal API、native、Docker 原有回归及多语言真机用例；检查全部后台线程在停止期限内结束。
- [x] **Step 5: 提交。** `git commit -m "feat: support multilingual interactive execution and cancellation"`。

## Task 8: 独立草稿界面、环境面板和实际语言展示

**Files:**
- Create: `frontend/src/local/{CodeEditor.tsx,codeDraftState.ts,useCodeDraft.ts,languageTypes.ts,LanguageEnvironment.tsx}`, `frontend/tests/{code-drafts.test.mjs,multilanguage.test.mjs}`
- Modify: `frontend/src/local/{useNote.ts,api.ts,CodePractice.tsx,PracticeDialog.tsx,NotesDrawer.tsx,AcmWorkspace.tsx,runRequest.ts,useTerminal.ts,acmTypes.ts,terminalTypes.ts,TerminalPanel.tsx,RunResults.tsx,runnerEnvironment.ts,AiTutor.tsx,aiTypes.ts,acm.css}`, `frontend/tests/{acm-requests.test.mjs,terminal.test.mjs,code-history.test.mjs,runner-environment.test.mjs}`, `scripts/verify.ps1`

**Interfaces:**
- Consumes: 任务 2 草稿/正文/偏好 API，任务 4 能力，任务 6–7 运行字段。
- Produces: `switchDraft(language, deps):Promise<boolean>`，deps 含 `stopActive():Promise<void>`、`flush():Promise<void>`、`load(language):Promise<CodeDraft>`、`commit(draft):void`；失败返回 false、不 commit，错误交给 UI 保留展示。
- Produces: `CodeDraft={problem_id,language,code_text,revision,exists}`；`CodeEditor` 参数 `language/value/onChange/readOnly/ariaLabel`。
- Produces: `prepareRun(source,mode,suite,language='python')`、`prepareQuickRun(source,stdin='',language='python')`；terminal.start(source,language='python')。签名和实际 submission 都带 language。

- [x] **Step 1: 写用户行为测试。**

```javascript
import {test} from 'node:test'
import assert from 'node:assert/strict'
import {prepareQuickRun} from '../src/local/runRequest.ts'
import {switchDraft} from '../src/local/codeDraftState.ts'

test('same source in two languages has different retry identities',()=>{
  const py=prepareQuickRun('x','','python')
  const js=prepareQuickRun('x','','javascript')
  assert.notEqual(py.signature,js.signature)
  assert.equal(js.submission.language,'javascript')
})
test('failed save keeps the current draft',async()=>{
  const events=[]
  const ok=await switchDraft('java',{
    stopActive:async()=>{events.push('stop')},
    flush:async()=>{events.push('flush');throw Error('conflict')},
    load:async()=>{throw Error('must not load')},
    commit:()=>events.push('commit'),
  })
  assert.equal(ok,false)
  assert.deepEqual(events,['stop','flush'])
})
```

补充两次切换、旧请求迟到、切换中编辑、刷新后已存空白不套模板、未存草稿套正确语言模板、保存冲突可导出、历史跨语言恢复失败等状态机测试；测试必须执行状态机，不能只扫描组件源码。
- [x] **Step 2: 跑红。** `& tools/node_modules/node/bin/node.exe --test frontend/tests/code-drafts.test.mjs frontend/tests/multilanguage.test.mjs`。
- [x] **Step 3: 实现状态机与 UI。** 以 problem_id+language 为草稿 query key、language 为能力 key。每次切换先设操作锁、捕获 generation，再 stop→flush→load→保存 preference→commit；过期 generation 不写 state，失败原 code/revision 不动，finally 解锁。关闭面板同样等待停止和保存，不吞掉冲突。

```typescript
export function initialCode(draft:CodeDraft, template:string):string {
  return draft.exists ? draft.code_text : template
}
```

CodeMirror 使用现有 lang-python/cpp/java/javascript，C 复用 cpp 语法高亮；其他历史语言继续选项和编辑。用 CodeEditor 替换当前练习/历史边界的 PythonEditor，保留 ariaLabel 和主题。NotesDrawer 的正文走 note/body，不混合代码保存。

环境面板展示版本、阶段、重试/停止/重新检查；点击准备才 POST，选择只 GET。未准备时运行入口指向环境面板；Docker 非 Python 明确提示本机模式。全局 Python consent 保留但说明为本机代码执行，不假装新增语言是额外沙箱。

去除硬编码非 Python 禁用；编译诊断独立区域，运行记录及终端显示实际语言/版本；Python 参考代码明确标记。AI 上下文取当前草稿或选中历史的语言。现有 verify.ps1 改为收录所有 frontend/tests/*.test.mjs，避免新增测试漏跑。
- [x] **Step 4: 跑绿。** 全部前端 Node 测试和 TypeScript 构建检查。记录浏览器真实交互验收；若当前 CUA 仍不可用，明确记为未执行，不以源码扫描声称 UI 已通过。
- [x] **Step 5: 提交。** `git commit -m "feat: add per-language editors drafts and environment controls"`。

## Task 9: 打包、三平台验证与用户文档

**Files:**
- Create: `scripts/multilanguage_smoke.py`, `docs/multilanguage-acceptance.md`, `backend/tests/test_multilanguage_distribution.py`
- Modify: `scripts/{desktop_assets.py,build_desktop.py,build_macos.py,package_release.py,backup_exchange.py}`, `packaging/{desktop.spec,macos.spec}`, `.github/workflows/macos.yml`, `README.md`, `docs/{deployment.md,user-guide.md,macos-validation.md}`

**Interfaces:**
- Consumes: 固定 toolchains.json，任务 1 新备份和任务 4 prepare CLI。
- Produces: `prepare_toolchains.py --languages python,c,cpp,java,javascript --root PATH --require-ready`，无交互准备到测试专用根，Mac CLT 不存在立即明确失败；`multilanguage_smoke.py --base-url URL --require-all` 通过 HTTP 验证五语言运行、编译错误、终端和版本。
- Produces: 三平台 CI 报告含 OS/arch、实际版本、工具链 SHA、五语言结果、0004 跨平台备份内容比较；真实缺席项必须标未执行。

- [x] **Step 1: 写分发失败测试。**

```python
import importlib.util
import json
from pathlib import Path

def test_distribution_has_pinned_toolchain_manifest():
    manifest = json.loads(Path('packaging/toolchains.json').read_text(encoding='utf-8'))
    assert manifest['schema'] == 1
    assert manifest['artifacts']
    for item in manifest['artifacts']:
        assert 'latest' not in item['url'].lower()
        assert len(item['sha256']) == 64
        assert item['license']

def test_packaged_assets_include_manifest(tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('multilanguage_assets', root / 'scripts/desktop_assets.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.copy_assets(root, tmp_path / 'assets')
    assert (tmp_path / 'assets/packaging/toolchains.json').is_file()
    assert (tmp_path / 'assets/backend/migrations/versions/0004_multilanguage.py').is_file()
    assert not (tmp_path / 'assets/toolchains').exists()
```

测试实际 desktop_assets 输出包含清单、新迁移和引导，源码发布包也包含；不包含工具链缓存、运行目录和学习数据。Mac bundle probe 通过只读应用路径读取清单、写用户工具链根，不能给已签资源新增 pyc。
- [x] **Step 2: 跑红。** 分发测试对尚未收录清单的 assets 应失败；失败必须来自实际输出缺项。
- [x] **Step 3: 接入打包和 CI。** 复用现有 Windows、Mac arm64、Mac Intel 矩阵，push 增加 codex/multilanguage，PR 检查保留。每平台显式准备工具链后执行五语言集成，SDK 缺失另用注入探测测试；使用缓存只能按清单 SHA+平台作 key，命中后仍校验 receipt/入口。离线验收在准备完成后阻断下载依赖，执行五语言。备份交换 fixture 包含5种草稿、已存空白、旧非执行语言、偏好、历史及多语言运行；比较逐项内容而非只比较总数。

```powershell
& backend/.venv/Scripts/python.exe scripts/prepare_toolchains.py --languages python,c,cpp,java,javascript --root runtime/toolchains-ci --require-ready
& scripts/verify.ps1
& scripts/build.ps1
```

Mac 使用 CI 自带 Python 环境对应命令，再实际构建 app/DMG 跑 packaged smoke；不将源码测试替代已打包应用测试。Windows 从 Start-CodeTop.cmd 启动本地新 release，验证服务健康、当前 HTML/静态资源版本、五语言执行及关页退出。用户学习数据不用于破坏性迁移测试，验收数据用显式独立目录。

README 增加支持矩阵、首次准备联网/就绪离线、Mac CLT、C++ 标准头文件、Java Main、Node EOF、管道 flush、各语言资源预算和编辑-only语言说明；部署/用户指南补工具链目录、失败重试、备份不含编译器。现有公开 macOS 测试包仍只支持旧 Python 功能，文档不能把尚未发布的多语言能力写成已发布下载；用“源码分支/待发布”清楚区分。
- [x] **Step 4: 跑绿并记录证据。** `scripts/verify.ps1` 全通过→`scripts/build.ps1` 成功→普通启动入口验收→三平台 CI 与实际 app smoke。无 Mac 实机/网络授权时记录实际阻塞，不声称完成该平台验收。完成后依 requesting-code-review 做一次完整差异审阅，处理发现，再按 verification-before-completion 记录最终检查。当前任务不自动发布 Release 或合并 main。
- [x] **Step 5: 提交。** `git commit -m "build: validate and document multilingual desktop packages"`。

## 规格覆盖与交付记录

| 规格主题 | 实施任务 |
| --- | --- |
| 五语言单文件、标准、模板及旧语言可编辑 | 5、8 |
| 固定工具链、准备状态、离线、CLT、全局环境不变 | 4、8、9 |
| 分阶段资源限制、编译一次、取消、子进程和 EOF | 3、5、7 |
| 草稿存在性、共享正文、revision、偏好、历史恢复 | 1、2、8 |
| 语言请求签名、能力、Docker 边界、版本、AI | 6、7、8 |
| 旧数据和旧备份升级、新备份三平台交换 | 1、9 |
| 安装包资源、原入口、文档和验证证据 | 9 |

实施日志在本计划复选框和 `docs/multilanguage-acceptance.md` 记录；测试工件留在 runtime，不提交真实用户数据或密钥。最终交付列出已完成、验证证据、仍缺的真机验收；不得将未执行项写成通过。


## 执行结果与实施裁定

- 最终产品测试提交 `8f25ba2`；CI [44676286322](https://github.com/lv-xiaoke/code_platform/actions/runs/44676286322) 的 6 个任务全部通过。源码启动入口、Windows 冻结应用、Mac 两种架构实际应用和三平台备份互换已完成自动验证。
- 保存/切换状态由 `DraftController` 集中管理，`useCodeDraft` 订阅状态；以真实 React/CodeMirror DOM 测试验证撤销和失败终端，不以源码扫描代替行为验证。
- 为保留 0003 接口接受的旧语言名，存储键保留最长 50 字符的原始字符串，新增 query 草稿接口和保存语言枚举；执行层仍严格限制五个规范语言 ID。此项替代任务 2 的 lowercase32 假设。
- 普通源码入口默认本机执行，显式 Docker 模式保留；启动器检测旧 schema 服务并提示关闭旧窗口，不自动中断用户服务。
- 独立审查的 7 项重要问题已修复并通过回归；两项次要问题和完整浏览器/Finder 等未执行人工项见验收记录。本计划的复选框表示实现与已记录的自动检查完成，未把人工项改写为通过。
- 沿用现有功能分支，保留全部测试、失败 staging 和旧构建；技能 shell 辅助脚本因 Windows 沙箱受限改用等价执行记录。未合并 main、未发布 Release。
