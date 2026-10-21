# CodeTop Local

Windows 单机刷题工作台。题库、笔记、代码、掌握程度、练习历史和复习安排保存在本机 SQLite 中。

项目根目录是 `D:\my_develop\A_work_program\code_platform`，覆盖原设计文档中的建议部署路径。原设计文件保持原样。

## 日常使用

双击根目录的 **`Start-CodeTop.cmd`**，浏览器打开 **http://127.0.0.1:8000**。也可以运行：

```powershell
.\scripts\start.ps1
```

启动脚本按自身位置定位应用，与终端当前目录无关。相同应用已经运行时会打开已有页面；端口被其他程序占用时会明确报错。服务仅监听本机回环地址，一个 worker；日常运行不需要 Vite、Node 或 Bun。

- **题库**：公司、部门、岗位、标签、难度、题集、掌握程度、练习状态、收藏和最近考察筛选；搜索题号或标题。
- **题目详情**：查看本地题面或打开原题；记录独立完成、使用提示、查看答案、未完成；保存用时、代码、收藏和掌握程度。
- **ACM 编程 / 运行**：直接写完整 Python 程序，填写 stdin 和可选期望输出，在本地 Docker 中运行；保存多组自定义测试，查看逐组结果、错误和历史代码。
- **编辑笔记**：沿用上游 CodeMirror Markdown 编辑器和预览。停止输入约 700 ms 后保存，显示等待保存、保存中、已保存或失败。关闭详情前会完成待保存内容。
- **笔记冲突**：保留当前草稿并提示，不覆盖其他页面的内容。可以先导出草稿，再载入服务器版本并合并。
- **今日复习**：按 Asia/Shanghai 日期显示已到期且未暂停的题目。间隔为 1、3、7、14、30 天；同日成功不重复升级，非独立完成会重置并安排次日复习。掌握标记由你单独维护。
- **全部历史题目**：可找到新快照中已不再出现的旧题及其个人记录。
- **数据与备份**：预览和应用导入、生成并下载完整备份、切换来源版本。

关闭服务：

```powershell
.\scripts\stop.ps1
```

日志保存在 `runtime/server-*.log`、`runtime/server-*.err.log`。运行错误时先查看对应日期的错误日志。

## 题库与统计口径

首批固定快照含 **1,153 道题、21,906 条范围统计**，生成于 **2026-07-18**。页面同时显示来源生成日期与本机导入日期。来源、提交、哈希、依赖版本记录于 `environment.json`。

首页默认按 overall 累计频次排序；选择公司、部门或单独岗位时使用该维度频次。公司或部门与岗位共同选择时取题目交集，频次仍按公司或部门统计。标签与难度只过滤，不累计频次。“最近三个月考察过”根据来源最近时间过滤，显示的仍是累计频次。

快照有 21 道题缺少题面、7 道题缺少 URL；保留空值，不猜测地址。另外有一个部门引用来源未提供的公司编号 15，界面明确显示“来源未提供公司（15）”，原关联编号保留；该内部占位不计入原始 22 家公司的数量。

安装完成后，已有文字题库、笔记、历史、复习可以离线使用；Docker 镜像已安装时，本地 Python 运行也可离线使用。原题网站和题面外链图片仍需网络。

## Python ACM 练习

打开题目，点击 **ACM 编程 / 运行**。代码需要自行读取 `input()` / `sys.stdin` 并向 stdout 输出，写成可以直接启动的完整程序。填写“标准输入 stdin”后运行；勾选“校验期望输出”可比较结果，不勾选则只观察输出。已勾选但内容为空时会校验空输出。

测试输入草稿与“我的测试”会自动保存。点击“保存为测试用例”加入测试集，再用“运行全部测试”运行题目样例与自己的测试；最多保存 16 组自定义测试，每次最多运行 20 组。支持忽略空白、严格文本、忽略行顺序和浮点容差比较。运行结果保存完整代码、输入、实际输出、stderr、状态和耗时，历史入口显示最近 20 次。

