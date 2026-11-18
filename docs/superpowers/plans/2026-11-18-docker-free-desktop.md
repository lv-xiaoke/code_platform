# Docker-free desktop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in the current chat. Steps use checkbox (`- [ ]`) syntax for tracking. User may instead choose subagent-driven-development during plan review.

**Goal:** Deliver a Windows x64 installer that opens the existing CodeTop interface and runs Python exercises without user-installed uv, Python, Node, Docker or WSL.

**Architecture:** Preserve the current learning services and HTTP contracts. Add Windows Job-managed native execution, explicit runner selection and machine-local consent; freeze the application launcher/service and ship a separate relocatable CPython 3.12 runtime for exercises. Keep desktop data outside the installation directory, provide graphical backup recovery, and build an ordinary-user Inno Setup installer with a file manifest and SHA256.

**Tech Stack:** Python 3.12, ctypes/Win32 Job Objects, FastAPI, React/TypeScript, PyInstaller, Inno Setup.

**Spec:** `docs/superpowers/specs/2026-11-18-docker-free-desktop-design.md` (approved by user on 2026-11-18).

## Global Constraints

- Windows x64 desktop release only; source launch and explicitly selected Docker mode remain available.
- No bulk deletion, cleanup script or directory removal; generated build/test artifacts go in fresh unique directories and remain there.
- Native execution runs as the current user and is not a filesystem/network sandbox.
- Never execute either existing Linux container supervisor on the host.
- Native child process enters its Job before user code can execute; assignment failure prevents execution.
- Standard tests: 2 seconds wall time each. Interactive: 300 seconds wall time and approximately 3 seconds cumulative CPU.
- Job limits: 256 MiB aggregate committed memory, 32 active processes, kill on final Job handle close, no breakaway flags.
- Input/output: 64 KiB input per case/session, 64 KiB combined stdout/stderr per case/session.
- Preserve current queue bounds, two interactive sessions, idempotent requests, notes and history.
- Installer includes dependencies and runtime; no first-run package downloads or system PATH/Python installation requirement.
- Desktop data: `%LOCALAPPDATA%\CodeTopLocal`; installation files and data must not overlap.
- Native consent is outside SQLite and all learning backups; enforce it in both server execution entry points.
- Run `scripts/build.ps1` after frontend changes and verify `Start-CodeTop.cmd`; separately verify the actual desktop executable/shortcut.
- No Git commit, main-branch push or Release mutation is part of this implementation plan without separate applicable authorization. Earlier automatic review rejected unsolicited direct main pushes.

## Review Focus

1. Child spawning happens before Job assignment, or a detached child holds pipes open: create suspended, bind Job, resume; test both normal parent exit and forced stop with real Windows processes.
2. Frozen `sys.executable` is mistakenly used as an interpreter, or PATH/env selects another Python: pin the separate bundled interpreter and sanitize Python environment; test a deliberately broken PATH and PYTHONPATH.
3. A caller bypasses the frontend consent dialog: exercise both HTTP run routes and direct service entry points before consent, with assertions that no source runs or run record is created.
4. Upgrade or restore affects the running learning database or overwrites consent/keys: run restore as a separate stopped-service operation, verify failure rollback and backup exclusions.
5. A healthy server belongs to another installation/data directory: validate identity before reuse and choose another port without stopping unrelated services; test two instances and occupied ports.

## File and interface map

