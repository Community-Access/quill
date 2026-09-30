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
- Updated the main PRD and changelog; trimmed the completed portion of QC2
  F-02 while retaining per-surface adoption and activity-history work.
- Existing staged and unstaged work is outside these commits unless explicitly
  recorded here. No changes have been pushed or released.