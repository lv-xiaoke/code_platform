# Interactive terminal implementation plan

**Goal:** Add real interactive stdin/stdout to the approved simple run flow.

**Spec:** ../specs/2026-10-22-interactive-terminal.md

**Architecture:** A container-only supervisor forwards JSON-line input to a resource-limited child and wraps its streamed output. A bounded server manager owns sessions, idempotent writes and persistent history. Existing authenticated HTTP APIs poll snapshots. Frontend terminal keeps input/EOF/stop controls and integrates stopping with the practice close guard. No dependency/schema change.

- [x] Write API and actual Docker regression tests; confirm missing feature failures.
- [x] Implement container worker, host runner, bounded session manager and API/lifespan wiring. Verify the new tests with real Docker.
- [x] Implement terminal panel, polling, idempotent input and close/stop guard; preserve optional batch input and advanced test execution.
- [x] Run full checks, review, build and test UI against an isolated acceptance service; fix concrete findings and verify fixes.
- [x] Record acceptance, compare production table fingerprints, deploy retained local release and open it.

Review focus: stop during startup/output flood; duplicate input after a lost response; EOF after pending input; Unicode chunk boundaries; child descendants; expired/missing Docker; concurrent sessions; close with pending startup/input; completed run persistence and startup interruption. Do not remove host files or old releases.

## Verification record

56 backend tests passed with CODETOP_TERMINAL_TESTS=1, 24 frontend tests passed, TypeScript and final build passed. 13 pre-existing optional batch/reference tests skipped. Real Docker verifies prompts, Unicode, repeated input, EOF, stop, descendants, isolation and limits. Review findings for aggregate CPU and supervisor FDs reproduced and fixed with RED/GREEN tests; focus also fixed. Browser writes used isolated preview only. Production 14-table fingerprints unchanged. See docs/interactive-terminal-acceptance.md.
