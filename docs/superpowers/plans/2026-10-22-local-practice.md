# Local practice implementation plan

**Goal:** Keep the catalog homepage and add an on-demand local statement / Python ACM practice dialog.

**Architecture:** Reuse the detail API, note storage, ACM workspace and Docker runner. A new native dialog owns fresh detail loading and one note draft, keeps the ACM workspace mounted across tabs, and flushes both code/notes and test drafts before closing. No schema or runner change.

**Scope approved:** User approved the in-chat proposal and explicitly requested implementation on 2026-10-22. Execute here without another approval cycle. Keep all existing files, data and releases; do not perform bulk deletion. Work in the requested checkout so the local build can be used directly; do not commit or publish automatically.

## Tasks

- [x] 1. Add regression tests for a local title button with an independent safe source link, and closing only after both save guards succeed. Run the tests before implementation.
- [x] 2. Add ProblemEntry and PracticeDialog. Preserve existing notes entry, filters, paging, focus return and homepage scroll. Show statement / notes on the left, code and tests on the right; provide mobile tabs and maximize.
- [x] 3. Reuse ACM workspace, make local ACM sample wording explicit, show environment setup guidance and safe loading failures. Keep reference solutions collapsed.
- [x] 4. Run verify.ps1, build a retained release, and exercise statement, sample load, actual Docker run, immediate close/reopen, notes, absent statement/sample, mobile and dark theme against an isolated data directory.
- [x] 5. Review the change, update README and acceptance evidence, verify production learning data is unchanged, and show the updated local app.

## Review focus

- Fresh revisions on each open; no stale draft overwrites.
- Save failure blocks closing and leaves export/retry controls available.
- Switching tabs keeps test guards and draft holders alive.
- Missing Docker only disables running; reading and editing remain usable.
- Separate original statement examples from explicitly defined local stdin/stdout cases.

## Completion record

43 backend tests passed, 14 frontend tests passed, TypeScript and release build passed. 13 opt-in backend Docker/reference tests skipped; actual browser Docker sample 1/1 and builtin suite 4/4 passed. Independent review issue fixed with inert body regression; global close failure feedback also added. No unresolved review findings. See docs/local-practice-acceptance.md for browser and data integrity evidence.
