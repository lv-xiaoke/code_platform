# Third-party sources and attribution

The frontend is based on [dogxii/algoTop](https://github.com/dogxii/algoTop), commit `64d624feee3fbec0dc67dd58f0cf8874ecdc6e1b`, copyright (c) 2026 Dogxi. The original MIT license is retained in `frontend/LICENSE` and `vendor/algoTop-main/LICENSE`. Original source and lockfile are retained in `vendor/`; the local entry point adapts its theme, React tooling, Query dependency and CodeMirror Markdown editor.

The bundled catalog is the upstream `public/data/codetop.json` snapshot, generated at `2026-07-18T14:29:48.365Z`, SHA256 `BC496564C4939EAE1173636DEC05B358B0A46B0B6DD1797D3FF10416DBC81AC9`. Upstream attributes inspiration and data to [CodeTop](https://codetop.cc). Problem statements, links and underlying material retain their respective original attribution, including LeetCode. The repository's software license is not represented as a separate license grant for third-party problem text or statistics.

The local application uses React, TanStack Query, Vite, TypeScript, CodeMirror, lucide-react, highlight.js and DOMPurify in the frontend, and FastAPI, Starlette, Pydantic, SQLAlchemy, Alembic, Uvicorn and Python SQLite in the backend. Exact versions are in the lockfiles and `environment.json`; package license files are included with installed dependencies. DOMPurify project: [cure53/DOMPurify](https://github.com/cure53/DOMPurify).

This installation is a personal local workspace. It does not fetch live rankings, submit solutions, or provide cloud account synchronization.