| File | Responsibility / public contract |
| --- | --- |
| `backend/app/paths.py` | `application_root() -> Path`, `default_data_dir() -> Path`, `native_python() -> Path`; source/frozen path resolution |
| `backend/app/runner/windows_job.py` | `JobProcess(argv, cwd, env, *, memory_mb, max_processes)`; stdin/stdout/stderr streams, pid, poll/wait/terminate/close, cumulative CPU and memory-limit notification |
| `backend/app/runner/native_process.py` | `execute_process(python, script, *, stdin, inputs, stop_event, on_output, wall_seconds, cpu_seconds) -> dict`; bounded streams and lifecycle |
| `backend/app/runner/native.py` | `NativeRunner(artifact_root).health()/execute(job_id, source_code, cases)/close()`; current batch result shape and `image_ref` compatibility identifier |
| `backend/app/runner/terminal_native.py` | `NativeTerminalRunner(artifact_root).execute(session)/close()`; consumes existing `TerminalSession` |
| `backend/app/runner/factory.py` | `runner_kind() -> str`, `create_runner(artifact_root, *, interactive=False)`; explicit native/docker choice |
| `backend/app/runner/consent.py` | `consent_status(data_dir)`, `accept_native_execution(data_dir)`, `require_native_consent(data_dir)`; atomic local file |
| `backend/app/desktop.py` | EXE dispatch, service startup/reuse, browser opening, visible errors, stopped-service restoration |
| `backend/app/desktop_restore.py` | stage/validate a selected backup and issue a launcher restore ticket; no in-process replacement of live SQLite |
| `frontend/src/local/runnerEnvironment.ts` | health label and first-run consent flow shared by all run actions |
| `frontend/src/local/RestoreBackup.tsx` | archive picker, preview/confirmation, restoration status and restart handling |
| `scripts/build-desktop.ps1` | fresh staging/build directories, pinned build inputs, frontend build and packaging entry |
| `scripts/build_desktop.py` | allowlisted runtime/application assembly, manifests, PyInstaller invocation and artifact hashing |
| `packaging/desktop.spec` | frozen service/launcher dependencies, migrations and application assets |
| `packaging/CodeTop.iss` | per-user installer, shortcuts, stable app identity and data-preserving upgrade |
| `packaging/runtime-lock.json` | runtime/tool versions, source URLs and cryptographic hashes; consumed before assembly |

## Task 1: Native process supervision and real execution

**Create:** `paths.py`, `windows_job.py`, `native_process.py`, `native.py`, `terminal_native.py` and `backend/tests/test_native_runner.py`.

**Consumes:** `compare_output` from `comparison.py`; existing cases and `TerminalSession` shape. **Produces:** native equivalents of the existing batch and interactive runner interfaces; no service selection changes yet.

- [ ] Write the first batch test before implementation:

```python
def test_native_batch_runs_unicode_and_preserves_comparison(tmp_path):
    from uuid import uuid4
    from app.runner.native import NativeRunner
    runner = NativeRunner(tmp_path)
    result = runner.execute(str(uuid4()), 'print(input())', [
        {'name': 'unicode', 'stdin': '你好\n', 'expected_stdout': '你好\n', 'comparison': 'exact'}
    ])
    assert result['results'][0]['stdout'] == '你好\n'
    assert result['results'][0]['status'] == 'passed'
    assert result['python_version'].startswith('3.12.')
```

- [ ] Run `backend/.venv/Scripts/python.exe -m pytest -c backend/pytest.ini backend/tests/test_native_runner.py -q --tb=short`; confirm the missing native runner failure before writing production code.
- [ ] Implement the process launcher with public Win32 functions through ctypes. Create pipes with explicitly controlled inheritance, use `CreateProcessW` suspended and without a visible console, assign to a configured Job, then resume the primary thread. Wrap each OS handle in a single owner and close handles on all startup-error paths. No private subprocess attributes, system shell, taskkill-by-name or unsafe breakaway fallback.
- [ ] Implement concurrent stdout/stderr readers and a separate stdin writer. Use incremental UTF-8 decoders, enforce combined byte budget before emitting text, and use bounded queues/events so a user program that never reads stdin cannot hang stop or shutdown. Remove Python injection variables from the child environment, use `-I -S -B -u -X utf8`, keep Windows-required environment entries, and use an absolute bundled interpreter path.
- [ ] Monitor wall time, cumulative Job CPU and Job memory-limit notification separately. Explicit stop has `stopped`, wall/CPU expiry `time_limit`, output expiry `output_limit`, memory exhaustion `memory_limit`; syntax/runtime exceptions retain current statuses. Do not classify every nonzero Windows exit as memory exhaustion. Terminate the Job and drain bounded residual output on every exit, including normal parent exit with live descendants.
- [ ] Build the batch runner around one fresh task directory per execution and one fresh process/Job per case. Preserve comparison rules and return `{'results': [...], 'python_version': ...}`. `image_ref` becomes an honest compatibility string `local-python@<version>-windows-x64`, never a Docker digest.
- [ ] Build the terminal adapter around the existing session: emit `ready`, consume `session.inputs`, forward raw stdout/stderr via `session.emit`, close stdin once on EOF, and return the existing final status/duration shape. `close()` stops all tracked tasks and rejects new starts.
- [ ] Add real-process parameterized tests for `print`, assertion failure, syntax error, empty input, no final newline, Unicode split across read chunks, output flood, 20-case comparison, 2-second loop timeout, 3-second interactive CPU timeout and waiting for input without CPU timeout. Use literal expected outputs, not the implementation's serializer as an oracle.
- [ ] Add real terminal tests using `TerminalSession`: `s = TerminalSession(id, pid, 'print(input("提示> "))')`, run adapter in a thread, wait for the literal prompt, send `TerminalInput(request_id='line', text='中文\n')`, assert final stdout `提示> 中文\n`; separately cover `readline`, `read`, EOF, blank lines and manual stop.
- [ ] Add Job tests that spawn a long-lived child and write its PID to the test directory. On parent completion, manual stop, supervisor exit and output overflow, assert the recorded child PID is no longer alive and an independently created unrelated process still is. Test process-count and aggregate-memory limits. All test-created processes are terminated by their own PID/Job in `finally`, without file cleanup.
- [ ] Test invalid/missing interpreter, non-3.12 interpreter, tampered manifest and Job assignment failure. Verify user source cannot run before successful assignment by using a source script that writes a marker and asserting the marker is absent on failure.
- [ ] Run the new tests and existing runner/API tests. Native Windows tests require an execution environment that permits real child processes; report sandbox restrictions rather than weakening Job checks.

