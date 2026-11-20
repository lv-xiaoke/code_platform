# CodeTop 多语言练习升级设计

日期：2026-11-20

状态：设计已确认，产品实现和三平台自动验收已完成。实施计划见 [2026-11-20-multilanguage.md](../plans/2026-11-20-multilanguage.md)；人工验收边界与已知次要问题见 [验收记录](../../multilanguage-acceptance.md)。

## 目标和范围

让 Windows x64、macOS arm64 和 macOS x86_64 用户在现有刷题工作台中编写、编译并运行 Python、C、C++、Java 和 JavaScript，继续使用交互终端、预设输入、高级测试、笔记、代码历史和 AI 助教。不同语言草稿独立保存，已有学习数据能够升级和恢复。

首版以单文件完整算法程序和标准输入/输出为约定：Python 3.12、C17、C++17、Java 21、Node.js 24。C/C++ 提供标准头文件模板；不默认承诺 GNU 专有头文件或编译扩展在所有平台一致，不静默改写用户源码。Java 使用不带 package 声明的 Main 类和 main 入口；Node.js 使用普通 JavaScript CommonJS 脚本，不提供浏览器 DOM。嵌套类和同一文件内的辅助函数/类型正常支持。

首版不提供多文件工程、外部包管理、npm/Maven/Gradle 依赖安装、交互 REPL、断点调试或原题网站的函数签名自动适配。已有 Go、Rust、TypeScript、SQL、text 等语言代码继续可编辑、保存和查看历史，但明确显示首版暂不支持执行，不能因选项调整丢失数据。

维持本机服务和浏览器界面；不新增云执行或多人服务。Python 继续内置，其他运行时按需准备。Windows 原有 Start-CodeTop.cmd 和桌面快捷方式继续可用，Mac 应用和浏览器关闭生命周期保持现有行为。

## 当前限制

- CodePractice 只有 Python 使用 CodeMirror，其他语言为 textarea；AcmWorkspace 禁用非 Python 的运行和测试按钮。
- RunWrite.language 仅允许 python，TerminalStart 缺少 language，交互请求重试签名没有语言。
- NativeRunner 和 native_process 写死 Python 文件名、启动参数和版本字段，Mac bootstrap 也直接 runpy 执行 Python。
- notes 同时保存共享 Markdown 和唯一的 code_text/language/revision；切换语言没有独立草稿。
- code_history 已有 language，code_runs 无语言列，展示层将所有运行记录强制标为 Python。
- 数据库当前版本 0003；备份校验只接受 0001–0003 并显式统计固定表。
- 参考程序包目前是 Python；AI 请求已有 language 字段，可复用并增加编译上下文。

## 语言环境准备

选择“基础应用 + 按需语言环境”方案，避免每个用户安装全部编译器。完整内置是未来离线发行包选项；本次不同时制作第二种全量安装包。原 Docker Python 模式保留，但多语言首版通过本机执行器交付，不假装 Docker 已支持新增语言。

| 语言 | Windows | Mac |
| --- | --- | --- |
| Python | 现有内置 CPython | 现有内置 CPython |
| C / C++ | 下载完整 LLVM-MinGW 工具链，含编译器、链接器、标准库 | 检测 Apple Command Line Tools / 已配置 Xcode 中的 clang、clang++ 与 SDK |
| Java | 下载 Eclipse Temurin 21 JDK | 下载对应架构 Eclipse Temurin 21 JDK |
| JavaScript | 下载 Node.js 24 | 下载对应架构 Node.js 24 |

每个可下载运行时由随版本发布的受审阅清单锁定确切发行版、来源 URL、SHA-256、操作系统、架构、入口和许可证信息，不在运行时请求 latest 决定执行版本。不能仅复制一个 clang.exe 就声称具备完整 C/C++ 编译环境。不同语言版本更新通过明确的发布变更进行。

新增语言环境页面/面板，展示“未准备、下载中、校验中、解压中、已就绪、准备失败、需要系统工具”及具体版本。选择语言不会自动下载；用户点击“准备环境”才下载对应包。首次准备需联网，已准备环境可离线使用；失败可重试，不删除已有可用环境，不重置草稿。

