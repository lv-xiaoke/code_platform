# CodeTop macOS Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留 Windows 使用方式的同时，交付可在 macOS 构建和验证的 CodeTop.app、内置 Python、DMG 及双架构 CI。

**Architecture:** React、FastAPI、SQLite 和 API 结果保持共用。平台模块管理路径、启动选项及服务进程身份，独立的 macOS 进程后端和钥匙串后端接入现有运行器及 KeyStore。打包使用独立 macOS spec 和入口，共享资产复制与许可证收集逻辑。

**Tech Stack:** Python 3.12.13、现有 requirements.lock.txt、PyInstaller 6.22.3、React/Vite、macOS Security/CoreFoundation、psutil 7.2.2（仅 Darwin）、GitHub Actions。

**Spec:** [macOS 支持设计](../specs/2026-11-19-macos-support-design.md)，用户于 2026-11-19 确认。

## 执行记录（2026-11-19）

| 任务 | 代码与 Windows 验证 | Mac 环境验证 |
| --- | --- | --- |
| 1 平台路径 | 已实施并回归 | 真实冻结目录待验收 |
| 2 启动恢复 | 已实施，身份、锁及启动参数测试通过 | Finder、关页退出及恢复助手待验收 |
| 3 凭据 | 已实施，Windows DPAPI 回归和 Mac 后端选择测试通过 | 真实钥匙串待验收 |
| 4 原生执行 | 已实施，Windows 执行及 Mac 状态分类测试通过 | Mac 进程、采样、取消和管道测试待执行 |
| 5 打包 | 已实施，构建逻辑测试通过、公共前端构建通过 | 双架构应用、DMG、签名及公证待执行 |
| 6 CI 与迁移 | 已加入工作流，Windows 合成备份导出/恢复通过 | 未推送触发 CI，真实跨系统交换待执行 |

以下为原实施步骤清单；真实平台验收未执行的步骤仍属未完成。独立审查已完成，发现的签名缓存、相对路径、空 PATH 浏览器启动、CPU 信号分类、管道线程和动态库依赖问题均已补充代码及回归测试。最新命令结果与限制记录在 [验收记录](../../macos-validation.md)。

## Global Constraints

- Windows 发布与 Start-CodeTop.cmd 入口保留现有行为。
- 仅监听 127.0.0.1。
- 源码模式继续默认项目 data/，显式 CODETOP_DATA_DIR 优先。
- Mac 学习数据放在 `~/Library/Application Support/CodeTopLocal/`，应用包不写用户数据。
- 普通样例保持 2 秒墙钟、3 秒 CPU、64 KiB 输出；交互模式沿用现有 300 秒墙钟、3 秒 CPU、64 KiB 输入及输出。
- 内存目标为 256 MiB，macOS 采用实际常驻内存监测而非将 RLIMIT_AS 当成与 Windows 等价的硬限制。
- Key 不写入 SQLite 和学习备份，跨设备迁移后重新配置。
- 禁止批量删除，所有输出写入新的明确目录。
- Apple Silicon arm64 为首个验收目标；Intel x86_64 使用独立构建和验收。
- macOS 13 是初始目标，只有对应环境验收后才承诺支持；新系统 CI 通过不能证明旧系统兼容。
- 本机为 Windows，Mac 应用构建、钥匙串、签名、公证、Finder 启动和 Safari 验收必须由 macOS 实机或 CI 提供证据。
- 本次不自动上传 GitHub Release、不申请账号或购买证书。
- 用户原有修改先检查并保留；测试产物沿用仓库自定义 tmp_path 保留策略。

## Review Focus

1. 从带中文/空格的 Applications 路径启动、移动应用、PATH 为空：资源正确定位，用户目录仍可写（任务 1、5）。
2. 恢复时 PID 复用、服务未释放锁、助手晚启动：不误恢复或终止无关进程，原数据保留（任务 2）。
3. 钥匙串拒绝访问、空条目与多数据目录：不泄露 Key、不静默降级明文、不覆盖其他目录凭据（任务 3）。
4. 父进程先退出而子进程持有管道、停止时等待输入、UTF-8 输出截断：有界退出并回收资源（任务 4）。
5. 内置 Python 签名后哈希改变、依赖架构不符、运行时符号链接越界：构建失败或正确生成最终清单，不产生看似成功的坏包（任务 5）。