## Task 2: Service selection, consent and frontend execution flow

**Create:** `factory.py`, `consent.py`, `runnerEnvironment.ts`, `backend/tests/test_native_api.py`, `frontend/tests/runner-environment.test.mjs`.
**Modify:** `service.py`, `terminal.py`, `routes.py`, `docker.py`, `acmTypes.ts`, `AcmWorkspace.tsx`, `scripts/verify.ps1`.

**Consumes:** Task 1 runners and `paths.py`. **Produces:** explicit `CODETOP_RUNNER=native|docker`, native consent endpoints and a runner-neutral frontend.

- [ ] Write and run failing tests for selection and both run-entry guards. Start with the existing `loaded` fixture and replace each runner with one whose `kind='native'`; POST batch and terminal requests before consent and expect HTTP 403, no run-history row and no side-effect marker. Accept through `POST /api/v1/runner/consent` with `{'accepted': True}` and verify the same requests then execute. Existing session-token/origin protection must still reject cross-origin consent writes.
- [ ] Implement factory selection: desktop dispatch explicitly sets native, source defaults to existing Docker, `CODETOP_RUNNER` accepts only `native` or `docker`; reject other values. Do not probe Docker to decide the native mode and do not silently fall back. Factory creates batch or terminal runner according to `interactive`.
- [ ] Add a versioned JSON consent file in the active local data directory. Write through a unique pending file and atomic replace. Record scope/version; invalid JSON or wrong version means not accepted. Do not store consent in SQLite settings. Expose GET consent state and strict accepted-true POST; both execution services call the guard before creating/reserving a new task.
- [ ] Add runner kind/display name to both health implementations while preserving existing health keys. Native health validates the selected interpreter and fixed manifest without Docker calls. Include `consent_required` in native health as display information; it must not replace service-side enforcement.
- [ ] Update both service constructors to use the factory. Extend batch shutdown to cancel pending tasks and terminate its active runner tasks before joining the pool; ensure capacity releases exactly once. Terminal shutdown continues to signal sessions and must finish within its existing wait window.
- [ ] Add a frontend helper with this contract:

```typescript
export type RunnerKind='native'|'docker'
export function runnerLabel(kind:RunnerKind,available:boolean):string {
  return `${kind==='native'?'本机 Python':'Docker'}${available?' 已就绪':' 未就绪'}`
}
```

