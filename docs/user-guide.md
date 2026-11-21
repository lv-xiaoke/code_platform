# CodeTop Local

macOS：[免费测试版下载](https://github.com/lv-xiaoke/code_platform/releases/tag/v1.6.0-macos-test.1)提供 M 系列和 Intel 安装包，未经过 Apple 公证。安装与构建见[部署说明](deployment.md#macos-构建与使用)，自动测试与待人工验证项目见[验收记录](macos-validation.md)。源码模式可通过 `bash scripts/start-macos.sh` 启动，`--no-browser` 常驻；完整应用通过 Finder 双击启动，学习数据位于用户 Application Support 目录。

简洁的本机高频刷题题单：筛选题目、本地读题与 ACM 练习、标记进度、记录笔记。已发布 **1.6.0** 安装包支持 Python、数据库为 **0003**；当前多语言源码分支数据库为 **0004**，尚未发布新安装包。完整桌面版内置本机 Python，无需 Docker；本文中容器准备与隔离说明仅适用于显式 Docker 模式。

文中命令默认在你自己的项目根目录运行。首次安装和故障处理见[部署说明](deployment.md)。

## 多语言练习（当前源码）

选择 Python、C、C++、Java 或 JavaScript。Python 使用内置环境，其他语言在“语言环境”中按需准备；Mac C/C++ 缺少 SDK 时按 Apple 官方说明安装 Command Line Tools。准备失败可重试，选择语言不会自行下载。

每题每种语言各有一份草稿，切换前会停止运行并保存；保存冲突时停留原语言，可先导出草稿再重新载入。空白已存草稿不会被模板替换。Markdown 笔记按题共享，输入输出用例也按题共享。“重新编写”只归档当前语言；历史可按当前语言筛选，载入其他语言历史会切换到对应语言并保留其他草稿。

C/C++ 请使用标准头文件；Java 入口为无 package 的 Main；Node.js 运行 CommonJS JavaScript，不能使用浏览器 DOM。程序读取 EOF 时点击“结束输入”，交互提示需要主动刷新输出。编译诊断与运行输出分开显示，停止按钮在编译期间同样有效。详细预算和暂不支持的工程能力见 [README](../README.md#多语言练习当前源码待发布)。

## 日常使用

按安装方式启动：

| 安装方式 | 启动入口 | 默认数据目录 |
| --- | --- | --- |
| Windows 完整安装包 | 桌面“CodeTop 刷题” | `%LOCALAPPDATA%\CodeTopLocal` |
| Mac DMG | Applications 中的 CodeTop.app | `~/Library/Application Support/CodeTopLocal/` |
| Windows 源码 / 旧体验 ZIP | 根目录 Start-CodeTop.cmd | 项目 `data/` |
| Mac 源码 | `bash scripts/start-macos.sh` | 项目 `data/` |

Windows 源码入口也可运行：

```powershell
.\scripts\start.ps1
```

默认浏览器会打开本地工作台，通常为 `http://127.0.0.1:8000`；完整应用在端口占用时可选择其他本机端口。关闭最后一个 CodeTop 标签页后，本地服务会在约 5 秒后退出。服务仅监听本机回环地址；完整安装包日常使用无需 Python、Node、Bun 或 Docker。

- **筛选**：搜索题号/标题，公司、部门、岗位、标签、难度、最近考察、排序。切换公司会清空旧部门，并显示该公司的部门。
- **排序**：默认频次从高到低，也支持频次从低到高、最近考察优先、题号排序。
- **最近考察**：不限、最近三个月、最近半年；按 Asia/Shanghai 当前日期与来源最近考察日期筛选。
- **本地练习**：点击题目名称打开宽幅练习面板，左侧显示本地题面、原题示例或 Markdown 笔记，右侧编写完整 Python ACM 程序。默认占满窗口，可还原，手机通过“题目／代码与测试／笔记／AI 助教”页签切换，输入内容继续保留。题名旁的独立外链图标仍在新标签页打开原题；缺少链接时明确提示。
- **交互运行**：在编辑器中编写完整 Python 程序，点击“运行”后，`input()`、`sys.stdin.readline()` 会等待终端输入。输入后按 Enter 或点击“发送”，支持连续输入；Shift+Enter 可换行。`sys.stdin.read()` 需要点击“结束输入”才会读完。无需输入的函数调用、`print(...)` 和 `assert ...` 也可以直接运行。终端增量显示输出、提示和错误；“停止”或关闭练习会终止程序。输入与输出保存在原有运行历史和完整备份中。
- **重新练习与历史代码**：代码区可切换“当前练习 / 历史代码”。点击“重新编写”先保存草稿，再将非空代码归档并清空编辑器；空白代码不生成历史。历史按保存顺序倒序显示时间和语言，默认只读，可复制或载入到当前练习；载入前也会归档当前非空代码。查看历史不改变当前草稿，归档失败时保留草稿。已有代码继续作为当前练习保留，首次重写时进入历史；历史代码随完整备份保存。
- **预设输入与高级测试**：需要提前提供一次性 stdin 时展开“预设输入”。在“高级测试”里可填写标准输入和可选的期望输出，保存、编辑多组样例，并点击“一键测试全部”运行本题已保存的自定义样例。
- **运行环境与保存**：Windows 安装包与 Mac DMG 已内置 Python，直接使用本机执行器；首次运行前确认文件与网络访问说明。当前源码默认本机模式；显式选择 Docker 时需要 Docker Desktop 和固定 Python 镜像。代码、笔记与测试草稿自动保存，关闭前完成保存，失败会保留面板。交互终端最多同时运行两个，允许等待输入至 5 分钟，累计计算 CPU 约 3 秒，Python/C/C++ 内存目标 256 MiB，Java/JavaScript 为 512 MiB，输入/输出各 64 KiB；批量测试保持每组 2 秒。Mac 的内存限制通过 RSS 采样监测，可能短暂超出阈值。本机模式以当前用户权限执行，不提供文件/网络隔离；Docker 模式保持禁网、非 root 隔离。运行不自动标记已做。
- **题面与样例**：当前 1,153 道题中有 1,132 道含本地题面，其余提示暂缺。原题示例仍随题面展示；本地测试通过不等同于原题平台隐藏测试 AC。
- **进度与收藏**：表格直接勾选已做/取消已做、切换收藏；可切换全部、未做、已做、收藏视图。手动标记不会创建练习记录或安排复习。已有练习记录默认显示为已做，手动取消只改变题单标记，保留原记录。
- **笔记**：点击每行的笔记按钮打开右侧面板，支持 Markdown 编写、预览、导出。停止输入约 700 ms 自动保存，关闭前完成保存；保存失败保留草稿并提供重试、导出和冲突恢复。
- **设置**：题库来源选择、导入预览、版本切换、完整备份与恢复说明统一放在设置中。

首页保持精简题单，练习面板按需打开。界面不展示复习安排、掌握程度、统计卡片或热力图。原有笔记、代码、练习/复习记录、测试集与运行历史继续保留并参与完整备份；原界面与参考程序文件也保留。

完整应用关闭最后一个标签页即可退出。Windows 源码/体验 ZIP 也可手动停止：

```powershell
.\scripts\stop.ps1
```

完整应用日志位于上表用户数据目录的 `logs/` 下；Windows 源码/体验 ZIP 的启动日志保存在项目 `runtime/server-*.log`、`runtime/server-*.err.log`。

## 题库与统计口径

首批固定快照含 **1,153 道题、21,906 条范围统计**，生成于 **2026-07-18**。界面显示生成日期；这是固定快照的累计频次，不是实时排名。已有题库、笔记、进度可以离线使用；LeetCode 与其他原题网站需要网络。

选择公司或部门时使用该维度的累计频次；公司/部门与岗位共同选择时取题目交集，频次仍按公司/部门统计。标签、难度和最近考察只过滤，不累加频次。手工来源评分与 CodeTop 累计次数分别标注。

少量补充题没有 LeetCode 地址或未提供原题链接。来源中一个部门引用了未提供的公司编号 15，显示“来源未提供公司（15）”，原关联编号保留。

## 备份和恢复

两端均可从页面“设置 → 完整备份 → 生成并下载完整备份”。Windows 源码/体验 ZIP 也可运行：

```powershell
.\scripts\backup.ps1
```

备份 ZIP 包含一致性 SQLite 快照、引用的原始来源文件、来源版本清单、记录数、应用/结构版本和 SHA256。每日首次启动以及题库导入、版本切换、恢复前会自动备份。备份位于当前数据目录的 `backups/` 下，全部保留；源码默认是项目 `data/backups/`。Windows 与 Mac 之间可恢复同一格式的学习备份，AI Key 需要在新设备重新配置。

完整应用在页面“设置 → 完整备份”上传文件，校验预览后确认恢复，服务会重启。Windows 源码/体验 ZIP 使用以下恢复命令：

```powershell
.\scripts\restore.ps1 -Archive "D:\backup\your-backup.zip"
```

脚本核对本应用进程身份后停止服务；再校验路径、哈希、数据库完整性、外键、结构版本与记录数。当前数据库会先备份，并保留为数据目录下的 `study-before-restore-<唯一编号>.sqlite3`。恢复失败时回退，成功后重新启动。应用使用 OS 文件锁阻止服务运行时恢复。

要在独立目录试恢复：

```powershell
.\scripts\restore.ps1 -Archive "D:\backup\your-backup.zip" -DataDir ".\runtime\trial-restore" -NoRestart
```

当前源码备份结构版本为 `0004`，包含全部语言草稿、语言偏好、共享笔记、代码历史、测试草稿、测试集和完整运行历史；已发布 v1.6.0 使用 `0003`。运行目录为冗余产物，恢复历史无需依赖这些目录。仍支持恢复旧版 `0001` / `0002` / `0003` 备份，并在下次启动自动升级；结构升级前自动备份。不要直接替换运行中的 `study.sqlite3`，也不要只复制 WAL 模式下的主文件作为备份。

## 导入和迁移

AlgoTop JSON：选择格式、来源名称 `algotop` 和本地快照，检查预览再应用。同一来源、同一哈希返回已有版本；更新只写题库内容，不修改个人笔记、练习和学习状态。旧来源版本保留并支持切换。

手工 CSV/JSON：使用另一个来源名称，例如 `my-list`。CSV 至少包含：

```csv
platform,display_id,title,difficulty,url,tags,collection,frequency
leetcode,3,无重复字符的最长子串,medium,https://leetcode.cn/problems/longest-substring-without-repeating-characters/,字符串|滑动窗口,面试准备,
```

难度接受 `easy/medium/hard`、`简单/中等/困难`、`1/2/3`。JSON 使用对应字段的题目数组。可选 `source_record_id` 用于非标准题号的稳定身份；`content_html` 可补充题面。手工频率保持 `source_score` 原值，与 CodeTop 累计次数分别展示。

跨来源仅对常规力扣数字题号自动关联；补充题和外链保留独立身份。相似标题出现于预览时，可明确选择关联或保留独立身份。slug 不是题目的全局唯一标识。

旧版 AlgoTop 学习数据：先在**原页面所在浏览器来源**导出 JSON，再选择“旧版 AlgoTop 学习数据”预览。按来源内部题号迁移，无法匹配的编号会显示；本地已有不同笔记时取消迁移以保留两份内容。旧浏览器数据不会被修改。旧版完成标记记为迁移记录，不推测旧练习日期或重排复习。

账号、云同步、在线抓取和独立第三方公司 CSV 适配器不属于这一版本；不要将其他来源的百分比与累计次数混用。

## 开发与重装

源码安装会准备项目专用 Python 3.12 虚拟环境和本地 Node 24 / Bun。源码重装需要网络、系统可用的 `uv` 与 `npm`；Windows 体验包只需 uv，不包含前端开发工具：

```powershell
.\scripts\setup.ps1 -BuildFromSource
```

后端完整依赖锁：`backend/requirements.lock.txt`；前端锁：`frontend/bun.lock`；构建工具锁：`tools/package-lock.json`。上游原锁文件、源码和 MIT 许可证保留于 `vendor/algoTop-main`，固定提交归档也保留。

开发时先启动后端，再运行前端：

```powershell
.\scripts\start.ps1 -NoBrowser
cd frontend
..\tools\node_modules\bun\bin\bun.exe run dev
```

Vite 只监听 `127.0.0.1:5173`，将 `/api` 代理至后端。同源写入通过本机会话令牌校验。生产前端由 `src/main.tsx` 加载 `src/local/CatalogApp.tsx`。原工作台 `LocalApp.tsx`、题目详情与执行器源码保留。

```powershell
.\scripts\verify.ps1
.\scripts\build.ps1
```

完整 Docker 和参考实现验收（需要运行镜像）：

```powershell
$env:CODETOP_DOCKER_TESTS='1'
$env:CODETOP_REFERENCE_TESTS='1'
.\scripts\verify.ps1
```

常规验证包含后端测试、前端请求重试测试与 TypeScript 检查。上述两个环境变量额外启用实际容器边界测试和全部参考程序验证。测试产物保留在 `runtime/tests`。

构建写入新的 `releases/<版本>`，成功后原子切换 `releases/current.json`，旧产物保留；旧页面引用的哈希资源仍可访问。需回退前端时，停止服务，将 `current.json` 的 `path` 改为保留版本目录，再启动。

目录说明：`backend/app` 业务服务；`backend/migrations` Alembic 迁移；`frontend/src/local` 本地界面；`data` 正式数据；`runtime/acceptance*` 独立验收数据；`runtime/tests` 测试产物。验收数据没有写入正式学习库。

**不提供批量清理脚本。原始快照、备份、回退文件、测试目录和旧发布全部保留；需要批量清理时由你手工操作。**

交互终端验证记录见 `docs/interactive-terminal-acceptance.md`；简化运行区验证记录见 `docs/quick-run-acceptance.md`；本地练习验证记录见 `docs/local-practice-acceptance.md`；精简界面验证记录见 `docs/simple-ui-acceptance.md`。原版本与 ACM 增量的设计、计划、验收和执行记录均保留在 `docs` 下。

## 随题 AI 助教

打开题目默认占满窗口，左侧“AI 助教”可结合题面和当前代码提问，右侧继续编辑和运行。首次在“设置”或助教内的“AI 设置”填写 DeepSeek Key，保存并测试连接。支持逐步提示、样例解释、代码/报错分析、停止与重试、代码复制、追加笔记；运行结果旁可一键分析原次提交。聊天按题目本地保存。Key 在 Windows 使用 DPAPI 加密保存在数据目录，在 Mac 存入系统钥匙串，其他系统保存为仅当前用户可读的本地文件，均不进入学习备份。

接口按 [DeepSeek 官方文档](https://api-docs.deepseek.com/) 接入。真实账户连接需要填写自己的 Key 后测试；界面截图不代表已经验证你的账户。