工具链默认位于当前用户 CodeTopLocal/toolchains 下，独立于应用包和学习数据目录，并可由开发配置显式指定测试根目录。不写 PATH、JAVA_HOME 或其他全局设置；启动使用经过校验的绝对路径。应用更新和恢复学习备份不删除工具链；共享工具链目录不包含学习内容，数据目录切换可复用同一工具链。学习备份不包含编译器压缩包、已解压工具链或编译产物。

下载和解压使用唯一 staging 目录，检查响应大小上限、压缩文件哈希、成员路径、符号链接/硬链接和解压总大小。校验并探测版本、架构及基础编译/运行能力后原子发布为 ready，不能暴露半安装目录。准备作业按工具链加锁，C 与 C++ 共享同一作业；同一环境重复请求返回同一准备状态。取消或失败时保留明确状态供排查，遵守禁止批量删除约束。

Mac 缺少 C/C++ 工具时先通过 xcode-select 配置探测，不调用可能自动弹安装提示的编译器占位程序。面板提供 Apple 官方安装说明，由用户完成系统工具安装和必要系统确认，再点击重新检查；不要求完整 Xcode，也不要求付费开发者账号。安装后的版本和 SDK 路径被记录并显示。没有 SDK 时其他语言继续工作，C/C++ 仍可编辑保存。

## 统一编译与执行

拆出 LanguageSpec、ToolchainRegistry、ProgramPreparer 和 ProcessSupervisor 四个职责：

1. LanguageSpec 提供语言标识、文件名、模板、标准、预算、编译和运行参数规则。
2. ToolchainRegistry 负责已审核清单、准备状态和绝对工具路径，不参与用户源码执行。
3. ProgramPreparer 在每个运行 UUID 对应的新目录写入 main.py、main.c、main.cpp、Main.java 或 main.js；C/C++/Java 编译一次，供本次任务全部样例复用。
4. ProcessSupervisor 接收 argv、cwd、白名单环境、预算、输入和停止事件，提供有界 stdout/stderr 和退出信息，复用 Windows Job Object 与 Mac 进程组管理。

调用编译器/运行时均使用参数数组，不拼接 shell 命令。编译产物仅在本任务独立目录使用，验证存在且路径不越界；首版不做跨任务的全局编译缓存，避免语言/版本/参数改变却执行旧二进制。

编译期与运行期分别管理。C/C++/Java 编译期默认墙钟 30 秒、CPU 20 秒、总内存目标 1 GiB、诊断输出 256 KiB。编译期不接受终端输入，取消立即停止编译进程及其受管后代；编译失败不继续启动程序。

普通样例默认墙钟 2 秒、CPU 3 秒；交互程序墙钟 300 秒、CPU 3 秒，输入与输出各 64 KiB。Python、C、C++ 总内存目标 256 MiB；Java、JavaScript 总内存目标 512 MiB，Java 堆上限和 Node 堆上限初始各 128 MiB。能力接口如实返回各语言实际限制；Java 堆不是整个 JVM 的内存，不能将 -Xmx 标成进程总内存。

Windows 使用 Job Object 的受管组限制；Mac 使用进程组资源采样、可信子进程引导和 CPU 限制，明确采样阈值可能短暂超出。Mac 可信引导设置限制后 exec 目标程序，不能给 Java/C 可执行文件附加 Python 参数。不能在线程化服务中使用 preexec_fn。

状态至少区分 preparing、compiling、running、compile_error、compile_time_limit、runtime_error、time_limit、memory_limit、output_limit、stopped，以及样例比较后的 passed/wrong_answer/executed。保留编译诊断与运行 stdout/stderr 的区别，不把 javac/clang 输出混入答案比较。JavaScript/Python 语法错误通过对应执行诊断显示。执行记录同时保存语言、版本/工具链标识、编译诊断、运行结果和预算。