## 执行约定

推荐由当前会话原生执行，六项任务存在连续接口依赖，先完成每项测试循环再进入下一项。若用户选择子代理执行，按相同任务边界交接，不并行改动同一文件。隔离工作区由 using-git-worktrees 技能在实施开始时处理，不能丢失本设计和计划。

以下 PowerShell 测试命令从项目根目录运行，解释器为 `backend/.venv/Scripts/python.exe`；Mac 命令使用已安装锁定依赖的 Python 3.12.13。每项先观察新测试因缺少行为而失败，再实现，再运行相关回归。只在测试通过后提交该任务列出的文件，先检查 `git diff --cached`，不打包用户无关修改。没有 Mac 环境时完成可在 Windows 运行的单元测试及代码，保留 Mac 验收未完成项。

## Task 1: 平台路径和运行时定位

**Files:**
- Create: `backend/app/platforms.py`
- Modify: `backend/app/paths.py`
- Modify: `backend/tests/test_desktop.py`
- Create: `backend/tests/test_platforms.py`

**Interfaces:**
- Consumes: 现有 sys.frozen、sys.executable、CODETOP_DATA_DIR。
- Produces: `platforms.system_name() -> str`（windows/macos/unsupported）、`platforms.architecture() -> str`（arm64/x86_64）、`platforms.background_options() -> dict`。
- Produces: 保持 `application_root() -> Path`、`native_python() -> Path`、`default_data_dir() -> Path`、`verify_bundled_runtime() -> None`。
- Mac 冻结布局：application_root 为 Contents/Resources，解释器为 Resources/python/bin/python3；Mac 清单新增 executable 字段。Windows 接受已有无 executable 字段清单，默认 python.exe。

- [ ] **Step 1: 写失败测试，隔离平台识别，避免修改全局 os.name。**

```python
def test_frozen_macos_paths_ignore_cwd(tmp_path, monkeypatch):
    import sys
    from app import paths, platforms
    contents = tmp_path / '中文 App.app' / 'Contents'
    (contents / 'MacOS').mkdir(parents=True)
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(contents / 'MacOS' / 'CodeTop'))
    monkeypatch.setattr(paths.Path, 'home', lambda: tmp_path / '用户')
    monkeypatch.delenv('CODETOP_DATA_DIR', raising=False)
    monkeypatch.chdir(tmp_path)
    assert paths.application_root() == contents / 'Resources'
    assert paths.native_python() == contents / 'Resources/python/bin/python3'
    assert paths.default_data_dir() == tmp_path / '用户/Library/Application Support/CodeTopLocal'
```

再以参数化测试覆盖显式数据目录、源码模式、Windows 原布局、清单 executable 缺失/越界、文件损坏和空清单。现有 Windows 路径测试显式 monkeypatch system_name 为 windows，使其可在 Mac 上运行。

- [ ] **Step 2: 运行新测试并记录预期失败。**

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_platforms.py backend/tests/test_desktop.py -q
```

预期首先因缺少 app.platforms 或 Mac 路径错误失败。

- [ ] **Step 3: 实现集中平台分支和布局。**

```python
def background_options():
    return {'creationflags': 0x08000000} if system_name() == 'windows' else {'start_new_session': True}

def application_root():
    if getattr(sys, 'frozen', False):
        executable_dir = Path(sys.executable).resolve().parent
        if platforms.system_name() == 'macos':
            return executable_dir.parent / 'Resources'
        return executable_dir
    return Path(__file__).resolve().parents[2]
