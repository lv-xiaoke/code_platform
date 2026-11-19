# CodeTop macOS 支持设计

日期：2026-11-19

状态：用户于 2026-11-19 确认本规格及原生执行方式；适配代码已实施，Windows 回归通过，Mac 构建和实机验收待执行，详见 docs/macos-validation.md。

## 目标与交付

让 Mac 用户安装后双击 CodeTop.app，即可在默认浏览器使用题库、笔记、进度、Python 练习和 AI 助教，不需要自行安装 Python、Node 或 Docker。继续使用 React + FastAPI + SQLite，Windows 与 macOS 共用业务代码。

交付包括平台适配代码、Mac 构建脚本、macOS CI 配置、安装说明与测试。Apple Silicon arm64 为首个验收目标；Intel x86_64 使用独立构建和验收，未经过对应环境测试的产物不能标记为已支持。不在首版合并 universal2 安装包。最低 macOS 版本以 macOS 13 为初始构建目标，必须经过构建依赖及运行验证后才写入正式下载说明。

本机为 Windows，能够完成代码开发、Windows 回归和平台分支单元测试。Mac 应用构建、钥匙串、签名、公证、Finder 启动和 Safari 验收必须由 macOS 实机或 CI 提供证据；缺少该环境时明确交付为待 Mac 验收，不能宣称 Mac 版本已验证完成。

## 当前实现及适配原因

- `backend/app/desktop.py` 使用 Windows 创建标志、等待进程 API 和错误弹窗，同时负责服务复用、端口选择、恢复助手和浏览器启动。
- `backend/app/paths.py` 固定使用 LOCALAPPDATA、python.exe，并假设冻结应用的资源都在可执行文件旁边。
- `backend/app/runner/native_process.py` 直接导入 windows_job；`native.py` 仅允许 Windows 并硬编码运行时标识。
- `backend/app/ai/secrets.py` 使用 DPAPI，其他系统当前只能通过环境变量配置 Key。
- `scripts/build_desktop.py` 复制 Windows Python 文件、生成 Windows 运行时清单并调用 Inno Setup。
- `backend/app/runtime.py` 已有 fcntl 文件锁分支和浏览器标签生命周期管理，可继续复用。
- 工作区已有用户对 README.md 的修改，实施时保留。

## 平台边界

增加小型平台模块，集中处理系统识别、架构标识、后台进程选项、等待服务退出和用户可见错误。Windows API 只在 Windows 分支导入；macOS 使用独立实现，避免 macOS 打包收集模块时触发 WinDLL 或 msvcrt 导入失败。

资源根目录、运行时目录和可写数据目录分别定位，均不依赖当前工作目录或用户 PATH。冻结 Mac 应用将静态页面、题库和元数据放在 Contents/Resources，启动程序放在 Contents/MacOS，内置解释器以独立可执行程序保留。源码模式保留原有项目布局及 CODETOP_DATA_DIR 覆盖规则。

Windows 发布与 Start-CodeTop.cmd 入口保留现有行为。首版不改为 Electron/Tauri，不新增独立桌面窗口、账号或同步服务。

## 启动与退出

Finder 双击应用后：定位数据目录，获取启动锁，核对已有服务的应用标识、资源目录和数据目录；匹配则打开已有服务，否则寻找可用端口，启动后台服务，健康检查成功后打开默认浏览器。仅监听 127.0.0.1。

沿用浏览器标签连接和关闭宽限期，刷新页面或关闭其中一个标签不应退出服务；关闭最后一个标签后，宽限期结束自动停止服务并结束正在运行的代码。开发模式提供可常驻的无浏览器入口。

Mac 后台进程启动不传 Windows creationflags；错误写入用户日志并提供原生可见提示。恢复助手等待原服务确实退出、数据锁可取得后才恢复，不能只凭 PID 是否存在就误判，因为 PID 可能被复用。失败保留原学习数据，记录恢复状态，重新提供可用服务。

## 本机 Python 运行器

保持现有 NativeRunner、NativeTerminalRunner 及 API 结果格式。将进程管理与有界 stdin/stdout/stderr 传输分离，Windows 继续使用 JobProcess，macOS 新增独立实现。

Mac 解释器通过独立会话/进程组启动；受信任的启动代码先设置可用的 CPU、文件大小和 core dump 限制，再执行练习代码。不要在有线程的服务中使用 preexec_fn。监督端限制总输出、输入、墙钟时间，并监测进程组的 CPU 和常驻内存；停止或超限后结束本次练习的进程组，回收进程和管道。

普通样例保持 2 秒墙钟、3 秒 CPU、64 KiB 输出；交互模式沿用现有 300 秒墙钟、3 秒 CPU、64 KiB 输入及输出。内存目标为 256 MiB，macOS 采用实际常驻内存监测而非将 RLIMIT_AS 当成与 Windows 等价的硬限制。能力信息和文档应说明监测方式，未能实现的限制不能伪装成已强制执行。