The submission flow checks native consent after saving current code and before calling either terminal-start or batch-start. Present the exact spec disclosure once, POST acceptance only after the user agrees, and preserve draft/selected tests on cancel or failure. Reuse this flow for quick/custom/suite buttons; don't auto-run after an unrelated settings change.
- [ ] Replace hard-coded Docker health/setup copy with mode-aware labels and actionable native error text. Existing Docker setup guidance remains only in Docker mode. New history records display their actual runtime; old records remain unchanged.
- [ ] Test the disclosure's cancel, acceptance, failure/retry and repeat-run behavior with API interactions; verify all quick/custom/suite actions pass through it. Add label tests with literal expected strings and extend `verify.ps1` to run the new frontend test.
- [ ] Run `scripts/verify.ps1` and the new native tests. Verify explicit Docker selection still uses the old command and isolation tests, without requiring Docker for native tests. Inspect a complete backup ZIP and assert neither consent file nor AI key appears in entries.

## Task 3: Desktop paths, frozen launcher and service lifecycle

**Create:** `backend/app/desktop.py`, `packaging/desktop.spec`, `backend/tests/test_desktop.py`.
**Modify:** `paths.py`, `db.py`, `main.py`, `serve.py`, `cli.py` and `scripts/build-desktop.ps1` as needed to expose build entry.

**Consumes:** Task 2 explicit native mode and consent. **Produces:** `CodeTop.exe` dispatch with normal launch, `--serve`, and stopped-service restoration entry modes.

- [ ] Write failing path tests: source root is the repository, frozen asset root is the installed bundle, desktop data uses the local application data directory rather than the EXE extraction directory, and an explicitly passed test data directory is honored. Missing LocalAppData produces a visible actionable error instead of writing to the install directory.
- [ ] Centralize root resolution. Preserve `db.ROOT` as a compatibility export used by current imports/tests, but derive it from `application_root()`. Validate that migration scripts, reference pack, runner runtime configuration, fixed snapshot and frontend manifest resolve inside the bundle. Never use cwd or PATH as an application-root search mechanism.
- [ ] Implement launcher/service modes without a shell. Normal desktop launch takes a single-instance launcher lock, checks the saved service identity/port, reuses only matching application/data identities, starts the frozen EXE in `--serve` mode if needed, polls UTF-8 health, then opens the default browser. Persist no API tokens in command lines or logs. Release the launcher lock after startup; keep the existing service data lock as the final arbiter.
- [ ] Try loopback port 8000 first; if occupied by a different app, bind an available loopback port. Retry boundedly if another process wins the selected port. Browser URL uses the actual chosen port. A saved port file or matching app name alone is insufficient proof of service identity.
- [ ] Use a Windows native message box for startup failure with a short Chinese message and log location. The launcher runs without a console and starts the server hidden. Existing `--close-with-browser` lifecycle and `-NoBrowser` source behavior remain distinct.
- [ ] Add launch tests for matching-service reuse, mismatched root/data, occupied port, concurrent double click, startup crash and timeout. Exercise actual localhost services for identity checks; terminate only test-owned processes. Add a test that closes the final browser WebSocket while an exercise has descendants and asserts both service and its exercise Job finish, while an unrelated process survives.
- [ ] Define the PyInstaller spec with explicit Alembic migration data, SQLAlchemy runtime modules, selected reference/runtime files and assets. Frozen service and launcher share the application executable; a separate unfrozen Python is bundled for exercises. Do not invoke `sys.executable -c` for native exercises in frozen mode.
- [ ] Smoke-build to a fresh `runtime/desktop-build-<unique-id>` directory. Launch the built executable with an explicit isolated data directory, verify initial migrations/import, 1,153 catalog entries, HTML assets and a native run. Do not promote a build that only displays its window but cannot migrate or execute.

## Task 4: Graphical backup restoration with stopped-service ownership

**Create:** `desktop_restore.py`, `RestoreBackup.tsx`, `backend/tests/test_desktop_restore.py`, `frontend/tests/restore-backup.test.mjs`.
**Modify:** `desktop.py`, `DataPanel.tsx`, `backups.py` only for shared non-mutating validation, and the desktop routing/middleware integration.

**Consumes:** Task 3 launcher, existing complete-backup format and `restore_backup`. **Produces:** native desktop restore ticket flow; source recovery commands continue to work.