```

平台识别使用 sys.platform 和 platform.machine；未知平台报清晰错误。校验清单先解析相对解释器及所有文件路径，拒绝绝对路径、上级越界和解析后逃出 runtime 根目录的链接，再逐个 SHA-256 检查。保留 Windows 现有清单兼容。

- [ ] **Step 4: 重跑上述测试；检查从其他工作目录启动不影响路径。**
- [ ] **Step 5: 只提交本任务四个文件。**

```powershell
git add backend/app/platforms.py backend/app/paths.py backend/tests/test_desktop.py backend/tests/test_platforms.py
git diff --cached --stat
git commit -m "feat: add macOS application and runtime paths"
```

## Task 2: 跨平台启动和恢复助手

**Files:**
- Modify: `backend/app/platforms.py`, `backend/app/desktop.py`, `backend/app/desktop_restore.py`, `backend/app/runtime.py`
- Modify: `backend/requirements.lock.txt`, `packaging/build-requirements.lock.txt`
- Create: `backend/tests/test_desktop_platforms.py`
- Modify: `backend/tests/test_desktop.py`

**Interfaces:**
- Consumes: Task 1 路径和 background_options；既有 RuntimeLock 与 BrowserServer。
- Produces: `platforms.process_identity(pid: int) -> str | None`、`platforms.wait_for_process(pid: int, identity: str | None, timeout: float) -> None`、`platforms.show_error(message: str) -> None`。
- 恢复 CLI 新增 `--parent-identity`，助手先确认服务身份结束，再等待 service.lock 可取得；restore_backup 最终再次取得独占锁，避免检查与使用之间的竞态。
- Darwin 依赖为 `psutil==7.2.2; sys_platform == "darwin"`，加入运行与桌面构建锁文件；Windows 不依赖它。Mac 身份使用 PID 与 psutil.create_time，Windows 保留 OpenProcess 句柄等待。
- 构建依赖中 pywin32-ctypes 和 pefile 加 `sys_platform == "win32"` 环境标记，Windows 继续使用原固定版本；Mac 依赖安装不得尝试导入 Windows 组件。

- [ ] **Step 1: 新增不需真实 Mac 的启动参数和恢复等待测试。**

```python
def test_macos_background_options_never_pass_creationflags(monkeypatch):
    from app import platforms
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    options = platforms.background_options()
    assert 'creationflags' not in options
    assert options['start_new_session'] is True

def test_wait_does_not_wait_for_reused_pid(monkeypatch):
    from app import platforms
    monkeypatch.setattr(platforms, 'process_identity', lambda pid: 'new-instance')
    platforms.wait_for_process(12345, identity='old-instance', timeout=0)
```

补充 Popen 捕获测试，确保 desktop.launch 与 start_restore_helper 都使用平台选项；通过受控假进程验证健康检查超时终止本次进程、无关健康服务不被复用、已启动服务不被重复创建。持有 RuntimeLock 时触发恢复等待超时，断言原库内容不变；旧 attempt 迟到仍不提交。BrowserTabs 已有测试继续覆盖刷新、多标签和关页宽限期。

- [ ] **Step 2: 运行 test_desktop_platforms.py 和 test_desktop.py，确认因缺少身份接口及固定 creationflags 失败。**
- [ ] **Step 3: 实现与接线。**

```python
# desktop.launch 和 desktop_restore.start_restore_helper
process = subprocess.Popen(args, stdout=log, stderr=log, **platforms.background_options())

# confirm 创建助手 argv 时，记录当时的服务实例，不在助手启动后猜测。
identity = platforms.process_identity(os.getpid())
if identity is not None:
    argv.extend(['--parent-identity', identity])
```

Mac wait_for_process 每 50 ms 检查同一实例；超时抛 RuntimeError，不杀死父服务。助手等待 service.lock 使用短暂独占锁探测和同一个总截止时间；随后原子恢复仍以 restore_backup 的锁为准。Windows API 移入平台函数并延迟加载，desktop 模块不再导入 wintypes。Mac 错误提示通过固定 osascript 程序经 stdin/argv 输入消息、不拼接消息到脚本，失败至少保留日志并输出日志路径；Windows 保持 MessageBox。

desktop.serve 仅 Windows 显式 SelectorEventLoop，Mac 使用正常 asyncio.run；保留 browser tabs 行为，--no-browser 仍指不自动开页。新增源码开发脚本的常驻模式在任务 6 使用 app.serve，不混淆桌面关页生命周期。

- [ ] **Step 4: 运行验证。**

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_desktop_platforms.py backend/tests/test_desktop.py backend/tests/test_browser_lifetime.py -q
```

生命周期回归使用仓库已有 test_browser_lifetime.py，同时保留本任务新增的恢复等待测试。

- [ ] **Step 5: 提交本任务文件；确保 Windows 启动入口文件没有被无关修改。**

```powershell
git add backend/app/platforms.py backend/app/desktop.py backend/app/desktop_restore.py backend/app/runtime.py backend/requirements.lock.txt packaging/build-requirements.lock.txt backend/tests/test_desktop_platforms.py backend/tests/test_desktop.py
git diff --cached --stat
git commit -m "feat: support macOS desktop launch and restore lifecycle"
```

