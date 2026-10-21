# Python ACM Implementation Plan

> **For agentic workers:** Use executing-plans inline; perform one independent review at the end. Preserve all artifacts and never bulk delete.

**Goal:** Deliver a runnable Python ACM workspace and 50 verified reference programs.

**Architecture:** React editor and test panel call asynchronous FastAPI jobs; an isolated Docker Python supervisor executes complete stdin/stdout programs. Additive SQLite migration persists test suites and runs, preserving the existing note workflow.

**Tech Stack:** Existing React/CodeMirror/TanStack Query, FastAPI/SQLAlchemy/Alembic, Python 3.12 Docker image pinned by digest.

**Spec:** ../specs/2026-10-21-python-acm-design.md

## Global Constraints

- Work at D:\my_develop\A_work_program\code_platform; no bulk deletion or prune.
- Preserve the existing personal note and all original learning data.
- Python only initially, complete programs with stdin/stdout, no host execution fallback.
- 2 seconds/case, 256 MiB, 64 KiB output/case, at most 20 cases; two workers/eight outstanding jobs.
- Existing same-origin/session/revision boundaries remain in force.
- Local examples and original reference programs are clearly labeled; no claims of official hidden-test AC.

## Review Focus

1. Timeout, forked processes and massive stdout cannot leave unbounded jobs or host memory use.
2. Docker arguments, mounts and case inputs cannot select arbitrary host paths or commands.
3. Schema migration and restoring original backups retain the existing note and learning data.
4. Concurrent run requests and note/test-suite edits retain idempotency and conflict visibility.
5. Reference copying/loading and async refresh never silently replace a draft or auto-mark practice done.

### Task 1: Additive schema and compatible backups

Files: backend/app/{models,db,backups}.py, backend/migrations/versions/0002_acm.py, backend/tests/test_acm_data.py.

- [x] Write and run failing tests that construct schema 0001, add a note, upgrade to 0002, verify a pre-migration 0001 backup and restore/re-upgrade it.
- [x] Add problem_test_suites(problem_id, revision, cases_json, updated_at) and code_runs(id, problem_id, request_id unique, request_hash, source_code, tests_json, results_json, status, error, image_ref, created_at, finished_at).
- [x] Recognize snapshot versions 0001/0002 and actual count tables; run old and new backup tests.

### Task 2: Bounded Docker execution

Files: backend/runner/{worker.py,runtime.json}, backend/app/runner/{docker.py,comparison.py}, scripts/setup-runner.ps1, backend/tests/test_runner*.py.

Interfaces: DockerRunner.execute(job_id, source_code, cases) returns case results; health() returns pinned-image status; compare_output(actual, expected, mode) returns bool.

- [x] Test normalization, empty expectations, finite float tolerance, command arguments/mount isolation, timeout/output-limit handling; observe failure before implementing.
- [x] Implement trusted Linux supervisor and bounded host transport with exact-container shutdown; preserve host artifacts.
- [x] Pull and pin official Python runtime; validate actual normal, error, timeout, excessive output and isolation cases.

### Task 3: Reference pack

Files: backend/reference_pack/, backend/app/runner/references.py, backend/tests/test_references.py.

Interfaces: reference_for(conn, problem_id) returns a matched source-record contract and complete authored Python reference plus golden tests; unsupported problems return a generic stdin template and no invented reference.

- [x] Define golden tests and metadata for the fixed top 50 overall records, including supplemental 1906.
- [x] Implement each original algorithm as a complete standalone Python main program with explicit ACM contracts.
- [x] Validate all references inside Docker and record program hashes/test evidence; verify unsupported/duplicate-slug mapping.

### Task 4: Async run and suite APIs

Files: backend/app/runner/{schemas,service,routes}.py, backend/app/main.py, backend/tests/test_acm_api.py.

Interfaces: suites revision write; runs accept request_id, source_code, mode custom/suite and custom cases; job service owns two workers and an eight-job gate.

- [x] Test suite conflicts, job retries/hash conflicts, queue bound, restart handling, problem validation and unchanged study counters.
- [x] Implement APIs, persist full submitted inputs/results, recover interrupted jobs and return clear unavailable-runtime failures.
- [x] Verify runs/tests round-trip through a complete backup.

### Task 5: Python ACM interface

Files: frontend/src/local/{AcmWorkspace,RunResults,ReferencePanel}.tsx, acm.css, API types; integrate with ProblemDialog and existing useNote.

- [x] Add CodeMirror Python code editor, stdin/expected fields, comparison, saved custom cases and current/all-run actions.
- [x] Poll job status, display per-case errors/diffs/timing, and expose source/result history.
- [x] Add visible contracts and collapsed reference solutions, copy/reference-run actions and empty-editor-only template loading.
- [x] Keep autosave/revision protection and show failures without losing drafts.
- [x] Type-check and build a new retained release; browser-verify on an isolated data directory.

### Task 6: Review and production upgrade

Files: README.md, environment.json, docs/acm-acceptance.md, docs/acm-progress.md.

- [x] Independently review changes; reproduce and repair important findings.
- [x] Run full regression tests, actual Docker/reference verification, TypeScript and release build.
- [x] Back up and restart the production service, verify migration and the existing personal note count/hash.
- [x] Verify browser operation, preserve artifacts, deliver running application and usage instructions.
