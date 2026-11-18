# CodeTop Local 发布整理执行计划

**目标：** 新用户看懂项目用途，能够从源码或 Windows 体验包安装并看到内置题库。

**设计依据：** 用户已批准本次聊天中提出的五部分方案，并要求开始执行。保持 Windows 单人本机应用定位，保留 Start-CodeTop.cmd、关闭标签页退出服务、SQLite 数据和现有备份机制。不增加云服务或跨平台承诺。

**实现：** 修正 Git 忽略范围；沿用 uv + Python 3.12 安装后端；体验包通过 RuntimeOnly 跳过前端工具，源码使用锁定依赖构建。通过文件白名单生成 ZIP，保留来源许可证并输出 SHA256。

## 执行清单

- [x] 增加回归测试：题库可被 Git 收录；体验包包含当前页面与题库，排除私密数据和旧发布；缺文件、越界路径及重复输出应失败。
- [x] 修正 .gitignore，增加 Setup-CodeTop.cmd，完善 setup.ps1 环境检查、RuntimeOnly、失败退出；保留现有 SkipBuild 用法。
- [x] 增加 package-release.ps1 和 package_release.py，生成独立 ZIP 与 SHA256，拒绝覆盖，不执行清理。
- [x] 将原 README 归档为详细使用手册，重写中文 README，增加部署和发布说明、第三方声明及截图。
- [x] 执行 scripts/verify.ps1 和 scripts/build.ps1，生成真实体验包，检查 ZIP 内容。
- [x] 从 ZIP 解压到 runtime 下的中文空格目录，重新安装后端、初始化独立数据；经 Start-CodeTop.cmd 启动，验证题库、静态资源和浏览器连接生命周期。
- [x] 从 Git 可分发文件创建干净源码副本，不携带虚拟环境、Node 工具或发布页面，执行 setup.ps1 -BuildFromSource，通过依赖安装、题库初始化与构建。
- [x] 记录验收证据与未验证边界，交付体验包。

验收证据见 `docs/public-release-acceptance.md`。中文路径验收中新增健康接口 UTF-8 修复，回归测试先失败再通过。

## 重点边界

- 只支持本次实际验证的 Windows 部署路径。
- 不复制开发机虚拟环境；体验包首次安装需要网络和 uv。
- 不覆盖用户学习数据库；初始化可重复执行。
- 包内只保留 releases/current.json 指向的页面；拒绝指向 releases 外的路径及符号链接。
- 所有测试和打包产物保留；禁止批量删除，不创建清理脚本。
- 发布文档不宣称题库实时更新，也不把本地测试描述为官方判题。