## Task 3: 系统钥匙串凭据后端

**Files:**
- Create: `backend/app/ai/macos_keychain.py`
- Modify: `backend/app/ai/secrets.py`
- Create: `backend/tests/test_keystore.py`, `backend/tests/test_macos_keychain.py`
- Modify: `backend/tests/test_ai.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: Task 1 system_name 与规范化数据目录。
- Produces: `macos_keychain.read(service: str, account: str) -> str | None`、`macos_keychain.write(service: str, account: str, value: str) -> None`。
- KeyStore.read()/write(key) 保持现有签名；Mac service 固定 CodeTopLocal.DeepSeek；account 为规范化数据目录 UTF-8 字节的 SHA-256，源码与冻结版同目录得到相同账户。

- [ ] **Step 1: 写隔离后端测试。**

```python
def test_macos_key_is_scoped_to_data_directory(tmp_path, monkeypatch):
    from app import platforms
    from app.ai import macos_keychain, secrets
    saved = {}
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setattr(macos_keychain, 'read', lambda s, a: saved.get((s, a)))
    monkeypatch.setattr(macos_keychain, 'write', lambda s, a, v: saved.__setitem__((s, a), v))
    first, second = secrets.KeyStore(tmp_path / '甲'), secrets.KeyStore(tmp_path / '乙')
    first.write('sk-unit-test')
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    assert first.read() == 'sk-unit-test'
    assert second.read() == ''
    assert not list(tmp_path.rglob('*.dpapi'))
```

同时验证条目不存在时环境变量回退、访问拒绝时报错、无明文文件、日志/异常不含 Key。Mac-only 集成测试使用随机账户写入/读取，然后只删除该明确测试条目；不接触用户真实条目。

- [ ] **Step 2: 运行 test_keystore.py 确认缺少 Mac 后端失败。**
- [ ] **Step 3: 用 ctypes 延迟载入 Security 与 CoreFoundation。**

```python
# Security.framework 调用的语义边界
# SecItemCopyMatching -> errSecItemNotFound(-25300): return None
#                       errSecSuccess(0): 解码 CFData，finally CFRelease
#                       其他 OSStatus: 抛不包含 Key 的 ValueError
# write: SecItemUpdate；仅 errSecItemNotFound 时 SecItemAdd
#       如竞争导致 errSecDuplicateItem，再 Update 一次
def credential_account(data_dir):
    import hashlib
    return hashlib.sha256(str(Path(data_dir).resolve()).encode('utf-8')).hexdigest()
```

对所有 C 函数声明 argtypes/restype，构造含 kSecClassGenericPassword、service、account 的 CFDictionary；持有并释放自行创建的 CFString/CFData/CFDictionary。不写 shell 密钥参数。Windows crypt 函数及原路径保持，非 Mac/Windows 使用既有环境变量行为并对保存报清晰错误。

在 Mac 的 AI 业务测试 fixture 注入内存凭据后端，避免全套测试弹钥匙串授权；Windows 保留真实 DPAPI 测试。将 test_ai.py 中读取 ai-key.dpapi 的断言只用于 Windows，所有平台都验证响应、数据库和备份无密钥。

- [ ] **Step 4: Windows 运行以下命令；Mac 运行同一组及 test_macos_keychain.py 的真实系统测试。**

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_keystore.py backend/tests/test_macos_keychain.py backend/tests/test_ai.py -q
```

- [ ] **Step 5: 提交六个任务文件。**

```powershell
git add backend/app/ai/macos_keychain.py backend/app/ai/secrets.py backend/tests/test_keystore.py backend/tests/test_macos_keychain.py backend/tests/test_ai.py backend/tests/conftest.py
git diff --cached --stat
git commit -m "feat: store macOS AI credentials in Keychain"
```

## Task 4: macOS 本机执行与交互输入

**Files:**
- Create: `backend/app/runner/macos_process.py`, `backend/runner/native_bootstrap.py`
- Modify: `backend/app/runner/native_process.py`, `backend/app/runner/native.py`, `backend/app/runner/terminal_native.py`
- Create: `backend/tests/test_native_platforms.py`, `backend/tests/test_macos_runner.py`
- Modify: `backend/tests/test_native_runner.py`

