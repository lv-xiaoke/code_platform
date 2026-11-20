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

| 你的电脑 | 下载 | 当前状态 |
| --- | --- | --- |
| Windows 10 / 11 x64 | [Windows 安装包 v1.6.0](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0) | 正式版 |
| Mac，Apple Silicon / M 系列 | [M 系列 DMG](https://github.com/lv-xiaoke/code_platform/releases/download/v1.6.0-macos-test.1/CodeTop-1.6.0-macos-arm64-unsigned.dmg) | 免费测试版，未经过 Apple 公证 |
| Mac，Intel 处理器 | [Intel DMG](https://github.com/lv-xiaoke/code_platform/releases/download/v1.6.0-macos-test.1/CodeTop-1.6.0-macos-x86_64-unsigned.dmg) | 免费测试版，未经过 Apple 公证 |

完整安装包已内置 Python、依赖与题库，**无需自行安装 Python、Node 或 Docker**。

### Windows 安装

1. 打开上方 Windows 下载页，下载 `CodeTop-Setup-*-windows-x64.exe` 安装包。
2. 双击安装包，按向导完成安装。
3. 双击桌面的 **CodeTop 刷题**，即可开始使用。

### Mac 安装

1. 按处理器类型下载上方对应的 DMG；不确定时，在苹果菜单“关于本机”查看“芯片”或“处理器”。
2. 打开 DMG，将 **CodeTop.app** 拖入 **Applications（应用程序）**。
3. 在应用程序中打开 CodeTop，默认浏览器会显示本地刷题工作台。

下载使用无需开通 Apple 开发者账号。当前为未公证的预发布测试版，首次打开可能被 macOS 拦截，请核对来源与校验文件，并参考 [Apple 官方打开 App 的说明](https://support.apple.com/zh-cn/102445)。[Mac Release](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0-macos-test.1) 附有 SHA-256 和测试报告；双架构已通过 macOS 15 CI，Finder、浏览器界面及旧系统兼容性仍需实机反馈，详见[验收记录](docs/macos-validation.md)。

两端均默认只在本机运行；关闭最后一个 CodeTop 标签页后，服务会自动退出。源码安装和开发启动见[部署说明](docs/deployment.md)。

## 数据、备份与更新

学习数据库、笔记、代码历史、自动备份和日志的位置取决于安装方式：

| 安装方式 | 默认数据目录 |
| --- | --- |
| Windows 完整安装包 | `%LOCALAPPDATA%\CodeTopLocal` |
| Mac DMG 应用 | `~/Library/Application Support/CodeTopLocal/` |
| 源码 / 旧 Windows 体验 ZIP | 项目目录的 `data/` |

完整安装包的程序文件与用户数据分开存放；源码方式可通过 `CODETOP_DATA_DIR` 指定数据目录。

- **备份与迁移**：页面“设置 → 完整备份”生成并下载备份；完整应用支持在页面恢复，Windows 与 Mac 之间可以迁移学习记录。源码版的命令行操作见部署说明。
- **升级**：升级前先备份。换电脑或更换数据目录时，使用完整备份恢复；AI Key 不随备份迁移，需要重新配置。
- **离线使用**：完整应用的内置题库、笔记、进度和本机 Python 练习可离线使用；AI、外部原题需要联网。选择 Docker 开发模式时，需另行准备镜像。

恢复步骤、换端口、日志位置和故障处理见[部署说明](docs/deployment.md)。

## 开发与生成体验包

技术栈：React + TypeScript + Vite、FastAPI + SQLAlchemy + SQLite，Python 代码支持本机执行和可选的 Docker 模式。

完整应用用独立 CPython 子进程运行代码：Windows 使用 Job Object，Mac 使用进程组与 RSS 采样管理资源。本机模式以当前用户权限执行，仅运行自己信任的练习代码。维护者构建见 [Windows 安装包](docs/deployment.md#维护者构建完整桌面安装包)和 [Mac DMG](docs/deployment.md#构建-codetopapp-和测试-dmg)。

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
