# 安装、部署与常见问题

普通用户优先使用已内置 Python 和题库的安装包：

| 平台 | 下载入口 | 安装与启动 |
| --- | --- | --- |
| Windows 10 / 11 x64 | [v1.6.0 正式版](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0) | 运行 EXE 安装向导，再打开桌面“CodeTop 刷题” |
| Mac M 系列 / Intel | [v1.6.0-macos-test.1 免费测试版](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0-macos-test.1) | 选择对应架构 DMG，将应用拖入 Applications，再打开 CodeTop |

完整应用运行练习无需安装 Docker。Mac 测试版未经过 Apple 公证；源码、旧 Windows 体验 ZIP 和构建工具的准备方式见下文。

## 多语言源码分支（待发布）

当前源码新增 Python 3.12、C17、C++17、Java 21、Node.js 24 的本机执行；已发布 v1.6.0 安装包仍为旧 Python 版本。源码普通启动入口默认本机模式，显式设置 `CODETOP_RUNNER=docker` 才使用仅 Python 的容器模式。

在代码区选择语言，点击“准备环境”下载固定版本。Windows C/C++ 下载完整 LLVM-MinGW，Java 下载 Temurin JDK，JavaScript 下载 Node.js；Mac C/C++ 使用系统 Command Line Tools 和 SDK，需用户按 [Apple 官方说明](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/)安装后重新检查。应用不会调用系统安装命令、修改 PATH/JAVA_HOME 或自动申请系统权限。

环境目录为 Windows `%LOCALAPPDATA%\CodeTopLocal\toolchains`、Mac `~/Library/Application Support/CodeTopLocal/toolchains`，独立于应用文件和学习数据目录。开发及 CI 可用 `CODETOP_TOOLCHAINS_DIR` 指定独立根；切换学习数据目录和恢复备份不删除工具链。失败归档与 staging 保留，可重试，不会批量清理旧文件。

清单 `packaging/toolchains.json` 固定每个平台的 URL、SHA-256、入口和许可证，运行时不查询 latest。开发者准备所有语言用于验收：

```powershell
backend/.venv/Scripts/python.exe scripts/prepare_toolchains.py --languages python,c,cpp,java,javascript --root runtime/toolchains-ci --require-ready
```

Mac 使用 `backend/.venv/bin/python` 运行同一脚本。验收服务需显式设置 `CODETOP_TOOLCHAINS_DIR` 为该根；普通用户直接使用面板默认目录。

升级至 schema 0004 前自动备份旧库；旧 notes 的代码按原语言迁移，包括空白代码和暂不支持执行的语言。0001–0003 备份可恢复并升级，0004 备份包含全部草稿、偏好、共享笔记、历史和运行记录，排除工具链、编译产物和 AI Key。0004 备份需新版应用恢复，不能降级覆盖旧结构。实际验证状态见[多语言验收](multilanguage-acceptance.md)。

## macOS 构建与使用

免费测试版下载见 [v1.6.0-macos-test.1](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0-macos-test.1)。M 系列下载 `arm64-unsigned.dmg`，Intel 下载 `x86_64-unsigned.dmg`，打开 DMG 后将 CodeTop.app 拖入 Applications。M 系列在 macOS 15.8.2、Intel 在 macOS 15.7.9 的 GitHub 环境完成构建及应用内自动验证。