**Interfaces:**
- Consumes: paths.native_python、Task 2 的 Darwin psutil 依赖。
- Produces: MacProcess(argv, cwd, env, memory_mb=256, max_processes=32)，公开 stdin/stdout/stderr、pid、memory_exceeded，以及 poll()、cpu_seconds()、limit_events()、terminate()、wait(timeout=5)、close()，与当前 JobProcess 消费接口兼容。
- execute_process 保持现有调用签名，按平台延迟导入对应 Process 后端。NativeRunner 新增 python_version 独立属性，image_ref 含平台架构；terminal 不再通过删除 windows-x64 后缀解析版本。

- [ ] **Step 1: 新增后端选择测试与 Mac 真实运行测试。**

```python
@pytest.mark.skipif(sys.platform != 'darwin', reason='requires macOS')
@pytest.mark.parametrize('code,status', [
    ('print("你好")', 'executed'),
    ('if :', 'syntax_error'),
    ('raise ValueError("bad")', 'runtime_error'),
    ('while True: pass', 'time_limit'),
    ('while True: print("x" * 8192)', 'output_limit'),
    ('a=[]\nwhile True: a.append(bytearray(20*1024*1024))', 'memory_limit'),
])
def test_macos_statuses(tmp_path, code, status):
    from uuid import uuid4
    from app.runner.native import NativeRunner
    runner = NativeRunner(tmp_path)
    try:
        result = runner.execute(str(uuid4()), code, [{'stdin': ''}])['results'][0]
        assert result['status'] == status, result
        assert len((result['stdout'] + result['stderr']).encode()) <= 65536
    finally:
        runner.close()
```

再测 input 中文回显/EOF、双并发、等待输入时停止、服务 close 时活动任务停止、Unicode 截断、子进程持有 stdout 后父退出、循环创建子进程时资源监测、进程已退出后终止幂等。进程清理断言使用 PID + 创建时间，不能误判复用 PID。通用测试用假的 MacProcess 验证 Windows 不加载 Mac 原生库，Mac 不加载 msvcrt。

- [ ] **Step 2: Windows 运行新平台测试得到失败；Mac 运行 test_macos_runner.py 得到原生健康检查不支持的失败。**
- [ ] **Step 3: 实现可信 bootstrap，限制先于用户代码执行。**

```python
# backend/runner/native_bootstrap.py 的主流程；在独立解释器中执行。
import resource
import runpy
import sys
resource.setrlimit(resource.RLIMIT_CPU, (3, 4))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
runpy.run_path(sys.argv[1], run_name='__main__')

# MacProcess：不使用 shell、不使用 preexec_fn。
self.process = subprocess.Popen(
    command, cwd=cwd, env=env, stdin=subprocess.PIPE,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    bufsize=0, start_new_session=True, close_fds=True,
)
```

MacProcess 把原 script 参数替换为可信 bootstrap + script。bootstrap 位于 application_root/backend/runner；源码和打包路径一致。env 仅包含明确允许的 TMPDIR、HOME、语言编码所需变量，PATH 指向内置解释器目录；不继承 DEEPSEEK_API_KEY、PYTHONPATH、DYLD_*。

每次监督轮询用 psutil 获取同进程组进程，对每个 (pid, create_time) 保留 CPU 最大读数，累计已退出成员读数，对仍在组内成员聚合 RSS；捕获 NoSuchProcess，权限错误终止本次运行并报告监督不可用，不能静默放行。RSS 超 256 MiB 标记 memory_exceeded；成员超过 32 个终止并给出资源错误。killpg 前检查组身份，清理时即使 leader 已退出仍结束持有管道的组成员；终止和 close 可重复调用。

保留传输队列和 UTF-8 增量解码，线程退出设有总截止时间，不能因后台子进程管道永不 EOF 卡死请求。原 JobProcess 代码不重写。NativeRunner.health 使用平台启动选项、独立版本值，并附 memory_enforcement=rss-monitor 说明，不将采样宣称为硬内存限制。