首批参考实现覆盖固定快照 overall 前 **50 道题**，含补充题。展开“查看完整 Python 参考实现”可阅读完整代码、思路、复杂度与本地 ACM 输入输出约定；可以复制或独立运行参考实现，运行参考实现不会替换自己的代码。其余题目也能编程和自定义测试，尚未附参考实现与内置样例。参考实现为本项目编写，152 组本地样例已在固定镜像验证；这些结果不等同于原平台隐藏测试的 AC。运行不会自动记录为练习完成或改变掌握程度。

需要 Docker Desktop 已启动并使用 Linux 容器。首次准备运行镜像：

```powershell
.\scripts\setup-runner.ps1
```

固定镜像及限制记录在 `backend/runner/runtime.json`，当前实际 Python 版本为 3.12.15。每组限制 2 秒、256 MiB、stdout/stderr 合计 64 KiB；容器禁网、只读根目录、非 root 用户，只挂载该次运行文件和监督程序。运行器不可用时网页显示原因和重新检查入口，笔记、题库仍可使用。运行文件位于 `data/runs/<运行编号>`，全部保留。

## 备份和恢复

页面“数据与备份 → 生成并下载完整备份”或：

```powershell
.\scripts\backup.ps1
```

备份 ZIP 包含一致性 SQLite 快照、引用的原始来源文件、来源版本清单、记录数、应用/结构版本和 SHA256。每日首次启动以及题库导入、版本切换、恢复前会自动备份。备份位于 `data/backups`，全部保留。

恢复本应用备份：

```powershell
.\scripts\restore.ps1 -Archive "D:\backup\your-backup.zip"
```

脚本核对本应用进程身份后停止服务；再校验路径、哈希、数据库完整性、外键、结构版本与记录数。当前数据库会先备份，并保留为 `data/study-before-restore-<唯一编号>.sqlite3`。恢复失败时回退，成功后重新启动。应用使用 OS 文件锁阻止服务运行时恢复。

要在独立目录试恢复：

```powershell
.\scripts\restore.ps1 -Archive "D:\backup\your-backup.zip" -DataDir "D:\my_develop\A_work_program\code_platform\runtime\trial-restore" -NoRestart
```

当前备份结构版本为 `0002`，包含测试草稿、测试集和完整运行历史。运行目录为冗余产物，恢复历史无需依赖这些目录。仍支持恢复旧版 `0001` 备份，并在下次启动自动升级。不要直接替换运行中的 `study.sqlite3`，也不要只复制 WAL 模式下的主文件作为备份。

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

已准备项目专用 Python 3.12 虚拟环境，以及本地 Node 24 / Bun。重装需要网络、系统可用的 `uv` 与 `npm`：

```powershell
.\scripts\setup.ps1
```

后端完整依赖锁：`backend/requirements.lock.txt`；前端锁：`frontend/bun.lock`；构建工具锁：`tools/package-lock.json`。上游原锁文件、源码和 MIT 许可证保留于 `vendor/algoTop-main`，固定提交归档也保留。

开发时先启动后端，再运行前端：

```powershell
.\scripts\start.ps1 -NoBrowser
cd frontend
..\tools\node_modules\bun\bin\bun.exe run dev
```

Vite 只监听 `127.0.0.1:5173`，将 `/api` 代理至后端。同源写入通过本机会话令牌校验。生产前端由 `src/main.tsx` 加载 `src/local/LocalApp.tsx`，原上游 `App.tsx` 保留为参考。

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

当前 ACM 增量验证记录见 `docs/acm-acceptance.md`，方案、计划与过程记录见 `docs/superpowers/specs/2026-10-21-python-acm-design.md`、`docs/superpowers/plans/2026-10-21-python-acm.md`、`docs/acm-progress.md`。原版本验证和实施记录保留于 `docs/acceptance.md`、`docs/progress.md`。