- [ ] Write failing tests using real backups produced by the existing fixture/database: inspect valid archive metadata and counts; reject corrupted SHA, duplicate/traversal entries, unexpected files, invalid schema, decompression over 256 MiB and missing source files before stopping a live service.
- [ ] Extract reusable read/validation logic from `backups.py` without changing the validated restore semantics. Stage each uploaded archive beneath an opaque restore-request ID. API never accepts an arbitrary user-supplied host path. Preserve current same-origin/token protection. Adjust request-size handling only for the desktop restore upload route, with a bounded 256 MiB archive cap; retain the existing 16 MiB general write cap.
- [ ] Use a two-step API: preview/upload returns a ticket plus version/count metadata, then explicit confirmation atomically publishes a restore request. A desktop launcher helper is started before shutdown, waits for this exact server process/data lock to finish, then performs existing restore in a separate process. No web worker replaces a live SQLite file. If the helper cannot start, leave the original service running and show the failure.
- [ ] Prevent duplicate pending restores, enforce the same data directory, reject arbitrary ticket filenames, and ensure retrying confirmation cannot start two restorations. Success restarts the service and navigates to the actual chosen port. On restore failure, preserve old database and recovery backup, restart the old data and surface an actionable result ticket. Result files contain no secret or arbitrary filesystem paths supplied by the browser.
- [ ] Add the archive chooser and preview/confirmation into existing settings. State clearly that current learning records will be replaced after a backup. Preserve source upload selection on recoverable failures. Polling during restart must tolerate the temporary disconnected server without falsely reporting success.
- [ ] Test stopped-service ordering with real OS locks and database counts. Verify corrupt uploads leave current records unchanged; a valid older-schema backup upgrades on restart; failed restore rolls back; restored learning data does not import consent or Key. Assert a recovery backup exists before replacement.
- [ ] Extend frontend tests and `verify.ps1`, then run the whole suite. Exercise this flow using the frozen EXE rather than only TestClient to catch helper dispatch and lock ownership errors.

## Task 5: Complete installer assembly, provenance and upgrade

**Create:** `scripts/build_desktop.py`, `packaging/CodeTop.iss`, `packaging/runtime-lock.json`, `backend/tests/test_desktop_distribution.py`.
**Modify:** `build-desktop.ps1`, `THIRD_PARTY_NOTICES.md`, `.gitignore` only for build outputs, and application version metadata to `1.6.0` consistently.

**Consumes:** Tasks 1–4 frozen executable, runtime assets, frontend build and recovery UX. **Produces:** installer `dist/CodeTop-Setup-1.6.0-windows-x64.exe`, checksum and provenance manifest.

- [ ] Check for existing build tools before installing any. Prepare only missing official/registry tools in an isolated build environment. Record exact PyInstaller, CPython runtime and Inno Setup versions, source URLs and SHA256 in `runtime-lock.json` before assembly; subsequent builds verify the lock, not mutable latest downloads. Treat the locally available CPython 3.12.13 base interpreter as a candidate to validate, not a portable `.venv` to copy blindly.
- [ ] Write a failing distribution test for an assembler fixture containing application files plus fake personal SQLite/Key/log files. Assert the staged output includes the executable, independent interpreter, standard-library imports, migrations, current frontend, canonical snapshot and license notices, while excluding learning data, machine consent, secrets, old releases and development dependencies.
- [ ] Assemble under a new unique directory through explicit file allowlists. Copy the relocatable base runtime's required executable/DLL/standard-library files and license, without development-machine site-packages, test caches or absolute path configuration. Record every shipped file hash. Validate the relocated interpreter by importing `encodings`, `json`, `sqlite3`, `ssl`, `subprocess`, `threading` and `ctypes` with a deliberately restricted PATH and hostile PYTHONPATH; fail the build if these checks fail.
- [ ] Freeze the application with the prepared spec, bundling backend dependencies and application data. Run frozen smoke checks before invoking the installer compiler. Use new directories rather than PyInstaller cleanup options that recursively remove old output.
- [ ] Write `CodeTop.iss` with a stable AppId, x64 architecture, `PrivilegesRequired=lowest`, default per-user programs directory, Chinese installation flow, desktop/start-menu shortcuts and optional launch-after-install. Upgrade replaces application files without touching `%LOCALAPPDATA%\CodeTopLocal`. Do not use user-data delete directives or bulk cleanup hooks.
- [ ] Produce the installer and checksum with no overwrite. Record its version/build inputs and SHA256. Include third-party licenses for the bundled Python, backend and bundled frontend dependencies; preserve original upstream attribution. Do not redistribute any credentials, local `data/`, arbitrary `runtime/` contents or the build environment.
- [ ] Test missing runtime, altered file hash, wrong architecture and incomplete frontend as hard build failures. Verify installer metadata and shortcuts reference the installed launcher, not repository paths or PowerShell.
- [ ] Install in an isolated current-user test location, open the shortcut and test offline operation. Upgrade a prior test install with saved notes, history and consent, then verify those records survive. Never uninstall/delete the user's current project or use bulk directory cleanup; if disposal of test installs is needed, leave it to the user.