正常运行、错误、超时、输出过量、内存过量和用户停止继续映射现有状态。中文输入输出、EOF、部分字节写入和 UTF-8 截断保持可用。环境变量使用白名单，AI Key 等不传给练习进程。

本机执行仍是个人学习用途，不承诺隔离恶意代码。进程组不能等同 Windows Job Object 对任意逃逸后代的管控；保留原有首次执行授权说明，并准确说明本机文件和网络访问能力。原 Docker 运行方式保留。

## 数据与凭据

冻结 Mac 应用默认数据目录为 `~/Library/Application Support/CodeTopLocal/`，包含学习库、备份、运行记录与日志；应用包内不写入用户数据。源码模式继续默认项目 data/，显式 CODETOP_DATA_DIR 优先。

保留现有 SQLite schema 和 ZIP 备份格式。使用 Windows 生成的备份恢复到 Mac，再由 Mac 生成备份恢复到 Windows，校验笔记、进度、收藏、题库来源、样例及代码历史。恢复不依赖原机器绝对路径；失败回滚机制保留。

KeyStore 对调用者继续暴露 read/write。Windows 保留 DPAPI；macOS 使用系统钥匙串通用密码项，服务标识固定为 CodeTopLocal.DeepSeek，账户标识与规范化后的数据目录关联，避免多个数据目录互相覆盖。通过系统 Security API 或经过验证的绑定调用，不将 Key 放入 shell 命令参数或日志。缺少钥匙串条目时沿用环境变量回退；钥匙串被锁定、拒绝访问或写入失败时显示明确错误，不回退为明文文件。Key 不写入 SQLite 和学习备份，跨设备迁移后重新配置。

## 构建与发布

复用前端构建和公共资产清单，分别维护 Windows、macOS arm64 和 macOS x86_64 的 Python 运行时清单。保留文件哈希校验、依赖锁定、许可证收集及新目录构建，避免覆盖历史发布产物。

新增 macOS 构建入口，在 macOS 上使用 PyInstaller BUNDLE 生成 CodeTop.app，包含独立 Python 运行时和所需动态库。检查动态库链接、可执行权限、架构与无开发环境条件下启动；不能把 Windows 的运行时复制规则直接套用到 Mac。

提供 macOS CI 配置以运行对应架构的测试和构建，只有已在目标架构验证的作业才可发布对应资产。测试构建可生成未公证应用供维护者验收，文档标明状态；正式发布使用 Developer ID 签名、hardened runtime、所需的最小权限及 Apple 公证，随后附加公证票据并生成 DMG 和 SHA-256 文件。签名内置解释器和动态库时遵循由内到外的顺序；校验清单必须基于签名完成后的最终文件生成，避免签名改变文件后导致运行时校验失败。

签名证书、Apple 账号及公证凭据由维护者提供给 macOS 构建环境，不能写入仓库。本次不自动上传 GitHub Release、不申请账号或购买证书。

## 验收

1. 平台单元测试：Mac/Windows 默认路径、包含中文和空格的路径、资源定位、运行时路径校验、平台导入、启动参数与凭据后端选择。
2. Windows 原有后端测试通过；本机执行、交互输入、停止、限时和学习备份恢复回归通过。
3. macOS 原生运行测试：正常输出、中文输入、语法与运行错误、死循环、过量输出、内存增长、交互 EOF、停止时的子进程及管道释放、服务关闭时运行中代码退出。
4. macOS 桌面流程：Finder 双击、应用移动到 Applications 后启动、重复启动、端口占用、Safari/Chrome 多标签及刷新、最后一页关闭、学习数据保留、恢复失败回滚及成功后重启。
5. 干净 Mac 环境：没有项目源码、Python、Node、Docker、开发依赖和 PATH 配置，内置题库与练习均能运行；钥匙串读写、拒绝访问可预期；安装包校验及签名、公证状态与发布说明一致。
6. 双向备份迁移验证通过，备份不含 Key。每个架构独立记录证据，不以 mock 测试替代 Mac 验收。
7. 若需要改前端能力展示或提示，验收通过后执行 scripts/build.ps1 更新 Windows 本地发布包，并从 Start-CodeTop.cmd 启动验证。

## 实施顺序

先完成平台及目录适配，再接通启动/恢复和钥匙串，随后实现 Mac 本机运行器，最后完成 Mac 构建、CI、文档及平台验收。针对每个行为先增加能揭示平台问题的测试，再实现；保留现有 Windows 功能。禁止批量删除，所有输出写入新的明确目录。

## 外部参考

- PyInstaller 平台要求：https://pyinstaller.org/en/latest/requirements.html
- Apple 公证流程：https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution

以上参考在方案讨论阶段已核对；实现时需核对实际锁定版本及 macOS 构建环境，不以文档中的能力声明替代产物测试。
