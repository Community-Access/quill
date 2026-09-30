# QC3: Completed Quality Changes

## 2026-09-30

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