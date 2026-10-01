# QC3: Completed Quality Changes

## 2026-09-30

- Beacon's existing context-help onboarding was extracted into the shared
  Preferences search module to preserve the dialog module's 3166-line budget.
  The budget was not raised. The 12 focused search/Beacon tests passed again.
  Radio's pre-existing mixed-ownership user-guide changes and regenerated
  copies remain outside the isolated search/registry commit.
- Full-worktree banned-pattern gate passed after native search integration.
  Final scoped Ruff checks passed. The first dialog inventory/hardening run
  timed out during repository source scanning, without a mismatch result.
  The rerun with a 300-second per-test limit passed all 7 registry/hardening
  tests; the source scan took 37 seconds, exceeding the default timeout.
  Only the existing unrelated invalid-escape warning was reported.
- Completed QC2 F-07: CommandRegistry checks its creating-thread ownership at
  every public state/dispatch boundary. Worker calls fail before side effects;
  immutable snapshots can travel to workers. The core remains wx-free.
- Validation: 77 registry and Quillin unit/integration tests passed; strict mypy
  on `quill/core/commands.py` reported success. Removed F-07 from remaining work.
- Implemented shared native Preferences/Settings search using existing dialog
  controls and the modal/modeless show contracts; Beacon's local setup installs
  the same helper. Labels, accessible names, and help are indexed, not values.
  Enter navigates without saving; Ctrl+F returns to search; Escape clears first;
  hidden book/Beacon pages are revealed; disabled controls remain disabled.
- Validation: 67 broader Preferences/dialog/Beacon tests passed, followed by
  29 search/dialog tests after modeless onboarding. Live tests cover Lite's real
  constructed dialog, companion controls, and Beacon's hidden Sync panel.
- Full all-app search is NOT complete: Converter, Player, and Inkwell lack a
  unified Preferences entry point; web forms and unopened nested dialogs are not
  indexed. Those gaps and manual screen-reader acceptance remain in QC2 and
  `docs/preferences-search.md`. No release or all-app completion claim is made.
- Focus repair committed as `53406c3`. Settings and focus manual screen-reader
  listening remain outstanding. QC2 now has 10 major findings, several partial.
- Added bounded Lite activation settling (QC2 F-04 implementation): two checks
  at most, invalidated by later activation/deactivation, with menu, visibility,
  shutdown, and intentional-control guards. Focus changes are not announced.
- Validation: 21 focus tests passed, including an actual wx MDI shell, child,
  editor, and Find-like field exercised over five repair/preserve cycles. The
  preceding combined activation/lifecycle run passed 28 tests. Physical Alt+Tab
  and screen-reader listening were not performed and remain tracked acceptance.
- Settings recovery committed as `6eaab53`; inbox shutdown as `fb9f32d`;
  shared callback lifetime as `84de01d`. No changes pushed or released.
- Fixed the silent Lite settings-write failure (QC2 F-01 implementation).
  Failures retain session values, expose a dirty-state warning in the status
  message, and report a safe diagnostic without exception text or user paths.
  Preferences no longer falsely claims success; reopening it retries already
  accepted settings. Pending warnings coalesce and flush before shutdown.
- Validation: 50 settings, status, Preferences, and lifecycle tests passed,
  including a real failed filesystem write followed by a successful atomic
  save, stale warning suppression after retry, and close with a pending warning.
- Updated Lite's PRD, user guide, unreleased release notes, announcement, and
  the family changelog. Their HTML/EPUB copies are regenerated with each commit.
- F-01 remains only for direct Activity/Problems actions, other persistence
  writers, and manual screen-reader acceptance; no claim that these are built.
- Added shared task callback lifetime guards. Shutdown suppresses success,
  failure, and progress delivery, including callbacks queued before shutdown
  and work finishing afterward. Optional per-surface tokens are one-way and
  independent of cancellation; replacement surfaces use new tokens.
- Preserved worker results in task futures without blocking `wait=False`
  shutdown. No persistent Activity/Problems surface is claimed.
- Added regressions for queued success/failure/progress, repeated invalidation,
  replacement tokens, running work after shutdown, and retained results.
- Validation: 12 focused task-manager tests passed.
- Completed QC2 F-03: Lite has one idempotent application timer shutdown owner,
  called by confirmed Exit, shell close, and final `OnExit`. Queued inbox ticks
  do not consume pending requests after shutdown. Requests remaining after a
  reentrant close are reposted; cancelled close keeps the app active. Deferred
  launch-update checks do not start after shutdown.
- Validation: 23 Lite construction, lifecycle, and update tests passed, including
  forced close, veto, repeated finalization, pending requests, and delayed checks.
- Updated Lite's PRD, user guide, unreleased release notes, and announcement.
- The first commit's isolated banned-pattern hook saw unrelated Cast dialogs
  without their existing staged inventory. The same gate passed in the full
  working tree; only that hook was skipped for the isolated commit. Formatting,
  lint, module budget, and generated-doc parity hooks passed.
- Updated the main PRD and changelog; trimmed the completed portion of QC2
  F-02 while retaining per-surface adoption and activity-history work.
- Existing staged and unstaged work is outside these commits unless explicitly
  recorded here. No changes have been pushed or released.