测试版未使用付费 Developer ID、未经过 Apple 公证，首次打开可能被系统拦截。请核对下载来源及 SHA-256，并参考 [Apple 官方安全打开 App 的说明](https://support.apple.com/zh-cn/102445)。用户无需开通 Apple 开发者账号。Finder、浏览器界面及干净电脑安装仍需实机反馈；macOS 13 只是构建目标，尚未在该系统版本验收。执行记录见 [macOS 验收](macos-validation.md)。

### 从源码启动（Mac）

维护者需要 Python 3.12.13、Node 24.10.0、Bun 1.3.5；下载 DMG 使用的用户无需这些工具。在项目根目录执行：

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock.txt
(cd frontend && bun install --frozen-lockfile)
backend/.venv/bin/python scripts/build_frontend.py --node "$(command -v node)"
bash scripts/start-macos.sh
```

默认打开浏览器并在最后一个 CodeTop 标签关闭后退出服务；`bash scripts/start-macos.sh --no-browser` 常驻运行。源码数据默认保存在项目 `data/`，可用 CODETOP_DATA_DIR 指定独立目录。

### 构建 CodeTop.app 和测试 DMG

在对应架构的 Mac 上执行，不能在 Windows 交叉打包。运行时来自固定的 [python-build-standalone 20260623 发布](https://github.com/astral-sh/python-build-standalone/releases/tag/20260623)，下载 URL 和 SHA-256 记录在 `packaging/macos-python-sources.json`，不自动选择 latest。获取与打包使用分离的环境，不向内置解释器安装用户依赖：

```bash
python_root="$(python3.12 scripts/fetch_macos_python.py --arch arm64)"
"$python_root/bin/python3" -m venv runtime/macos-build-env
runtime/macos-build-env/bin/python -m pip install -r packaging/build-requirements.lock.txt
runtime/macos-build-env/bin/python scripts/build_macos.py --python-root "$python_root" --arch arm64
```

Intel 将两处 `arm64` 改为 `x86_64`。构建前需要按上节安装前端依赖并生成 release。已有构建环境目录时换用一个新名称，不删除或覆盖旧目录。也可设置 CODETOP_BUILD_PYTHON 后通过 `bash scripts/build-macos.sh` 传入同样参数。

输出写入新的 `runtime/macos-build-*` 和 `dist/macos-*`；无证书参数的包以 `-unsigned.dmg` 命名，仅用于维护者测试。Apple Silicon 必需的 ad hoc 签名不等于 Developer ID 签名或 Apple 公证。测试包可能被 Gatekeeper 阻止，不要求用户关闭系统防护来运行。

正式分发需事先在 Mac 构建环境配置 Developer ID 和 notarytool 钥匙串配置，然后增加：

```bash
runtime/macos-build-env/bin/python scripts/build_macos.py \
  --python-root "$python_root" --arch arm64 \
  --identity 'Developer ID Application: YOUR NAME (TEAMID)' \
  --notary-profile 'codetop-notary'
```

脚本会由内到外签名、生成签名后运行时哈希、公证应用与 DMG、附加票据并输出校验文件；失败时不标记正式发布成功。证书、私钥和 Apple 凭据不得加入仓库。本仓库的 Mac CI 只生成测试 artifact，正式签名使用上述显式命令，不自动发布 Release。

### 数据和运行限制

完整 Mac 应用的数据、备份和日志位于 `~/Library/Application Support/CodeTopLocal/`，升级应用文件不覆盖学习数据。AI Key 保存在系统钥匙串，不随学习备份迁移；不同数据目录分别关联凭据。钥匙串拒绝访问时不会降级为明文文件。

Windows/Mac 使用相同的学习备份格式；跨设备恢复后重新配置 AI Key。本机练习可以访问当前用户文件和网络。Mac 使用进程组管理及 RSS 采样监测，256 MiB 是监测阈值，可能短暂超出，与 Windows Job Object 硬限制不同；本机模式不提供恶意代码隔离。普通样例 2 秒墙钟、交互模式 300 秒墙钟，CPU 预算 3 秒，输入与输出各 64 KiB。Mac 应用及 start-macos.sh 固定使用本机执行器；需要 Docker 模式的开发者可从 backend 目录设置 CODETOP_RUNNER=docker 后直接运行 app.serve。

---

## Windows 安装与源码部署

Windows 正式版面向 Windows 10 / 11 x64 的个人本机使用。源码或旧体验 ZIP 请解压到可写的本地目录，例如 `D:\Apps\CodeTop-Local`。支持中文和空格路径；不要直接在 ZIP 内启动，也不要复制另一台机器的 `.venv` 使用。

## 安装前需要什么

**v1.6.0 完整桌面版**：Windows x64 和现代浏览器，下载 `CodeTop-Setup-1.6.0-windows-x64.exe`，双击完成中文安装向导，然后点击桌面“CodeTop 刷题”。内置 Python、依赖与题库，无需 uv、Node、Docker、WSL 或安装时联网。第一次运行代码需确认本机文件与网络访问说明；运行限制不等于隔离沙箱。

桌面版数据、备份与日志位于 `%LOCALAPPDATA%\CodeTopLocal`，程序文件默认位于 `%LOCALAPPDATA%\Programs\CodeTopLocal`。设置中提供完整备份恢复入口，自动校验、先备份再恢复并重启，失败时保留原数据。AI Key 不随备份迁移。

**下表及后续脚本安装步骤对应旧体验 ZIP 和源码方式**，不适用于完整桌面安装包：

| 安装方式 | 首次准备 | 日常启动 |
| --- | --- | --- |
| Windows 体验包 | uv、网络；脚本准备 Python 3.12 与后端依赖 | 双击 Start-CodeTop.cmd |
| 源码 | uv、Node.js/npm、网络；Git 或源码 ZIP | 同上 |

已发布的旧体验 ZIP 默认使用 Docker；当前多语言源码入口默认使用本机运行器。开发者显式设置 `$env:CODETOP_RUNNER='docker'` 时，需要启动 Docker Desktop 的 Linux 容器并准备指定 Python 镜像。完整 Windows 安装包和 Mac DMG 使用内置 Python，无需 Docker。仅浏览题库、记录笔记或编辑代码时也无需 Docker。

先运行 `uv --version`：能显示版本号说明已安装，无需重复安装。提示找不到命令时，可参考 [官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)，WinGet 命令为 `winget install --id=astral-sh.uv -e`。安装完成后重新打开终端，运行 `uv --version` 确认 PATH 生效。Python 3.12 由 uv 按需获取。

下载源码不需要配置 GitHub OAuth 或 `.env`；`frontend/.env.example` 是保留的上游配置示例，本地题单不依赖它。

## 首次安装

普通用户双击 `Setup-CodeTop.cmd`。也可以在项目根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

如果目录带 `releases/current.json`，默认使用预构建页面，只准备后端和题库；源码目录首次安装会准备前后端并构建。

可显式指定模式：

```powershell
# 只接受带预构建页面的体验包
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -RuntimeOnly

# 源码构建，即使当前目录已有旧构建
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -BuildFromSource
```

`-SkipBuild` 为开发用途：安装前后端依赖并初始化，但不构建；需要之后自行运行 `scripts/build.ps1`。不要与 `-RuntimeOnly` 同用。

安装过程不会重置已有题库和学习记录。看到 `Setup complete` 后双击 `Start-CodeTop.cmd`。浏览器打开 `http://127.0.0.1:8000`，默认显示内置题单。

## Docker 代码运行环境（仅 Docker 模式）

按 [Docker Desktop Windows 官方安装说明](https://docs.docker.com/desktop/setup/install/windows-install/)完成安装及所需系统配置。已经安装的用户无需重复安装，打开 Docker Desktop 并等待引擎启动，确认使用 Linux 容器：`docker version` 应显示 Client 和 Server，`docker info --format '{{.OSType}}'` 应返回 `linux`。然后在项目根目录执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-runner.ps1
```

该命令拉取 `backend/runner/runtime.json` 指定的固定 Python 镜像，首次下载需要网络。看到 `Python ACM runner image is ready` 后，刷新练习面板，确认“Docker 已就绪”再运行代码。每次运行代码时都要保持 Docker Desktop 启动，镜像已准备好后无需每次重复下载。不运行代码时无需 Docker，读题、编辑代码和保存笔记仍可用。

运行区要求完整 Python ACM 程序。`input()` 可在终端等待输入；`sys.stdin.read()` 需要点击“结束输入”。运行和高级测试的详细说明见[使用手册](user-guide.md#日常使用)。

## 可选的 AI 助教

打开页面设置或练习面板中的“AI 设置”，输入自己的 DeepSeek Key，保存并测试连接。AI 调用需要联网，发送所选题面、代码和问题等上下文。界面模型能否使用以自己的 DeepSeek 账户为准。

Windows 的 Key 使用 DPAPI 加密，保存为当前数据目录下的 `ai-key.dpapi`：完整安装包位于 `%LOCALAPPDATA%\CodeTopLocal`，源码默认位于项目 `data/`。Mac 使用系统钥匙串，不生成 DPAPI 文件。Key 均不包含在学习备份中；换电脑或更换数据目录后重新配置。不要把整个数据目录作为软件包分享。

## 启动、退出和端口

Windows 完整安装包从桌面“CodeTop 刷题”启动，源码或旧体验 ZIP 使用 `Start-CodeTop.cmd`；Mac 打开 Applications 中的 CodeTop。关闭最后一个 CodeTop 标签页后，服务约 5 秒内退出。重复启动会复用同应用、同数据目录的服务。下面的 PowerShell 端口与停止命令适用于 Windows 源码/体验 ZIP。

默认端口被其他程序占用时：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Port 8010
```

手动停止对应端口的服务：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1 -Port 8010
```

仅在开发时需要服务常驻：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -NoBrowser
```

默认只允许本机访问。当前没有公网多用户部署入口，也不要将本地端口通过代理暴露给他人。

## 备份、恢复与升级

建议使用页面“设置 → 完整备份 → 生成并下载完整备份”。命令行也可执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup.ps1
```

自动备份保存在当前数据目录的 `backups/` 下：Windows 安装包为 `%LOCALAPPDATA%\CodeTopLocal\backups`，Mac 为 `~/Library/Application Support/CodeTopLocal/backups/`，源码默认是 `data/backups/`。内容包括一致性数据库、来源文件、校验信息和代码历史，不包含 AI Key。不要只复制运行中的 `study.sqlite3` 文件。

Windows 与 Mac 完整应用都可在页面“设置 → 完整备份”预览并确认恢复，恢复后服务重启。以下新目录升级和 PowerShell 恢复命令用于 Windows 源码/旧体验 ZIP。

升级推荐新目录安装，保留旧目录，然后恢复完整备份：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\restore.ps1 -Archive "D:\Backups\codetop-backup.zip"
```

恢复前脚本会停止本目录服务并备份当前数据；成功后重新启动。不要将旧 `.venv` 搬进新目录。若还开着旧目录的应用，请先关闭旧标签页，避免占用 8000 端口。

## 常见问题

| 提示或现象 | 处理方式 |
| --- | --- |
| 找不到 uv / uv is required | 安装 uv，重新打开终端，用 `uv --version` 检查，再运行 Setup-CodeTop.cmd |
| 源码安装提示 npm 缺失 | 安装含 npm 的 Node.js，或改用 Releases 中的体验 ZIP |
| 提示 Built-in catalog missing | 下载完整仓库或体验 ZIP，确认存在 `vendor/algoTop-main/public/data/codetop.json` |
| 双击启动提示 Python environment missing | 先运行 Setup-CodeTop.cmd；只下载解压还没有安装后端依赖 |
| 提示 Frontend build missing | 源码运行 `setup.ps1 -BuildFromSource`；体验包请完整解压 |
| 依赖下载或镜像拉取失败 | 检查网络、代理与对应服务访问权限，保留目录后重试安装或镜像准备命令 |
| 原题网站打不开 | 本地题面仍可用，原题链接需要访问外部网站 |
| 题单按最近三个月筛选后为空 | 内置数据是固定快照，最近考察日期不会随今天自动更新，先切回“不限时间” |
| 端口被占用 | 关闭旧 CodeTop 标签页，或使用 `start.ps1 -Port 8010`；脚本不会终止不属于本目录的其他程序 |
| Docker 未就绪 / 镜像未安装 | 启动 Docker Desktop 的 Linux 容器引擎，运行 setup-runner.ps1 |
| AI 无法连接 | 在 AI 设置测试连接，检查自己的 Key、账户余额、模型权限和网络 |
| PowerShell 阻止直接执行 ps1 | 使用 CMD 入口，或按文档的 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...` 运行，无需永久修改执行策略 |

完整应用日志位于用户数据目录的 `logs/` 下，Windows 源码/体验 ZIP 的启动日志位于项目 `runtime/server-*.log`、`runtime/server-*.err.log`。反馈问题时提供操作步骤与相关错误日志，隐藏个人数据和 Key。

## 维护者：生成发布包

在完成源码安装和验证后执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\package-release.ps1
```

发布脚本重新构建前端，生成 `dist/CodeTop-Local-Windows-<时间>-<编号>.zip` 及 `.zip.sha256`。如已构建且验证过，也可使用 `package-release.ps1 -SkipBuild`。包内只包含当前页面，不含旧版本和源码构建工具；体验包不能代替完整开发仓库。

校验下载文件：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath ".\CodeTop-Local-Windows-实际文件名.zip"
```

将结果与旁边 `.sha256` 文件中的值比较。发布前从 ZIP 解压到新目录，运行 Setup 和 Start，确认题单与可选功能说明一致。将 ZIP 和校验文件上传到仓库 Releases；本地生成不等于已上传发布。

构建、安装、测试和打包脚本均不提供批量清理功能；旧构建、测试目录、备份和输出产物保留，按需由维护者手动管理。

## 维护者构建完整桌面安装包

最终用户不需要构建工具。维护者需要已完成的源码环境，以及独立的 `runtime/desktop-work/build-env` 构建虚拟环境。按 `packaging/build-requirements.lock.txt` 安装构建依赖；Python 基础运行时固定为 3.12.13，PyInstaller 固定为 6.22.3。

安装器编译器使用官方 Inno Setup 7.1.1 x64，保存在 `runtime/desktop-work/inno/ISCC.exe`，原安装文件保存在 `runtime/desktop-work/innosetup-7.1.1-x64.exe`。构建脚本核对其官方 SHA256。Python 标准库和二进制文件的逐文件哈希保存在 `packaging/runtime-lock.json`；更换工具或运行时需先审阅并更新锁文件，不接受静默版本漂移。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-desktop.ps1
```

每次使用全新的 `runtime/desktop-build-*` 目录构建，在 `dist/desktop-*/` 输出 EXE 和 SHA256。旧构建保留。安装包包含许可说明和逐文件分发清单，不包含学习数据库、Key、首次运行确认记录、开发环境和日志。验收应从实际安装后的程序或快捷方式进行，不能仅以源码测试或 EXE 构建成功代替安装验证。
