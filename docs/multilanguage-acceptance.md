# 多语言实现与验收

当前工作分支：`codex/multilanguage`。功能尚未发布到 GitHub Release，已有 v1.6.0 下载包仍为 Python 版本。

## 已实现

- Python 3.12、C17、C++17、Java 21、Node.js 24 单文件编译/运行、输入输出样例和管道交互。
- 每次作业 UUID 独立目录，批量样例只编译一次；编译诊断、运行输出、阶段和版本分开记录。
- 按需工具链、固定哈希、并发准备、取消、失败保留、Mac CLT 检查和各语言环境面板。
- schema 0004 独立草稿、独立 Markdown revision、历史恢复和语言偏好；旧数据与旧备份升级。
- 多语言 CodeMirror、切换前停止和保存、冲突保留输入、语言感知请求签名与 AI 运行上下文。

## 本地验证记录

Windows x64：官方 Node 24.22.3、Temurin 21.0.13+9、LLVM-MinGW 20261117 已下载、核验 SHA-256 并完成基础编译运行。工具链测试根为仓库 `runtime/toolchains-ci`，未改写全局环境或用户学习数据。

本地最终自动检查：后端 **195 passed / 33 skipped**；前端 **48 passed**，TypeScript 检查及 `scripts/build.ps1` 成功。后端跳过项主要为 Mac 专属能力、Docker 真实环境及 Windows 无符号链接权限的测试；跳过不代表该平台已验收。跨平台 CI 报告在本次实现验证结束时补充。

真实五语言测试已覆盖 Unicode、多样例、编译一次、交互 stdin/EOF、编译失败、停止及编译期间关闭。五语言超时、内存和输出限制真实用例全部通过，计入上述全量结果。

普通入口 `Start-CodeTop.cmd -NoBrowser` 已通过独立数据验证：schema 0004、五语言多样例、交互 Unicode/EOF、C/C++/Java 编译错误；HTTP 返回的页面与当前 release HTML 字节一致。此项不代表浏览器点击和视觉验收。

## 自动验证入口

```powershell
scripts/verify.ps1
scripts/build.ps1
```

首次执行语言集成测试前，使用 `scripts/prepare_toolchains.py` 准备测试根。`CODETOP_TEST_TOOLCHAINS` 可指定该根；`CODETOP_REQUIRE_LANGUAGES=1` 使必需环境缺失变成失败。HTTP 验证使用独立数据目录，避免向个人学习库写入测试运行：

```powershell
Start-CodeTop.cmd -Port 18071 -DataDir runtime/multilanguage-entry-check -NoBrowser
backend/.venv/Scripts/python.exe scripts/multilanguage_smoke.py --base-url http://127.0.0.1:18071 --data-dir runtime/multilanguage-entry-check --require-all --report runtime/multilanguage-entry-report.json
```

验收进程需设置 `CODETOP_TOOLCHAINS_DIR` 为已准备的测试根。`-NoBrowser` 验证启动入口和本地 HTTP 流程；浏览器实际点击、布局与关页行为须另记人工结果，不能用 HTTP 成功代替。

CI 的 `Desktop languages and backup exchange` 在 Windows、Mac arm64、Mac Intel 三个平台准备工具链、运行后端/前端、交换包含多语言草稿与记录的 0004 备份。Mac 还从实际构建的 app 验证五语言编译、运行、交互和恢复重启。

## 仍需单独记录的人工验收

浏览器内语言切换、CodeMirror 焦点、环境面板布局、真实连续点击；Finder/Gatekeeper、干净机器安装、钥匙串授权与 macOS 13。当前聊天无法进行可靠的浏览器 CUA 验收，因此这些项目仍标为未执行。

工具链版本及哈希的官方来源见 [固定清单](../packaging/toolchains.json)，Mac 包原有边界见 [Mac 验收](macos-validation.md)。
