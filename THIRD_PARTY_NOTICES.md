# 第三方来源与许可说明

## AlgoTop

- 上游项目：[dogxii/algoTop](https://github.com/dogxii/algoTop)。
- 本项目保留的上游前端源码和归档采用 MIT 许可证，版权声明为 `Copyright (c) 2026 Dogxi`。
- 许可证原文保存在 `frontend/LICENSE`、`vendor/algoTop-main/LICENSE` 和固定提交归档内；Windows 体验包保留前两份文件。
- 本地服务、学习数据、Python 运行与 AI 助教等能力是在本项目中增加和调整的；第三方 MIT 声明对应其上游代码。

## 内置题库快照

`vendor/algoTop-main/public/data/codetop.json` 来自 AlgoTop 的 CodeTop 数据快照，生成时间为 2026-07-18。固定来源提交：`64d624feee3fbec0dc67dd58f0cf8874ecdc6e1b`。文件 SHA256：

```text
bc496564c4939eae1173636dec05b358b0a46b0b6dd1797d3ff10416dbc81ac9
```

快照含 1,153 道题和 21,906 条范围统计。统计是快照累计次数，不代表当前实时考察情况。题面、题目名称、来源统计及商标等第三方内容的权利归相应权利人所有；上游软件的 MIT 许可不等于对第三方题目内容作出新的授权。

应用保留来源及原题链接，供个人学习时参考；CodeTop Local 与 CodeTop、LeetCode 等来源平台无官方隶属关系。

## 运行环境与在线服务

- Python 运行镜像来自 Docker Official Image `library/python`，实际镜像摘要见 `backend/runner/runtime.json`。镜像通过用户本机 Docker 单独获取，不包含在体验 ZIP 中。
- AI 助教通过用户自己的 DeepSeek 账户访问其服务，Key 不随软件分发。
- 前端使用 React、TanStack Query、Vite、TypeScript、CodeMirror、lucide-react、highlight.js 和 [DOMPurify](https://github.com/cure53/DOMPurify)；后端使用 FastAPI、Starlette、Pydantic、SQLAlchemy、Alembic、Uvicorn 和 Python SQLite。依赖以各自项目的许可证为准；后端锁文件和源码仓库中的前端、构建工具锁文件记录其版本，安装后的依赖保留其许可证文件。

对外分享请使用发布脚本生成的 ZIP，不要直接压缩自己的工作目录。