交互终端继续采用管道标准输入/输出，不宣称是系统终端或 REPL。模板及提示明确各语言输入、EOF 和 flush 用法，避免 C/C++ 等程序等待输入时因 stdout 缓冲而没有提示。停止、关页、恢复和服务退出均取消编译/运行任务并释放输入输出线程；编译器或用户后代持有管道不能无限阻塞请求。

## 编辑器和交互

以统一 CodeEditor 替代 PythonEditor 的调用边界，按语言载入 CodeMirror 扩展，保留主题、无障碍标签、当前练习与只读历史视图。没有执行能力的历史语言明确显示“可编辑，暂不支持运行”。

初次打开尚无草稿的语言时可提供模板；不得用模板覆盖已有空白草稿或已保存代码。初次草稿是否存在由服务器记录区分，不能仅凭字符串为空判断。Java 模板显示 Main 入口要求，C/C++ 使用跨平台标准头文件，Node 模板说明 fs 读到 EOF 的行为。

切换语言时先停止本题活动编译/运行，再保存当前草稿，保存成功后切换并读取目标语言草稿。保存、取消或冲突失败时停留原语言并保留输入。切换期间锁住语言操作，防止较晚的网络响应覆盖新语言内容。运行中的环境准备不阻塞代码编辑；未就绪时按钮显示准备入口而不是泛化成 Docker 未就绪。

高级测试的 stdin/stdout 用例继续按题共享，便于同题多语言实现比较；运行记录和当前终端按语言区分，不能在切换后将 Python 的延迟输出当作 Java 结果。请求重试标识至少覆盖题目、语言、源码、模式和样例内容；相同代码文本但语言不同必须视为不同请求。

## 草稿、历史及迁移

新增 schema 0004，多语言代码以 code_drafts(problem_id, language) 为唯一键，记录 code_text、revision、created_at、updated_at。Markdown 笔记仍按题共享，并与草稿独立修订，代码自动保存不重置或覆盖 Markdown。

迁移前自动生成可恢复的旧版本备份。对每条旧 notes，将 code_text 按其原 language 原样迁入对应草稿，即使代码为空也保留该草稿存在性；未支持执行的旧语言同样迁移。保留旧 code_history 及其语言；code_runs 新增语言和工具链元数据，旧运行记录归为 Python。迁移不生成虚假的历史版本，不修改进度、收藏、原题面和 AI Key。

新接口将笔记正文保存、语言草稿保存和语言选择偏好分开：草稿按自身 revision 乐观并发控制；笔记正文按笔记 revision 控制；最近选用语言保存在题目偏好中。草稿和笔记保存失败均保留原有导出/冲突恢复体验。

旧 notes.code_text/language 字段保留作为旧数据迁移来源，不再作为新的双写主存储。题目详情返回的旧 note 视图由当前草稿投影生成；新前端使用明确的草稿接口。旧合并保存请求若不能提供新草稿版本信息，返回清晰的版本冲突提示，保留输入并要求刷新；不能为了兼容旧页面而允许它覆盖较新的多语言草稿。

“重新编写”仅归档当前语言并清空该语言草稿；查看历史可按语言筛选。载入历史版本时保存并归档目标语言当前非空草稿，切换到该历史版本的语言，不覆盖其他语言草稿。新记录保留完整语言和版本字段，Python 的 python_version 作为兼容字段保留，其他语言使用通用 runtime_version 展示。

备份校验增加 0004 和 code_drafts，保留对 0001/0002/0003 的读取与升级。新备份包括全部语言草稿、共享笔记、历史、语言选择偏好及运行记录，不包含外部工具链。旧应用不支持新结构的备份时应明确提示升级，不将新备份伪装为旧结构。

## API、参考程序和 AI

RunWrite、TerminalStart 都接受明确 language；旧的 Python 运行客户端省略语言时仍按 Python 执行。服务端独立验证语言与环境状态，不能仅依赖前端禁用按钮。未知语言或缺少工具链返回明确错误，并在创建运行记录前处理可恢复的环境问题。

健康/语言能力接口按语言返回编译器及运行时版本、是否需要编译、运行器类型、准备状态、限制和错误。保留 Python 兼容健康字段，前端以当前语言能力显示就绪状态。Docker 模式中首版仅 Python 就绪；其他语言提示切换本机模式，不能误用 Python 镜像执行。