- [ ] **Step 4: 运行测试并核对 Windows 原有行为。**

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_native_platforms.py backend/tests/test_native_runner.py backend/tests/test_macos_runner.py -q
```

Mac 执行同组测试，平台专有测试跳过符合预期；共用正常执行及授权测试不能整体跳过。

- [ ] **Step 5: 提交本任务八个文件。**

```powershell
git add backend/app/runner/macos_process.py backend/runner/native_bootstrap.py backend/app/runner/native_process.py backend/app/runner/native.py backend/app/runner/terminal_native.py backend/tests/test_native_platforms.py backend/tests/test_macos_runner.py backend/tests/test_native_runner.py
git diff --cached --stat
git commit -m "feat: execute local Python practice on macOS"
```

## Task 5: Mac 应用与 DMG 构建

**Files:**
- Create: `scripts/desktop_assets.py`, `scripts/build_macos.py`, `scripts/build-macos.sh`, `packaging/macos.spec`, `packaging/macos-entitlements.plist`
- Modify: `scripts/build_desktop.py`
- Create: `backend/tests/test_macos_packaging.py`

**Interfaces:**
- Consumes: Task 1 Resources 布局、Task 4 bootstrap、现有 releases/current.json 和版本常量。
- Produces: `desktop_assets.copy_assets(stage: Path) -> None`、`desktop_assets.copy_licenses(stage: Path) -> None`，由 Windows 和 Mac 构建器共用。
- Produces: `python scripts/build_macos.py --python-root ABSOLUTE_ROOT --arch arm64|x86_64 [--identity ID --notary-profile PROFILE]`；默认维护者测试构建，正式分发必须同时提供签名及公证参数。
- 输出写入 runtime/macos-build-时间-随机值、dist/macos-时间-随机值；产物名称包含应用版本、macos 和架构，测试包明确带 unsigned 字样。

- [ ] **Step 1: 写构建清单测试，不依赖本机 codesign。**

```python
def test_runtime_symlink_cannot_escape_source(tmp_path):
    import pytest
    from scripts.build_macos import validate_runtime_link
    root = tmp_path / 'python'
    root.mkdir()
    external = tmp_path / 'outside'
    external.write_text('not a runtime input')
    link = root / 'bad-link'
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip('symlink creation unavailable')
    with pytest.raises(ValueError, match='outside'):
        validate_runtime_link(link, root)
```

新增清单哈希必须在运行时签名之后生成、Mach-O 架构不符时报错、前端 current.json 路径越界时报错、无密钥/学习库进入包、Windows 原资产结构不变的测试。用 stub 命令执行器验证阶段顺序，不声称 stub 等于签名测试。

- [ ] **Step 2: 运行 test_macos_packaging.py 确认模块不存在失败。**
- [ ] **Step 3: 抽出公共资产复制与许可证逻辑，保留 Windows runtime-lock.json 校验。**

```python
# macos.spec 在 COLLECT 后包装应用，不将学习目录作为 datas。
app = BUNDLE(coll, name='CodeTop.app', bundle_identifier='local.codetop.CodeTop',
             info_plist={'CFBundleDisplayName': 'CodeTop 刷题',
                         'LSUIElement': True,
                         'NSHighResolutionCapable': True})

