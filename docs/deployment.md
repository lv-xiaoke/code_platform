# 安装、部署与常见问题

CodeTop Local 当前验证目标是 Windows 10 / 11 x64 的个人本机使用。建议将目录放在可写的本地磁盘，例如 `D:\Apps\CodeTop-Local`。支持中文和空格路径；不要直接在 ZIP 内启动，也不要复制另一台机器的 `.venv` 使用。

## 安装前需要什么

| 安装方式 | 首次准备 | 日常启动 |
| --- | --- | --- |
| Windows 体验包 | uv、网络；脚本准备 Python 3.12 与后端依赖 | 双击 Start-CodeTop.cmd |
| 源码 | uv、Node.js/npm、网络；Git 或源码 ZIP | 同上 |

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

## 可选的 Python 运行环境

安装 Docker Desktop，启动后切换到 Linux 容器，再执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-runner.ps1
```

该命令拉取 `backend/runner/runtime.json` 指定的固定 Python 镜像。不需要把整个 CodeTop 放进 Docker。不运行代码时无需 Docker，读题、编辑代码和保存笔记仍可用。

运行区要求完整 Python ACM 程序。`input()` 可在终端等待输入；`sys.stdin.read()` 需要点击“结束输入”。运行和高级测试的详细说明见[使用手册](user-guide.md#日常使用)。

## 可选的 AI 助教

打开页面设置或练习面板中的“AI 设置”，输入自己的 DeepSeek Key，保存并测试连接。AI 调用需要联网，发送所选题面、代码和问题等上下文。界面模型能否使用以自己的 DeepSeek 账户为准。

Key 以 Windows DPAPI 加密存放在 `data/ai-key.dpapi`，不包含在学习备份中。新目录或新电脑恢复学习备份后，重新配置 Key。不要把整个 `data/` 目录作为软件包分享。

## 启动、退出和端口

日常启动：`Start-CodeTop.cmd`。关闭最后一个 CodeTop 标签页后，服务约 5 秒内退出。重复启动会复用同目录、同数据目录的服务。

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

自动与命令行备份保存在 `data/backups/`，内容包括一致性数据库、来源文件、校验信息和代码历史，不包含 AI Key。不要只复制运行中的 `study.sqlite3` 文件。

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

服务日志位于 `runtime/server-*.log`、`runtime/server-*.err.log`。反馈问题时提供操作步骤与相关错误日志，隐藏个人数据和 Key。

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
