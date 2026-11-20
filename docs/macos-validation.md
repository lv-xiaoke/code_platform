# macOS 验收记录

当前多语言源码分支的最终三平台记录见 [多语言验收](multilanguage-acceptance.md)，CI [44676286322](https://github.com/lv-xiaoke/code_platform/actions/runs/44676286322) 已通过两种 Mac 实际 app 的五语言验证。下文保留 v1.6.0 已发布 Python 测试包的原始验收历史；多语言功能尚未发布到 Release。

## 当前交付状态

2026-11-20：Apple Silicon 在 macOS 15.8.2、Intel 在 macOS 15.7.9 的 GitHub 环境构建，通过两种架构各 **147 项后端测试**及打包应用冒烟测试；Windows 构建验证与三平台备份互通作业也全部通过。下载见 [v1.6.0-macos-test.1](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0-macos-test.1)，测试代码提交为 `14f4fcada270710193492fd0e4e28f312a8d498f`，证据见 [CI 44659301119](https://github.com/lv-xiaoke/code_platform/actions/runs/44659301119)。本测试版使用 ad hoc 签名，未使用 Developer ID，也未经过 Apple 公证。

| 验收项 | Apple Silicon | Intel |
| --- | --- | --- |
| 原生进程执行、资源采样、停止和子进程清理 | CI 通过 | CI 通过 |
| 系统钥匙串保存、读取、更新、访问拒绝 | 真实读写更新通过；拒绝授权待人工 | 真实读写更新通过；拒绝授权待人工 |
| 打包应用启动及 Unicode 样例 | 中文/空格路径及最小 PATH 通过 | 中文/空格路径及最小 PATH 通过 |
| 桌面版备份校验、恢复与重启 | 打包应用测试通过 | 打包应用测试通过 |
| Windows/Mac 真实双向备份交换 | 三个平台均恢复并逐表核对通过 | 三个平台均恢复并逐表核对通过 |
| Finder 双击、Safari/Chrome 多标签刷新及关闭 | 待实机操作 | 待实机操作 |
| 没有开发工具的干净电脑安装 | 待实机操作 | 待实机操作 |
| Developer ID 签名及 Apple 公证 | 本免费测试版不提供 | 本免费测试版不提供 |
| 最低 macOS 13 兼容性 | 待对应系统验证 | 待对应系统验证 |

Windows 上运行的模拟平台单元测试不能替代上表。

## Windows 上已执行的验证

- 最终完整 `scripts/verify.ps1`：后端 **138 项通过、32 项按平台或环境跳过**（44.92 秒）；前端 **34 项通过**；TypeScript 类型检查通过。包含冻结入口缓存测试及 Windows 原生执行回归。现有 Starlette/httpx 弃用提示保留，不影响本次测试结果。
- `scripts/build.ps1` 已更新本地发布，产物为 `releases/20261119-190056-6c0d65f5`。
- 从根目录 Start-CodeTop.cmd 启动独立端口 18061、隔离数据目录，健康检查返回 CodeTop 1.6.0 / schema 0003，题库 1,153 道；测试实例已停止。
- 另启动隔离端口 18062，确认 HTTP 200 页面内容与 current.json 指向的发布文件完全一致，之后按进程身份停止实例。
- 执行 `backup_exchange.py export` 与 `import`，合成数据的逐表内容摘要一致；未读取原有学习数据库。
- PyInstaller spec 语法和 Python 模块编译检查通过。Windows 无符号链接权限时，对应链接创建测试跳过；Mac 作业必须实际执行。
- 浏览器验收工具无法可靠识别 Windows Chrome 当前地址，UI 操作已停止；未将界面显示及实际关页退出标为已验收。

独立代码审查已完成。针对签名后字节码写入、相对验收目录、下载输入缓存、空 PATH 浏览器启动、SIGXCPU 分类、持管道的脱离子进程、首次运行记录平台及动态库解析补充修复和测试；对应 Mac 自动场景已通过，人工项目以上表为准。真实 CI 进一步修复了 Python 引导版本可用性、Windows 题库换行、动态库自身标识解析及恢复后 TIME_WAIT 端口复用问题。

实现选择：在原验收目录使用 codex/macos-support 功能分支，保留所有测试输出；固定 Python 下载及哈希，升级需审阅新输入；正式签名由配置了证书的 Mac 显式执行，CI 只产生 unsigned 测试包；两端共用 Python 前端构建入口，Windows 构建需要现有后端解释器。因平台模块共同变更，路径和启动恢复合并保存为一次提交。

## 自动验证

工作流 `.github/workflows/macos.yml` 为 Windows、macOS arm64、macOS Intel 分别运行后端测试、前端测试、前端构建并导出合成学习备份；随后在三个系统恢复并逐表比较数据库内容摘要。Mac 作业从固定来源下载 Python、校验 SHA-256 后构建 unsigned 测试 DMG，再复制应用到带中文及空格的路径运行。

手工运行安装包冒烟测试：

```bash
backend/.venv/bin/python scripts/verify_macos.py \
  --app '/absolute/path/CodeTop.app' \
  --report runtime/macos-smoke-report.json
```

报告包含系统版本、架构、程序哈希、真实执行项目、错误及仍待手工完成的项目。自动测试使用新的隔离数据目录，不修改现有学习数据；输出目录保留供排查。`passed: true` 只说明自动项目通过，不代表 Finder、浏览器或旧系统验收通过。

## 手工验收步骤

1. 在对应架构的新 Mac 用户或干净系统下载 DMG；核对 SHA-256 与签名状态，将应用拖入 Applications。无 Python、Node、Docker 时双击启动。
2. 检查题库包含 1,153 题，打开本地题面，保存中文笔记、进度、收藏、代码草稿及自定义样例，再退出重开。
3. 第一次运行确认本机执行说明。验证中文 input、EOF、停止、死循环、大量输出和内存增长；停止后不残留练习子进程。
4. 打开两个 CodeTop 标签，刷新其中一个、关闭其中一个，服务应继续；关闭最后一个，宽限期结束后服务应退出。分别在 Safari、Chrome 操作。
5. 配置专用测试 AI Key，验证重启后可读取；使用专用测试钥匙串或测试用户拒绝访问，界面应报明确错误，不写明文、不覆盖旧 Key。不要为了测试修改日常钥匙串访问策略。
6. 在 Windows 生成备份到 Mac 恢复，再反向恢复，核对笔记、收藏、进度、来源、样例及代码历史；AI Key 需重新配置。损坏备份恢复失败后原数据可继续使用。
7. 安装新版本后验证学习数据保留；移动应用目录后仍可启动。另在 macOS 13 实机或虚拟机重复关键流程，才能承诺该最低版本。

每次验收补充具体系统版本、架构、运行命令、产物及报告路径和结果；没有执行的项目保持“待验证”。
