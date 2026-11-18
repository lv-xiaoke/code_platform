# 2026-11-18 发布整理验收

## 交付范围

- 中文 README：定位、功能对照、截图、体验包和源码快速开始、Docker / AI 可选配置。
- 首次安装入口 `Setup-CodeTop.cmd`，日常入口 `Start-CodeTop.cmd`；后者支持转交 `-Port` 等启动参数。
- 源码完整安装与体验包 RuntimeOnly 安装。两者使用 Python 3.12 和后端锁文件，重复初始化保留已有数据。
- 通过白名单生成 Windows ZIP 和 SHA256，不携带数据库、Key、日志、虚拟环境和旧构建。
- 题库快照不再被 Git 忽略；只有 canonical 快照 `vendor/algoTop-main/public/data/codetop.json` 需要纳入版本控制，其余上游重复副本继续忽略。

## 验证结果

1. `scripts/verify.ps1`：**85 个后端测试通过，20 个可选测试跳过；32 个前端测试通过；TypeScript 检查通过**。其中 9 个发布回归测试覆盖题库收录、打包内容、私密数据排除、缺失文件、路径越界、重复输出和中文健康接口。依赖现有一条 FastAPI / Starlette TestClient 弃用警告仍会显示。
2. `scripts/build.ps1`：成功构建并切换根目录当前发布。
3. `scripts/package-release.ps1 -SkipBuild`：成功生成 ZIP 与 SHA256。SHA256 独立复核与校验文件一致。
4. 将体验 ZIP 解压至 `runtime` 下的**中文与空格路径**：从零创建独立 Python 环境、下载并安装后端依赖、导入 1,153 道题；没有安装前端工具。
5. 经该目录 `Start-CodeTop.cmd -Port 8018` 启动：返回 ready，在浏览器显示 1,153 道题；本地练习面板成功加载题面和代码区。数据只写入独立验收目录。
6. 真实 HTTP 检查：首页及所引用哈希资源返回成功；题库接口返回 1,153 道题；Windows PowerShell 5 健康检查得到的中文目录与实际路径一致。
7. 自动退出：在独立端口 8019 启动同一应用，建立唯一浏览器 WebSocket，再关闭连接，服务在等待窗口内正常退出（退出码 0）。8018 验收浏览器存在重连，因此该端口在检查后由停止脚本结束，未将其误判为自动退出失败。
8. 由 `git ls-files --cached --others --exclude-standard` 得到可分发文件，复制到全新源码目录。执行 `setup.ps1 -BuildFromSource`，完成 Python 环境、npm 工具、Bun 冻结依赖、题库初始化及 Vite 构建。未复用项目的 `.venv`、`node_modules` 或 `releases`。
9. 独立只读审查未发现重要问题，`git diff --check` 通过。

## 本次修复的首次部署问题

- 原 `.gitignore` 的 `data/` 会忽略 vendor 内置题库，导致新克隆缺少初始化输入；改为根目录范围，并显式忽略重复题库副本。
- 原安装脚本只在虚拟环境缺失时检查 uv，已有环境却未安装 uv 时提示不清；改为安装前统一检查，并区分源码与预构建模式。
- Windows PowerShell 5 默认将未声明编码的 JSON 解码为 ANSI，中文路径在健康检查中不相等；健康接口显式返回 `application/json; charset=utf-8`。该问题已先用失败测试复现，再修复，并在真实 PowerShell 中验证。

## 边界

- 这是同一 Windows 主机的独立目录验收，不是全新 Windows 虚拟机验收。
- 首次依赖下载需要网络和 uv；源码方式另需 Node.js/npm。体验包不包含 Python、uv、Docker 镜像或 AI Key，不是离线免安装包。
- 本轮未开启实际 Docker 边界与全部参考程序测试，也未使用真实付费 AI Key 验证账户连接；相关能力沿用原实现，本次不宣称新增验证。
- 安装中 uv 可能提示跨磁盘硬链接失败并回退复制，实际安装成功；沙箱环境本身限制 uv 缓存与本机套接字访问，完整安装和验证在允许的本机执行环境中完成。
- 尚未创建 Git 提交、推送仓库或上传 GitHub Release。提交时应包含新增脚本、文档和内置题库；只推送已跟踪文件会遗漏首次部署所需内容。
- 没有批量清理，所有验收目录和旧发布保留。