# 运行时清单由签名完成后的文件生成。
lock = {
    'python_version': RUNTIME_VERSION,
    'platform': 'macos', 'architecture': requested_arch,
    'executable': 'bin/python3',
    'files': {p.relative_to(runtime).as_posix(): digest(p)
              for p in runtime.rglob('*') if p.is_file()},
}
```

Mac spec 排除 windows_job 模块，显式包含 macos_process 和钥匙串模块；读取确切版本，隐藏依赖沿用 Windows。构建器要求 macOS 主机、Python 3.12.13、PyInstaller 6.22.3 与目标架构匹配，pyinstaller 在唯一新目录执行；由 --python-root 提供可重定位 standalone Python，验证 bin/python3 版本/架构及无 PATH 时 import encodings/ssl/sqlite3/ctypes/subprocess。不要把构建虚拟环境或系统 Framework Python 误当便携运行时。

输入运行时清单按平台与架构独立命名，记录源输入哈希；首次生成保存到新构建目录供审阅，已有锁不匹配则拒绝构建。最终签名产生的分发清单位于应用 Resources，不能将含时间戳签名的文件哈希当作跨构建恒定的输入锁。对于 Python 内部符号链接仅允许解析后仍位于源根目录，保留合法链接并记录真实目标校验，不沿越界链接复制。

构建顺序：复制 app/运行时/公共资产及许可证 → 检查链接和 Mach-O 架构/部署目标 → 内部 Mach-O 文件由内到外签名 → 生成最终 runtime-lock.json → 签外层应用并严格验证（不用 --deep 重新签内部）→ 应用归档提交 notarytool --wait → staple 应用 → 生成 DMG → 签名、公证并 staple DMG → 为 DMG 生成 .sha256。unsigned 模式对需签名的可执行文件作 ad hoc 签名并跳过公证，产物及证据明确标注测试用途。公证失败不发布正式命名产物。

entitlements 初始为空字典，只有原生测试证明确有需要时才加具体权限并记录理由，不能默认关闭库验证。DMG 通过 hdiutil create 从专用新 staging 目录生成；只在该目录加入应用副本和 Applications 快捷链接，不清空既有目录。

- [ ] **Step 4: Windows 运行构建逻辑单元测试；Mac 执行应用构建及独立解释器冒烟测试。**

```powershell
backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_macos_packaging.py backend/tests/test_distribution.py -q
```

```bash
python scripts/build_macos.py --python-root "$CODETOP_STANDALONE_PYTHON_ROOT" --arch arm64
```

Mac 将生成应用复制到含中文和空格的新目录后，以最小 PATH 启动内部 Python 和 CodeTop --serve；健康端点和题库应可用，不修改包内资源。签名发布另用提供的 identity/profile 参数完整执行，验证 codesign、spctl 和 stapler。

- [ ] **Step 5: 提交本任务七个文件，不提交本机签名清单或证书。**

```powershell
git add scripts/desktop_assets.py scripts/build_macos.py scripts/build-macos.sh packaging/macos.spec packaging/macos-entitlements.plist scripts/build_desktop.py backend/tests/test_macos_packaging.py
git diff --cached --stat
git commit -m "feat: build macOS CodeTop app and DMG packages"
```

## Task 6: 双架构 CI、迁移和完整验收

**Files:**
- Create: `.github/workflows/macos.yml`, `scripts/verify_macos.py`, `scripts/start-macos.sh`, `scripts/build_frontend.py`, `docs/macos-validation.md`
- Modify: `README.md`, `docs/deployment.md`, `docs/user-guide.md`, `scripts/build.ps1`
- Create: `backend/tests/test_cross_platform_backup.py`

**Interfaces:**
- Consumes: 前五项任务接口与生成应用路径。
- Produces: `python scripts/verify_macos.py --app APP_PATH --report REPORT_PATH`；JSON 报告记录主机系统、架构、产物哈希、执行状态和未执行的人工验收项，不把未执行记为通过。
- 源码入口 `scripts/start-macos.sh [--no-browser]`，检查 backend/.venv/bin/python 及前端 current.json，默认 app.serve --close-with-browser 并开浏览器，--no-browser 常驻。所有路径从脚本位置解析，shell 参数逐个引用。

- [ ] **Step 1: 新增跨目录备份迁移测试。**

```python
def test_backup_restores_to_unrelated_directory(loaded, tmp_path):
    from app.backups import create_backup, restore_backup, inspect_database
    client, app, _, pid = loaded
    response = client.put(f'/api/v1/problems/{pid}/note', json={'revision': 0, 'body_md': '跨平台笔记'})
    assert response.status_code == 200
    source = app.state.db
    backup = create_backup(source)
    target = tmp_path / '另一台电脑 中文' / 'data'
    restore_backup(source.data_dir / 'backups' / backup['filename'], target)
    counts, _ = inspect_database(target / 'study.sqlite3')
    assert counts['problems'] == 4
    assert counts['notes'] >= 1
```

笔记路由已经核实为 PUT /api/v1/problems/{pid}/note，按现有 NoteWrite 的 revision 和 body_md 字段写入。补充进度、收藏、代码历史、导入来源、自定义样例的内容级比较和损坏备份恢复后原数据不变；Mac/Windows CI 交换真实生成备份 artifact，分别恢复并比较同一规范化 JSON 摘要，Key 不含在归档或摘要中。

- [ ] **Step 2: 运行新迁移测试；现有能力应先通过，缺少完整内容校验或 CLI 互换部分再新增失败测试，不人为制造业务失败。**
- [ ] **Step 3: 建立双架构作业并生成证据。**

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - runner: macos-15
        arch: arm64
      - runner: macos-15-intel
        arch: x86_64
runs-on: ${{ matrix.runner }}
permissions:
  contents: read
```