## Task 6: Full verification, public-facing docs and review

**Create:** `docs/docker-free-desktop-acceptance.md`.
**Modify:** `README.md`, `docs/deployment.md`, `docs/user-guide.md`, build/verification entry points and this plan's status checkboxes.

- [ ] Run `scripts/verify.ps1` plus all new native Windows tests, using explicit Docker tests only where the engine is available. Record actual totals, failures, skips and warnings. No new native test is skipped merely because Docker is absent.
- [ ] Run `scripts/build.ps1` and use the root `Start-CodeTop.cmd` to verify the source interface. In explicit native source mode verify the consent dialog, quick run, Unicode interactive input/EOF, stop, custom suite and stored results; verify explicit Docker labels remain accurate. Do not modify the user's formal study database during acceptance; use a separate data directory.
- [ ] Rebuild the complete desktop installer from locked inputs and verify the installed shortcut: catalog, local statement, print/input/read, test comparison, first-run consent, cancellation, stop, backup/download, restoration, Key setup without making a paid AI call, duplicate launch, occupied port and final-tab shutdown.
- [ ] Run in a clean Windows VM/Sandbox without uv/Node/system Python/Docker and with networking unavailable after the installer is present. Confirm installation and all local execution work. If this environment is unavailable, list it as unverified in the acceptance document and final delivery; restricted PATH on the development host is supplementary evidence only.
- [ ] Rewrite README's preferred path around the actual installer: download, install, desktop shortcut. Clearly distinguish the new native desktop release from legacy Docker ZIP/source modes. Explain native file/network access and the first-run confirmation, offline capabilities, backup migration and AI requirements. Link the actual local installer during review; only link a new Release after it is actually uploaded.
- [ ] Inspect the complete diff and artifact manifest for private data and machine-specific paths. Use requesting-code-review for one independent final review, then fix important findings with a failing test and rerun relevant tests/full suite when needed. No independent implementer is dispatched unless the user chooses that execution method.
- [ ] Check spec coverage and record exact installer path, SHA256, machine/environment, test evidence, source-entry acceptance and any clean-machine verification gap. Preserve all builds/backups; no cleanup or automatic Release replacement.

## Execution recommendation and review status

Recommend native execution in the current chat, followed by one independent final review: the launcher, restore helper and native process lifecycle share interfaces, so keeping implementation in one context reduces integration churn. Per-task subagent implementation remains an alternative if the user explicitly chooses it.

The design is approved. This implementation plan is ready for user review; no execution code, dependency installation or installer scaffolding has been changed during planning.


## Execution result — 2026-11-18

- Task 1: implemented and verified with real Windows processes.
- Task 2: integrated; native consent guards, honest labels and history work; Docker remains explicit.
- Task 3: frozen launcher/service works; root source entry and local installed shortcut verified.
- Task 4: graphical preview/restore/restart works in the actual installed EXE; two review regressions fixed.
- Task 5: installer and SHA256 built, installed and upgraded in isolated test paths; 1,781-file manifest checked.
- Task 6: 107 backend and 34 frontend tests passed, TypeScript passed, independent review important findings fixed; documentation updated. Clean Windows VM/offline acceptance remains explicitly unverified and is not represented as passing.

Delivery and exact evidence: `docs/docker-free-desktop-acceptance.md`. Work remains local on `codex/docker-free-desktop`, without commits, pushes, or a new Release. All generated artifacts are retained.
