# CodeTop Local

**把高频选题、本地读题、Python 练习、笔记和 AI 助教放在一起的个人刷题工具。**

准备算法面试时，按目标公司、部门、岗位和考察频次筛题，在浏览器里直接读题、写代码、记笔记，学习记录保存在自己的电脑上。

[快速开始](#快速开始) · [部署与常见问题](docs/deployment.md) · [详细使用手册](docs/user-guide.md) · [第三方来源](THIRD_PARTY_NOTICES.md)

## 能帮你做什么

| 你想做的事 | CodeTop Local 提供的功能 |
| --- | --- |
| 找到值得优先练的面试题 | 按公司、部门、岗位、标签、难度、最近考察筛选，按累计频次排序 |
| 把刷题过程集中在一处 | 本地题面、代码编辑、交互终端、自定义样例和代码历史 |
| 留住自己的学习积累 | 已做标记、收藏、Markdown 笔记、草稿自动保存、完整备份与恢复 |
| 卡住时获得提示 | 可选 DeepSeek AI 助教，结合题面和代码解释样例、分析报错、给出提示 |
| 使用自己的题单 | CSV / JSON 导入预览、题库来源和版本切换 |

内置固定快照包含 **1,153 道题**，其中 **1,132 道有本地题面**。数据生成于 **2026-07-18**，展示的是来源快照的累计频次，不是实时排名。

## 界面预览

**高频题单：筛选、进度、收藏和笔记**

![CodeTop 高频题单](docs/simple-ui.jpg)

**练习与随题 AI 助教**

![CodeTop 练习和 AI 助教示例](docs/ai-tutor-preview.png)

AI 截图用于展示交互效果；实际回答需要自行配置 Key 并联网。

## 快速开始

当前部署面向 **Windows 10 / 11 x64**，使用现代浏览器。不需要单独安装数据库。

### 方式一：Windows 体验包（推荐）

1. 从仓库的 [Releases 页面](https://github.com/lv-xiaoke/code_platform/releases)下载 `CodeTop-Local-Windows-*.zip`，完整解压到你准备长期保存的目录，例如 `D:\Apps\CodeTop-Local`。请选择这个体验包；GitHub 自动生成的 `Source code.zip` 是下面的源码方式。若尚无发行附件，可先按方式二安装。
2. 打开 PowerShell，先运行 `uv --version`。如果能看到版本号，说明已安装，直接进入第 3 步；只有提示找不到命令时，才需要安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)。可运行官方提供的 WinGet 安装命令：

   ```powershell
   winget install --id=astral-sh.uv -e
   ```

   安装后重新打开终端。无需自己安装 Python，安装脚本会通过 uv 准备 Python 3.12。
3. 双击解压目录中的 **`Setup-CodeTop.cmd`**，等待依赖安装和题库初始化完成。首次安装需要网络；体验包已带前端页面，无需 Node、npm、Bun 或 Docker。
4. 双击 **`Start-CodeTop.cmd`**，浏览器会打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。看到题单即可开始使用。

以后只需双击 `Start-CodeTop.cmd`。关闭最后一个 CodeTop 标签页后，服务约 5 秒内退出。

### 方式二：从源码安装

需要 **uv、Node.js（含 npm）**；克隆仓库需要 Git，也可以下载源码 ZIP 后解压。

```powershell
git clone https://github.com/lv-xiaoke/code_platform.git
cd code_platform
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -BuildFromSource
.\Start-CodeTop.cmd
```

脚本创建项目专用 Python 3.12 环境，按锁文件安装依赖、导入内置题库并构建前端。首次准备好之后，日常启动无需再运行 Node 或 Bun。

### 按需开启更多能力

| 功能 | 额外准备 |
| --- | --- |
| 筛题、查看本地题面、标记进度、收藏、笔记和代码编辑 | 完成上述安装即可 |
| 运行 Python、交互输入和自定义样例测试 | 安装并启动 Docker Desktop（Linux 容器），执行下方命令准备运行镜像 |
| AI 助教 | 在页面“设置 → AI 设置”填写自己的 DeepSeek API Key，保存并测试连接 |

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-runner.ps1
```

代码运行在禁网、非 root 的隔离容器中。编辑器使用 Python ACM 风格：编写读取标准输入、输出结果的完整程序。本地样例通过不等于原题平台隐藏测试 AC。

AI 会将你选中的题面、代码、问题等上下文发送给 DeepSeek，调用费用由自己的账户承担。Key 使用 Windows 加密存储，不随学习备份导出。

## 数据、备份与更新

学习数据库、笔记、代码历史和自动备份保存在项目目录的 `data/` 中。初始化重复执行会保留已有学习数据。安装目录内会持续产生数据，请放在可写的本地目录。

- **备份**：页面“设置 → 完整备份”，或运行 `scripts/backup.ps1`。
- **升级**：先生成完整备份，在新目录安装新版，再恢复备份；AI Key 需要重新配置。
- **离线使用**：首次安装完成后，内置题库、笔记、进度可离线使用；运行代码需已准备好 Docker 镜像；AI、外部原题和下载依赖需要联网。

恢复步骤、换端口、日志位置和故障处理见[部署说明](docs/deployment.md)。

## 开发与生成体验包

技术栈：React + TypeScript + Vite、FastAPI + SQLAlchemy + SQLite，Python 代码通过 Docker 运行。

在源码安装完成后，于项目根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\package-release.ps1
```

第二条命令重新构建页面，在 `dist/` 生成 Windows ZIP 和 `.sha256` 校验文件。打包仅收录程序、当前前端构建、内置题库与文档，不携带本机学习库、Key、虚拟环境、日志或旧发布。体验包不是免安装离线包，首次使用仍需 uv 和网络。

开发服务器、测试选项和目录结构见[详细使用手册](docs/user-guide.md#开发与重装)。

## 来源与使用范围

项目面向个人本机学习，默认只监听 `127.0.0.1`，不提供账号、云同步或多人公网服务部署。

题库快照及部分前端代码来自 [AlgoTop](https://github.com/dogxii/algoTop)，上游采用 MIT 许可证；题目及原题链接保留其来源信息。详见[第三方来源与许可说明](THIRD_PARTY_NOTICES.md)。
