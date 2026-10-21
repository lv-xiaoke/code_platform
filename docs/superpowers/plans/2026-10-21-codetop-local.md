# CodeTop Local Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task by task in the current directory. Keep this plan and progress.md; never bulk delete files.

**Goal:** Deliver the design's complete local practice, notes, review, import, backup and restore workflow on Windows.

**Architecture:** Retain the pinned AlgoTop React/TypeScript/Vite frontend and its lockfile, connecting it to a same-origin FastAPI service. SQLAlchemy with Alembic manages a WAL SQLite database; immutable source snapshots and versioned frontend releases remain on disk.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, SQLite, pytest; Node 24, Bun, React 18, TypeScript, Vite, TanStack Query, CodeMirror, DOMPurify.

**Spec:** [2026-10-21-codetop-local-design.md](../../../2026-10-21-codetop-local-design.md)

## Global Constraints

- Project root: `D:\my_develop\A_work_program\code_platform`; this overrides the suggested deployment directory in the spec.
- Preserve the original design, existing files, data, backups and source versions. Never bulk delete files or directories.
- Bind only to 127.0.0.1, one worker, no permissive CORS, same-origin and session-token checks on writes.
- Stable UUIDs identify problems; upstream internal IDs, display IDs and question IDs remain distinct.
- Dataset updates never overwrite notes, practice logs or study state; no cascade deletion.
- Frequency scope and units remain explicit. Company/department plus job uses intersection, never invented joint statistics.
- Review intervals 1,3,7,14,30 days; Asia/Shanghai dates, UTC event timestamps; optimistic revisions and request idempotency.
- Daily operation runs the built frontend and API from one Python service, offline after installation.

## Review Focus

1. Repeated slug or nonstandard display ID must not merge unrelated supplemental problems.
2. Concurrent note/state writes and request retries must not lose data or advance reviews twice.
3. Import failure, omitted questions and dataset rollback must preserve personal records and active dataset integrity.
4. Unsafe HTML, URLs, backup paths, origins and archive members must not escape their local boundary.
5. Starting from another directory, occupied ports and failed restore must retain the current database and provide an actionable message.

## Task 1: Pinned baseline and environment

**Files:** `vendor/`, `frontend/`, `backend/requirements*.txt`, `.gitignore`, `environment.json`.

- [x] Inspect the current directory and design; record the root override and inventory.
- [x] Resolve upstream commit with read-only Git, retain its archive, license, source data and Bun lock.
- [x] Create isolated Python 3.12 environment and project-local Node 24/Bun tools. Install pinned dependencies.
- [x] Build upstream unchanged and record the result before integration.
- [x] Confirm source hash, question count, taxonomy counts and scope row count against the design snapshot.

## Task 2: Versioned catalog and local API

**Files:** `backend/app/{config,db,models,catalog,imports,main}.py`, `backend/migrations/`, `backend/tests/test_catalog.py`.

**Interfaces:** `create_app(root, data_dir, clock)` returns FastAPI; `Database` provides short SQLAlchemy transactions; `preview_import(raw, kind, source_name)` returns a persisted preview; `apply_import(id)` atomically returns a dataset.

- [x] Write fixture tests for internal ID 1681 versus display ID 3, duplicate slugs, missing HTML/URL, invalid references, repeated imports, intersection counts and source rollback. Run pytest and observe the absent implementation failure.
- [x] Implement Alembic migration for the design's tables, foreign keys, unique constraints and indexes; enable WAL, foreign_keys and busy_timeout on every connection.
- [x] Implement strict AlgoTop and manual CSV/JSON parsers, immutable source storage, diff previews, stable UUID mapping, transactional version activation and original snapshot bootstrap.
- [x] Implement catalog, taxonomy, problem search/detail/history APIs with scope metadata, stable ordering, pagination and explicit validation errors.
- [x] Run catalog tests, load the actual snapshot and check counts and foreign keys.

## Task 3: Persistent learning and scheduling

**Files:** `backend/app/{learning,scheduler,schemas}.py`, `backend/tests/test_learning.py`.

**Interfaces:** revision-checked state/note writes; attempts accept unique `request_id` and one of `independent`, `hint`, `solution`, `unfinished`; scheduler receives a UTC event and returns state in Asia/Shanghai.

- [x] Write and run failing tests for note revision conflicts, idempotency across problems, same-day success/failure, UTC/local midnight, paused reviews, restart persistence and legacy browser migration.
- [x] Implement notes, state, attempts/history, due reviews, activity statistics and legacy migration preview/apply.
- [x] Commit attempts and schedule changes together; expose failures without discarding drafts.
- [x] Run learning and catalog tests together.

## Task 4: Consistent backups, restore and runtime

**Files:** `backend/app/{backups,cli}.py`, `backend/tests/test_backups.py`, `scripts/*.ps1`, `Start-CodeTop.cmd`.

**Interfaces:** backups return a ZIP with SQLite snapshot, source bytes, manifest, schema/app version and hashes; offline restore validates everything before replacing the live database, preserving a rollback file.

- [x] Write and run failing tests for complete round trip, tampered archives, traversal members, incompatible schemas, foreign-key validation and existing-data preservation.
- [x] Use sqlite3 backup, quick_check and foreign_key_check; auto-backup before migration, catalog apply, activation, restore and first daily startup.
- [x] Implement a server-held process lock and stop-before-restore checks, safe extraction and rollback-preserving restore.
- [x] Add root-relative setup/build/start/stop/backup/restore scripts, health/port checks, hidden background startup and logs.
- [x] Run backup tests and restore into a fresh isolated data directory.

## Task 5: Frontend integration

**Files:** `frontend/src/` with focused local API, catalog, learning and data-management modules; `frontend/vite.config.ts`; release artifacts.

**Interfaces:** typed `/api/v1` client obtains session token; TanStack Query invalidates affected scopes after writes; DOMPurify sanitizes source HTML and rendered Markdown.

- [x] Retain upstream theme, filters, CodeMirror and notes interaction; replace catalog and learning persistence with API calls.
- [x] Add review queue, source dates/scope explanation, practice outcomes, activity, version switching, import preview/apply and full backup download.
- [x] Add debounced note autosave with visible pending/saved/failed/conflict status and draft retention, revision-aware state controls and idempotent attempt submissions.
- [x] Support legacy browser export JSON through preview and migration without touching the original browser data.
- [x] Type-check and build into a fresh immutable release; serve same-origin and ensure unknown API paths remain JSON 404.

## Task 6: Acceptance and handoff

**Files:** `README.md`, `THIRD_PARTY_NOTICES.md`, `environment.json`, `docs/acceptance.md`, `docs/progress.md`.

- [x] Run the full backend suite, frontend type-check and production build; record exact counts and versions.
- [x] Browser-check filtering, problem content, note save, review completion, source dates and backup/import UI against a separate acceptance data directory.
- [x] Review implementation against the design, repair important findings and rerun the relevant checks.
- [x] Confirm double-click launch, port reuse, persistence after restart, consistent backup and fresh-directory restore.
- [x] Deliver the running local URL, launch file, usage instructions, verification evidence and any remaining limitations.