作业检出代码、设置确切 Python 3.12.13 和 Node 工具、安装锁定依赖、检查 uname -m 与矩阵一致、运行全部后端测试/前端既有测试/类型检查、构建前端 release，再运行 Mac 原生测试和 unsigned app 构建。common.ps1 已确认固定 Windows 工具路径，因此新增 scripts/build_frontend.py，并由 build.ps1 调用，统一生成新的 releases/目录及 current.json。build_frontend.py 接受 --node 显式路径，顺序执行 node typescript/bin/tsc -b 与 node vite/bin/vite.js build --outDir 唯一新目录 --emptyOutDir false，核对 index.html 后写 path/built_at/version 与原格式一致的 current 临时清单，再原子替换；保留旧 current 为唯一命名 previous 文件。Windows wrapper 传原 $NodeExe，Mac 构建入口传 CI 指定的 node，不引入第二套清单格式。将既有 test_frontend_release.py 纳入此项回归，模拟构建失败验证 current 不被替换。

运行时来源使用审阅后的固定 URL、SHA-256 和版本，下载后先校验再解包；未提供通过验证的输入清单时构建作业应明确失败而不是自动获取 latest。上传测试报告和各架构 unsigned DMG artifact，不自动创建 Release。正式签名构建使用单独受控 workflow_dispatch job，缺证书或公证配置则明确缺失，不输出正式发布成功。

verify_macos.py 使用新测试数据目录启动应用的内部可执行文件 --serve，检查 health 身份、内置题库、运行器健康、正常 Python 代码及备份恢复；服务启动/等待/退出都有截止时间。退出仅终止本脚本创建并核对身份的服务进程。手工验收项记录 Finder、Safari/Chrome 多标签、钥匙串弹窗、关页退出、干净机器安装和 macOS 13 最低版本验证。CI 没有 GUI 证据不能自动勾选这些项。

- [ ] **Step 4: Windows 完整回归及真实入口检查。**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

若改到前端提示/能力展示，验证后执行 `scripts/build.ps1` 并从根目录 Start-CodeTop.cmd 打开验收；关闭最后一个标签并确认该服务正常退出。源码入口打开浏览器属于 GUI 操作时依照执行环境申请必要权限。

- [ ] **Step 5: 记录 Mac 证据并更新文档。**

docs/macos-validation.md 按架构逐项记录实际命令、结果、报告和产物路径；没有 Mac 环境时明确列出未执行项，不填写“通过”。README 和部署文档区分 Windows 已发布版本、Mac 源码使用、unsigned 维护者测试包及签名正式版，下载链接只指向确实存在的产物。用户已有 README 修改用最小补丁保留。说明钥匙串、数据目录、双向备份、内存采样和签名配置。

- [ ] **Step 6: 提交本任务十个文件；最终检查改动范围及未完成验收项。**

```powershell
git add .github/workflows/macos.yml scripts/verify_macos.py scripts/start-macos.sh scripts/build_frontend.py scripts/build.ps1 docs/macos-validation.md README.md docs/deployment.md docs/user-guide.md backend/tests/test_cross_platform_backup.py
git diff --cached --stat
git commit -m "ci: verify macOS packages and document platform support"
git status --short
```

## 计划自审结果

- 规格的路径、生命周期、凭据、运行器、构建与平台验收分别由任务 1–6 覆盖。
- 五项 Review Focus 均在所属任务加入测试或明确的真实平台验收。
- 进程接口匹配 JobProcess；KeyStore 和 API 保持兼容；新增能力说明为可选字段。
- 输入运行时锁与签名后清单分离，避免签名时间戳破坏输入可复现性。
- 依赖及 runner 资料于 2026-11-19 核对。实际执行时安装失败应记录具体问题，不未经审阅更换锁定版本。
- 本计划已由用户确认并原生执行；代码测试结果和仍待 Mac 环境完成的项目以上方执行记录及验收记录为准。

## 核对来源

- [psutil 7.2.2](https://pypi.org/project/psutil/7.2.2/)
- [GitHub macOS runner 标签与架构](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [PyInstaller 平台要求](https://pyinstaller.org/en/latest/requirements.html)
- [Apple 公证说明](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
