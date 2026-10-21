# Python ACM workspace

User-selected extension: Python and a local Docker executor. Continue implementing in the current project root; preserve all existing data and files. No bulk removal or Docker prune operations.

## Experience

The problem dialog gains a Python CodeMirror editor, editable stdin/expected-output cases, run-current/run-all actions, bounded results, execution history, and a collapsible complete reference program with an independent run action. Code retains the existing note revision/autosave protection. Tests have their own revision. Loading a template is allowed only into an empty editor; reference code has copy and run actions and never silently replaces personal code. Running code does not record practice completion or alter the review schedule.

Every problem supports free-form ACM execution: the user's program reads stdin and writes stdout. Top 50 overall source records get authored input/output specifications, Python reference programs with complete main entry points, explanations, complexity, and explicit golden tests. Other problems clearly say a curated contract/reference is not yet supplied and allow custom tests. LeetCode and supplemental identities remain separate. References are original local learning examples, not official solutions; tests are visible local examples, not official hidden tests.

## Executor

Use an official Python 3.12 Linux image pinned by digest after installation. Never fall back to running user code on Windows. Docker runs without network, privileges, Docker socket or application database mounts, with a read-only filesystem and only a read-only per-run source/input directory plus the trusted supervisor. Run as uid/gid 65534, drop capabilities, no-new-privileges, pids 32, one CPU, memory/swap 256 MiB, tmpfs 16 MiB, no core dumps.

Each case has 2 seconds of execution time and combined stdout/stderr limited to 64 KiB. A supervisor executes each case in a separate Python process, captures bounded streams, kills its process group on deadline/output excess, and emits structured JSON. The host separately bounds Docker output and whole-job time. Only server-authored Docker argument lists and server-generated UUID paths/names are accepted. On timeout, stop exactly that owned container; remove only that individually named container. Host code/input/result artifacts remain under data/runs. Normal file/directory cleanup is not implemented.

Service concurrency is bounded to two jobs and at most eight outstanding jobs. Execution is asynchronous, status polled by the page; HTTP requests do not hold SQLite transactions while Docker runs. Requests use request_id plus a content hash; exact retries return the same job, conflicting retries return 409. Restart marks interrupted jobs clearly rather than leaving them pending indefinitely.

## Data and compatibility

Alembic 0002 only adds problem_test_suites and code_runs. Original tables are unchanged. Create a consistent 0001 backup before upgrading. Backups recognize 0001 and 0002, record the snapshot's actual schema, and include added tables' counts in 0002. Restoring 0001 is accepted and upgraded on next start. Raw code, case inputs and bounded outputs live in SQLite and are included in a full backup; data/runs contains redundant diagnostic artifacts.

Reference files are versioned application assets in backend/reference_pack. Database suites contain user cases only; application updates cannot overwrite them. Built-in and custom case IDs are namespaced in API output. References are read from the matched algotop source key, not title or shared slug.

## API

- GET /api/v1/runner/health: Docker/image availability, Python version and limits; actionable error if unavailable.
- GET /api/v1/problems/{id}/acm: contract, reference, built-in cases, saved custom cases and revision.
- PUT /api/v1/problems/{id}/test-cases: revision-checked custom case replacement.
- POST /api/v1/problems/{id}/runs: Python source, request_id, custom/suite mode; returns queued run.
- GET /api/v1/problems/{id}/runs: recent history, source and cases/results only on individual detail.
- GET /api/v1/runs/{id}: job status, submitted source, case results and error.

Comparison supports tokens, exact text, unordered lines and finite floating-point tolerance. Null expected output means run-only, while an empty string is a real expectation. Report success/mismatch, syntax/runtime error, timeout, output limit and infrastructure error separately. Passing labels always refer to supplied local cases.

## Acceptance

Regression tests for 0001 upgrade with a personal note, original backup restoration, revised tests and run history backup/restore; token protection; request retry collisions; bounded queue; no changes to practice data. Actual Docker checks cover normal/Unicode input, syntax/runtime error, infinite loop, excessive stdout, nonzero exit, network denial, host-data isolation and pinned runtime. Run every curated reference against its explicit golden tests inside Docker. Browser checks cover custom run, wrong expectation, full suite, reference run, saved tests and history after reload; preserve the production note and existing backups.