已有参考程序继续按 Python 标注，通用输入输出样例与比较器可以复用。提供五种语言通用模板，并选用小范围确定的多语言示例完成真实测试，不把 Python 参考源码直接显示为 Java/C++ 模板，不自动批量生成全部题目参考解答。

AI 已有语言上下文字段，新增当前运行的语言、编译诊断、运行错误与版本信息。历史代码回填 AI 时携带该版本语言；提示和按钮移除只适用于 Python 的固定描述，不发送 API Key 或工具链用户路径中的额外私密信息。

## 文件职责和实施顺序

主要变化集中在 backend/app/runner（语言定义、工具链、准备与执行）、backend/app 的学习/模型/备份接口、backend/migrations、frontend/src/local 的编辑器/草稿/运行/环境管理，以及 scripts/packaging/CI 的清单收录和跨平台验证。新增模块按职责拆分，避免把下载、编译、流式交互都堆入现有 native.py。

实施顺序：先迁移及独立草稿/API，随后抽出可执行任意受管 argv 的进程监督，再接入 C/C++、Java、JavaScript，之后完成环境准备 UI、编辑器和 AI 展示，最后更新打包、CI、README 和发布说明。每部分先写能揭示行为的失败测试，再实现和回归；不以编辑器能选择语言作为支持运行的验收。

所有输入输出目录使用明确的新路径；不批量删除文件/目录，不自动删除旧工具链、备份或发布。实施使用 codex/ 功能分支，当前 main 和用户数据先核对并保留。本阶段不自动申请系统权限、安装 Mac 系统工具或发布新 Release；构建与发布验收通过后再按用户授权进行。

## 验收标准

1. Python 原有输入、EOF、运行、样例、历史、AI 与 Windows/Mac 生命周期测试通过。
2. 每种新增语言验证 Unicode 输入输出、正常程序、语法/编译错误、运行错误、错误答案、多组样例、超时、内存/输出阈值、停止和编译期间关闭；批量任务仅编译一次。
3. Mac 上的 SDK 缺失和 Windows 工具链缺失显示准确准备入口；下载失败、校验失败、取消、并发准备和断网不破坏已有环境或草稿。就绪后的语言无网络也能执行基础程序。
4. 同题 Python→Java→Python 草稿不变；共享 Markdown 不丢失；保存冲突、切换中继续编辑、迟到响应、历史载入和关面板失败均保留内容。空白已存草稿不会被模板覆盖。
5. 旧 0003 数据库含多种 language、非空/空草稿和历史时无损升级；旧备份恢复升级、新多语言备份在三个目标平台之间交换后逐项内容一致，工具链和 Key 不出现在备份中。
6. 运行与交互请求的幂等性包含 language，不同语言不会复用同一个执行或编译产物；AI 及历史显示实际语言和工具链版本。
7. Windows x64、Mac arm64、Mac x86_64 分别测试五种语言及对应工具链。Mac 系统编译器在已安装 CLT 的环境验收，也验证未安装场景。没有真实环境的项目明确记为未执行。
8. 前端测试及类型检查通过后执行 scripts/build.ps1 更新本地 release，从 Start-CodeTop.cmd 验证语言切换、环境准备、编译和运行；Mac 验收实际打包应用，不仅测试源码。

## 资料核对

以下为设计阶段查阅的官方来源；清单锁定具体发行版及 SHA-256 时继续核对其实际发布资产，不在此凭空填写版本或哈希。

- LLVM-MinGW 发布：https://github.com/mstorsjo/llvm-mingw/releases
- Temurin 21 发布与平台：https://adoptium.net/temurin/releases?version=21 ，https://adoptium.net/supported-platforms/
- Node.js 24 发布目录：https://nodejs.org/download/release/latest-v24.x/ （应用使用审核后的固定版本清单，不直接跟随此 latest 地址）
- Apple Command Line Tools：https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/
- Java JVM 参数：https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html
- Clang 标准选项：https://clang.llvm.org/docs/UsersManual.html
