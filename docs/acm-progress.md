# Execution ledger — 2026-10-21-python-acm

- User selected Python and local Docker execution after reviewing the proposed ACM workflow. Continue inline in the existing project root under the prior authorization to implement routine details; no repeated approval gate.
- Baseline: Git is now initialized at ba7b092, working tree clean. Work in the user-selected root without moving files or creating a second checkout.
- Formal database baseline: 1 personal note, 0 practice attempts. Preserve note contents, code and revisions; verification records only counts/hashes.
- Docker Desktop engine 29.8.2 is available. The official Python image is installed and pinned in backend/runner/runtime.json; actual Python version is 3.12.15.
- Scope: top 50 overall source records from the existing fixed snapshot, including supplemental source ID 1906. No title/slug identity matching.
- Preflight: run history stores complete source/case/result data in SQLite; run artifacts are redundant and are retained without cleanup. Backup compatibility must precede production schema migration.
- Tasks 1–6: complete. Current release: releases/20261021-150253-997-59bbd2, app 1.1.0 / schema 0002.

## Delivery and verification

- Added schema 0002, compatible 0001/0002 backups, persistent scratch input/test suites and complete asynchronous run history. No practice counters or review state are changed by execution.
- Implemented Python stdin/stdout editor, saved custom tests, four output comparators, job polling, per-case diagnostics/history and independent full-reference execution.
- Authored exactly 50 standalone programs for the snapshot's first 50 overall source records. All 152 golden cases passed in the pinned Docker runtime. Source, case and verification hashes are retained in backend/reference_pack.
- Full final verification: 52 backend tests passed (including real Docker and all references), 3 frontend request tests passed, TypeScript check passed, production build passed. One upstream test-client deprecation and one upstream chunk import warning remain non-blocking.
- Independent review found four Important issues: stale suite cache after reopening, detached/orphan child survival, JSON-escaped output exceeding host transport cap, and stale suite retry identity after a lost response. All were repaired; the additional delayed-GET revision rollback race was also fixed. Limited final re-review found no remaining Important/Critical issues.
- Red/green evidence: all three new Docker regressions failed on the original runner and passed after fixes. Browser reproduced the stale suite issue before the fix; saving, closing/reopening, and continuing to edit passed afterward.
- Browser acceptance used runtime/acm-acceptance on port 8001. Custom input passed, incorrect expectation displayed wrong output, reference execution passed 4/4 and then 5/5 with a saved custom case, and personal editor source stayed unchanged. No browser console errors were observed.
- Actual acceptance backup was restored into runtime/acm-restore-6c48bd64bee142ebbeb4e1417725432b. Complete rows for notes, suites and four run records matched; practice and study rows remained empty. Evidence: runtime/acm-backup-verified.json.
- Production was backed up before migration (schema 0001) and after migration (schema 0002). The original 1 note, 0 practice logs, 0 study states and 0 settings matched the complete pre-upgrade ordered-row JSON hashes. Evidence: runtime/acm-personal-baseline.json and runtime/acm-personal-verified.json. Production contains no acceptance runs or suites.
- Formal service is running at http://127.0.0.1:8000 with the new release; README and environment.json were updated. Existing data, source files, backups, test directories, run artifacts and prior releases were retained. No bulk deletion or prune was performed.
