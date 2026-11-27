# QUILL work record

Updated: 2026-11-26

This is the only status file for QUILL. It replaces `report2.md` (human and external checks) and `report3.md` (deferred branch queue), which have been folded in here and deleted.

The file has three separate parts. Don't mix them:

1. **[Code work](#part-1-code-work)** is what someone has to build, fix or change in the repository, in priority order.
2. **[Repository cleanup](#part-2-repository-cleanup)** covers worktrees, folders and branches: what was removed, what remains, and what happens to each remaining branch.
3. **[Human checks and external blockers](#part-3-human-checks-and-external-blockers)** is what only a person, a real service, a real install or another project can confirm. None of it counts as missing code.

Ideas in `new.md` (Gitview, Drop Deck, EdSharp, AccessCode and BlindPilot comparisons) are **new feature ideas**. They are not Beta work and are not counted anywhere in this file.

## Where things stand

- `main` is at `038d6609b` (PR #2084, protected batch feed promotion), and the root checkout `D:\QUILL` is level with `origin/main`.
- Git now has **one** registered worktree: the root checkout. Every other worktree has been removed (see [Cleanup log](#cleanup-log-2026-11-26)).
- Every branch that held unique work is on GitHub. Nothing exists only on this PC.
- Open PRs: only **#2003** (SwiftLetter follow-ups, deliberately deferred).
- **Being verified now:** five read-only reviews are checking every remaining branch, plus whether GitHub, WordPress, Scribe, startup and the family-UX milestones are really complete on `main`. Sections marked *Pending review* get their verdicts when those reviews finish.

---

## Part 1: Code work

Items are ordered by how much they block a trustworthy 11-app Beta. "Done when" is the test that removes the row.

### 1.1 Beta blockers

| # | Work | Why it matters | Done when |
|---|---|---|---|
| 1 | **Verify startup is finished across all 11 apps.** Main's plan listed six startup items: profile read before optional imports; minimal and Notepad mode defers heavy features; essential behaviour stays in the core; profile switching keeps the open document; installed-build timing for all 11 apps; Lite gain of at least 25.5 percent. PR #2083 landed most of this. *Pending review.* | Startup speed and launch safety are the first impression of every app. | Each item is marked done with evidence, or the remaining gap is fixed in one green PR. |
| 2 | **Verify Scribe is complete**, including the switch to the Pneuma ETA progress contract. Confirm no code path still uses the old progress method, and that tests cover the new contract. *Pending review.* | Scribe is a headline integration, and the provider's API changed. | The review confirms main is complete, or the gaps land in green PRs. |
| 3 | ~~Verify the GitHub Workbench is complete.~~ **Verified complete as code (2026-11-26).** 99 of 100 live requirements are Met, and the API coverage gate shows nothing still planned (`planned_ceiling: 0`). Roadmap GX01 to GX16 have all shipped. The one Partly-met item, GH-R-119, needs human help sessions (see Part 3). | | Done. |
| 4 | **Verify the WordPress Workbench and Practice Site are complete** against their own plan. SwiftLetter is excluded (see 1.3). *Pending review.* | Same as above. | Verdict recorded, with any code gap fixed. |
| 5 | **Fix the Dependabot alerts in `scripts/wp_playground/package-lock.json`**: `isomorphic-git` to 1.38.6 (1 high: arbitrary file write through a directory symlink; 3 moderate) and `qs` to 6.16.1 (2 moderate). | A high-severity alert on `main` is a release risk if this tooling ships with the packaged Practice Site, and noise if it doesn't. | Lockfile updated in a green PR, and `main` shows no open high alerts. |
| 6 | **Cast: automatic feed check never runs in standalone Cast.** The fix is in `train/handoff-cast` commit `f3003b03a` (same fix as `claude/festive-meitner-3e3470`). On `main`, `quill/ui/podcasts/startup_bootstrap.py` (around line 151) and `new_feed_check.py:23` read `host.settings or host._podcast_history`, but Cast Preferences write the switch to `PodcastHistory`. So "Look for new episodes on a schedule" can never turn on. Changing only the interval is also ignored until restart, and per-show schedules are ignored. | A core feature of a pilot app silently does nothing. | One small PR, hand-ported because #2083 moved the monitor setup: about 60 lines plus the 204-line test `test_cast_check_reads_history.py`. Then delete both source branches. |
| 7 | **Cast: download status is written to a fixed column.** `SetItem(row, 3, …)` in `manager_downloads.py:115`, `manager_downloads.py:124` and `manager_phase4.py:348`, but Episodes columns are user-configurable. | It overwrites the wrong cell, or targets a column that doesn't exist. | A PR of about 30 lines plus a test, using `_set_episode_state_cells` (write by column id) from `feat/m13-cast-radio-player` and covering all three call sites. |
| 8 | **QUILL and Lite crash recovery loses drafts.** `recovery.begin_session` offers only the newest snapshot, and only when the log shows an error. After a power cut or forced close, nothing is offered, and a second unsaved document is never offered. | Real draft loss in the flagship editor. | Land `feat/m6-quill-lite` (about 800 lines with tests; those files are unchanged on `main`, so no conflicts). |
| 9 | **Damaged files are silently overwritten.** A damaged `abbreviations.json` loads the defaults and the next save overwrites the user's file; a damaged GitHub drafts file is overwritten; a Beacon rollback can't be undone. | Silent data loss. | Land the data-safety core of `feat/m6-drafts-backups` (about 500 lines; low conflict risk). |
| 10 | **Chapter Workbench Close discards unsaved chapter and tag edits without asking.** | Silent loss of edits. | Land only the Close prompt from `feat/m6-radio-studio`: `chapter_workbench.py`, `chapter_workbench_edits.py`, and the test, about 150 lines. |
| 11 | **Lite never resumes Scribe jobs left running at launch, and Transcribe exit discards a running queue without asking.** | A functional gap if Scribe ships in Lite for Beta. | Land those two pieces of `feat/m6-transcribe-converter` (about 200 lines). Expect conflicts in `lite.py`, `lite_window_scribe.py` and `transcribe.py` after #2083. |
| 12 | *Optional one-liner:* `quill/ui/dictation_transcription.py:55` calls `frame._speech_provider(registry=registry)`, but `MainFrame._speech_provider` takes no arguments. It raises TypeError only when the provider ladder returns an id that isn't registered. | A latent crash. | Fix the call, or the signature. |

### 1.2 Release engineering (the Beta path)

Run these in order from a single merged `main` commit. Don't build from a feature branch.

1. **Run the 11-app Dev build matrix:** `gh workflow run dev-builds.yml -f force=true`. Every product must produce its installer, portable ZIP, checksums, notes and expected version. Inspect all 11 before rerunning; fix shared packaging defects once, then rerun only the failed apps.
2. **Build and inventory the shared Windows runtime locally**, then run the skipped runtime-inventory gate:

   ```powershell
   .\build.ps1 runtime
   python scripts\check_runtime_inventory.py standalone\runtime\dist\QuillVilleRuntime
   python -m quill.tools.platform_report
   ```

   If the Dev workflow is unavailable, the fallback is `.\build-quill-apps.ps1 all -KeepGoing`. After that, rerun only failed apps with `-SkipRuntime`.
3. **Smoke test the exact artifacts that will become Beta.** For each app, installed and portable, on clean data: first launch, one useful action, persistence after restart, clean exit, and an update check. Also confirm that Stable, Beta and Dev data roots and runtime slots don't overwrite each other. A failure in the shared runtime blocks every product; a failure in one app blocks only that app.
4. **Promote the same binaries to Beta** with the batch workflow from #2084. Do a dry run first:

   ```powershell
   gh workflow run release-feed-batch.yml -f sha=<dev-build-sha> -f dry_run=true
   ```

   ```powershell
   gh workflow run release-feed-batch.yml -f sha=<dev-build-sha> -f dry_run=false
   ```

   Approve the protected signing job once, merge the single signed-feed PR, and verify all 11 feeds and the signed index. Don't rebuild between Dev and Beta.
5. **Run installed-build startup timing for all 11 apps** on the final build.
6. **Release, observe, repair narrowly.** Publish one announcement naming the 11 products, their hashes, known rough edges and feed locations. A release-blocking defect gets a rebuild of only the affected app. Never overwrite tags or artifacts.

### 1.3 Documentation gate (before announcing Beta)

Every reader-facing document must match what `main` actually ships:

- the QUILL and QUILL Lite user guides
- each app's guide and help
- release notes and What's New
- `CHANGELOG.md`
- `docs/release/RELEASE.md`
- the generated EPUB, HTML and DOCX copies of all of the above

Regenerate the outputs from their Markdown sources **once**, after the last code merge, not piecemeal.

**Done when:** the docs parity and help-reference gates pass, each app's What's New names its Beta changes, and no guide documents a menu or feature that a new install doesn't have. The `View > Load More` mismatch in PR #2003 is the known example.

### 1.4 After Beta

| Work | Notes |
|---|---|
| **Retire the separate Dev-builds repository** (`Community-Access/quillville-dev-builds`) | **Requirement: anyone in the public must be able to download Beta and Dev builds**, both from a release page and through the in-app update channel, without signing in. Publishing Dev builds as clearly labelled prereleases in the public `Community-Access/quill` repository meets this. Also add a public download page that lists the current Stable, Beta and Dev build for each app. `main` still depends on the separate repository today: `dev-builds.yml` publishes unsigned Dev builds there, and `release-feed-batch.yml` promotes Beta from those releases using `DEV_BUILDS_TOKEN`. To retire it, change `dev-builds.yml`, `scripts/publish_release.py` and `scripts/promote_release_batch.py` so Dev builds publish as prereleases inside `Community-Access/quill`, make the batch promotion read them there, and update `docs/release/RELEASE.md`. Delete the repository only after one full Dev → Beta cycle works without it. Deleting the repository is the owner's action. |
| **SwiftLetter Phase 1** (PR #2003 stack) | Blocked on SwiftLetter PR #11 publishing updated contract fixtures. Then: fix the failing docs-contract shard (`View > Load More`), address review comments, sync fixtures, and finish the editor wiring (open an article, Save to SwiftLetter, Compare and Retry, lossless Markdown and HTML round trips). |
| **Reuse system Whisper resources** | The full plan is under [Future plan](#future-plan-reuse-system-whisper-resources). It starts only after Beta. |
| **Ideas in `new.md`** | Product ideas, not commitments. Review them after Beta. |

---

## Part 2: Repository cleanup

### Goal

`main` is the single build source. Every other branch is either landed and deleted, or kept on GitHub with a written reason in [Branch queue](#branch-queue). No worktree folders remain on disk.

### Cleanup log (2026-11-26)

| Action | Detail |
|---|---|
| Merged | PR #2084 (`train/batch-release-feed`), admin squash `038d6609b`. |
| Synced the root checkout | `D:\QUILL` fast-forwarded 37 commits to `origin/main`. Local notes were backed up first. |
| Pushed local-only branches | `codex/coverage-stage1-2026-11-11`, `docs/github-f1-pass`, `fix/settings-apps`, `fix/swl-browse-review`, and `worktree-agent-a3cb8ce7ee947a5d9` (pushed as `rescue/agent-a3cb8ce7ee947a5d9`). |
| Removed registered worktrees | `D:\wt\lite-build` and `D:\wt\lite-main`: commits already on `main`; their only changes were regenerated EPUB and HTML with no Markdown source edits. `D:\wt\swiftletter`: its one untracked reply draft was saved to the backup folder. `.claude\worktrees\gh-verify-object-lifecycles` and `.claude\worktrees\wp-live-run`: clean, branches on GitHub. |
| Deleted branches already in `main` | `train/batch-release-feed`, `fix/lite-listening-mutagen`, `fix/lite-ffmpeg` and `feat/radio-add-folder-path`, locally and on GitHub where present. Their tips are recorded in the backup folder's `deleted-branches.txt`. |
| Folded status files into this one | `report2.md` and `report3.md`. |

### Why the S: paths stopped mattering

Twenty-three orphan folders had `.git` pointers to `S:/QUILL/.git/worktrees/...`. That is this repository's path on the other PC, `D:` here. The worktree metadata those pointers need no longer exists on either drive, so remapping the drive letter (for example with `subst`, which needs no admin rights) would not have revived them. They are handled as plain folders of files instead.

The test applied to each folder: hash every file it contains, then check each hash against every file version reachable from any branch or tag. A folder with zero unmatched files contains nothing that Git doesn't already have.

### Orphan folders: verdicts

All 24 folders were scanned, and all 24 were deleted on 2026-11-26.

| Folder | Unique files | Result |
|---|---|---|
| `D:\wt\quill-github-tokens`, `D:\wt\pr-1801`, `D:\wt\quill-radio-folder` | 0 | Deleted. |
| `D:\wt\quill-secrets` | 29 | Despite the name, it held **code, not credentials**: an older copy of the GitHub Actions secrets feature, which `main` already has. The 29 files were copied to `D:\quill-local-backup-2026-11-26\quill-secrets-unique`, then the folder was deleted. |
| `.claude\worktrees\agent-*` (19 folders) and `festive-meitner-3e3470` | 0 | Deleted. The only ignored files were regenerable: `.claude/` session settings, generated CHANGELOG EPUB and HTML, and downloaded podcast models. |

### Other contents of `D:\wt`

| Item | What it is | Plan |
|---|---|---|
| `preserved-beta-builds` (214,169 files) | Build trees from five old branches: `build/deps` (including `wordpress-7.1.4.zip`), dictation models and Python, launcher, and the Lite and runtime build folders. Also `orphan-key-snapshot/quill-pub.key`, which is the same public key as the root copy apart from its line ending. | **Low risk to delete.** Everything here is either regenerated by a build from `main` or downloaded by the build. The Beta builds must come fresh from `main` anyway. It is the owner's decision; I recommend deleting it once the first Beta build succeeds. |
| `release-notes-backup-20261109` (4 files) | Old release-notes drafts: QUILL 1.0.0, Lite 2.0, Radio 3.2, Cast 2.0. None is identical to what is in Git. | **Copied** to `D:\quill-local-backup-2026-11-26\release-notes-backup-20261109`, so the folder can be deleted with no loss. |
| `voice-prototype`, `swl-client`, `ext` | Separate prototypes or tools, not QUILL worktrees | Identify each. Keep and relocate any that are their own project; delete the rest. |
| About 80 loose files | Old helper scripts, transcripts, PR conflict notes, gateway compose files, `jev_*` evaluation data, plans | Keep anything not already in a repository by moving it to the backup folder; delete the rest. |

### Branch queue

**Progress on 2026-11-26:** the branch count went from 89 local to 34 local. 62 branches were deleted after verification. Each verification used content, not ancestry, because `main` squash-merges: every file the branch added had to exist on `main`, commit subjects were matched to the squash-merge train bodies, and the cited PRs had to be on `main`. Deleted:

- **GitHub family (18):** all `gh/*`, `feat/github-*`, `docs/github-*` and `deferred/github-*` branches, plus `claude/command-key-phase3-jev`. Superseded by #1991, #1809, #1830, #1833, #1835 and #1801.
- **Family UX (31):**
  - FUX-04/06/02/07/08: all of M1, M2 (except the workbench branch), M4, M7 and M8, plus `train/family-m1-m2-m7`.
  - FUX-09/10/11/12/14/15: all of M9 to M12, M14 and M15. Superseded by #2052, #2065 and #2068.
- **Other (9):**
  - `feat/scribe-live-regression` and `feat/mobi-reading` (#2028)
  - `codex/coverage-stage1-2026-11-11` (a throwaway coverage run)
  - `wip/auphonic-backlog` (#1779)
  - `wip/dictation-benchmarks`
  - `fix/ai-and-settings-legible` (audit findings already fixed on `main`)
  - `train/batch-release-feed`, `fix/lite-listening-mutagen`, `fix/lite-ffmpeg` and `feat/radio-add-folder-path`
  - the stale `pr/1999` and `pr/2000` refs (squashed into `feat/swiftletter`)

**Remaining branches and their verdicts:**

| Branch | What it is | Verdict |
|---|---|---|
| `train/handoff-cast`, `claude/festive-meitner-3e3470` | Cast automatic feed check fix | **Land** as Beta blocker 6, then delete both. |
| `feat/m13-cast-radio-player` | FUX-13 availability wording, plus the Cast column fix | **Land** the column fix only (Beta blocker 7), then delete. `train/media-recovery` holds a newer copy of the rest. |
| `feat/m6-quill-lite` | FUX-05 QUILL and Lite crash recovery | **Land** (blocker 8), then delete. |
| `feat/m6-drafts-backups` | FUX-05 damaged-file protection | **Land** (blocker 9), then delete. |
| `feat/m6-radio-studio` | FUX-05 Chapter Workbench Close prompt, plus Radio and Studio wording | **Land** the Close prompt (blocker 10). **Keep** the wording for after Beta. |
| `feat/m6-transcribe-converter` | FUX-05 Lite Scribe resume and Transcribe exit question, plus wording | **Land** those two pieces (blocker 11). **Keep** the wording. |
| `train/editor-recovery` | An aggregate: exactly `feat/m6-quill-lite` plus `feat/m16-editors` | **Delete** after blocker 8 lands. |
| `feat/m13-workbench-weather-beacon` | FUX-13 freshness wording | **Delete**; `train/media-recovery` has the same or newer copy. |
| `feat/m2-workbench` | FUX-06 Workbench refresh | **Delete**; the canonical copy is `train/workbench-sets` commit `a37fd7c76`. |
| `train/workbench-sets` | `a37fd7c76` keeps Workbench list place on refresh; `62a01151c` is durable Scribe document sets (core only, no UI) | `a37fd7c76` is an optional small **Land** (4 files, no conflicts). **Keep** the sets commit for after Beta, with `feat/scribe-sets`. |
| `feat/scribe-sets` | Named Scribe document sets, Set Details dialog | **Keep**, after Beta. Rebase onto the durable queue (#2075) and the ETA contract (#2078); conflict risk is high. |
| `feat/m5-radio-studio` | FUX-03 "Where Is the Sound?" (Alt+Shift+A) | **Keep**, after Beta. It's a new feature with a new key. |
| `feat/m16-editors` | FUX-16 plain-language failure boxes | **Keep**, after Beta. Wording and buttons only. |
| `train/media-recovery` | The canonical source for FUX-13, M5 and M6 media wording | **Keep**, after Beta, and re-split it into small PRs. **Never merge it as is:** its `main_frame_radio.py` would undo #2083's startup deferral. Drop its root `.audit-*.patch` files. |
| `fix/settings-apps` | Ordered settings writes (on `main` via #1979, #1986 and #1990) | Check one leftover test, `tests/unit/apps/test_converter_settings_save.py`. Land it if it still passes; otherwise delete the branch. |
| `worktree-agent-a3cb8ce7ee947a5d9` / `rescue/agent-a3cb8ce7ee947a5d9` | WordPress Workbench 15.12 "Change Everywhere" | Reported as reimplemented on `main` under different file names (`workbench_across_ops.py`; #1834, #1837, #1842). Its 8 added files have different names on `main`, so **confirm in the WordPress review, then delete**. |
| WordPress: `wp/*` (2), `wp-finish/*` (5), `feat/wordpress-*` (3), `deferred/wordpress-workbench-15-12`, `docs/wp-live-run` | WordPress Workbench work | **Review not finished** (stopped by the usage limit). |
| SwiftLetter: `feat/swiftletter`, `feat/swiftletter-client-followups` (PR #2003), `fix/swl-browse-review` | SwiftLetter Phase 1 | **Keep**, deferred. Collapse into one stack when the fixtures arrive. |

Verdict types used for the remaining branches:

- **Land:** small, self-contained, not on `main`. It goes through its own PR with green CI.
- **Consolidate:** it overlaps another branch, so it is folded into one canonical branch and the duplicate is deleted.
- **Keep:** major feature work, left until after Beta with a written reason.
- **Delete:** already on `main` or superseded.

What is already known about the 88 remaining branches:

- 83 already have identical copies on GitHub, so local deletion loses nothing.
- None merges cleanly into `main` unchanged. Most are 17 to 200 commits behind and touch generated docs, so landing anything means a fresh, small PR against current `main`, not a merge of the old branch.
- The aggregate `train/editor-recovery`, `train/media-recovery` and `train/family-m1-m2-m7` branches overlap the focused `feat/m*` branches. They are preservation snapshots, not merge candidates.
- Paused work on GitHub only: `wip/auphonic-backlog` (unfinished, untested, about 4,400 lines), `wip/dictation-benchmarks`, and `fix/ai-and-settings-legible` (unverified audit findings).

Families under review:

| Family | Branches |
|---|---|
| GitHub Workbench | `gh/*` (7), `feat/github-*` (4), `docs/github-*` (4), `deferred/github-*` (2), `claude/command-key-phase3-jev` |
| WordPress and SwiftLetter | `wp/*` (2), `wp-finish/*` (5), `feat/wordpress-*` (3), `deferred/wordpress-workbench-15-12`, `docs/wp-live-run`, `feat/swiftletter`, `feat/swiftletter-client-followups`, `fix/swl-browse-review` |
| Family UX M1 to M8 | `feat/m1-*` through `feat/m8-*`, `train/family-m1-m2-m7`, `train/editor-recovery`, `train/handoff-cast`, `train/workbench-sets` |
| Family UX M9 to M16 and others | `feat/m9-*` through `feat/m16-*`, `train/media-recovery`, `feat/scribe-sets`, `feat/scribe-live-regression`, `feat/mobi-reading`, `fix/settings-apps`, `claude/festive-meitner-3e3470`, `codex/coverage-stage1-2026-11-11`, `rescue/agent-a3cb8ce7ee947a5d9`, `wip/*`, `fix/ai-and-settings-legible`, `pr/1999`, `pr/2000` |

### Recovery

Everything removed today can be recovered:

- **Backup folder:** `D:\quill-local-backup-2026-11-26`
  - `root\untracked.tar`: the root checkout's local notes and the two locally regenerated EPUBs, taken before the sync.
  - `swiftletter\issue-1992-reply.md`: the private SwiftLetter reply draft. Don't publish it without approval.
  - `deleted-branches.txt`: the name and tip hash of every deleted branch. To restore one, run `git branch <name> <hash>`.
- **Pushed branches:** every branch with unique work is on `origin`.

---

## Part 3: Human checks and external blockers

These need a person, a real service, a real Windows install, assistive technology, or another project. They are not code gaps.

### Credentials and operations

- [ ] Restore `DEV_BUILDS_TOKEN`. While the Dev-builds repository exists, the Dev build and batch promotion need it.
- [ ] Set `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET` for Cast's Dev search, or decide explicitly to ship the first Beta without Podcast Index search.
- [ ] Approve the protected `release-feed-batch.yml` signing job once per Beta promotion.

### Human validation

- [ ] NVDA, JAWS and Narrator checks for shipped dialogs and family journeys.
- [ ] Clean installed and portable updates on real machines.
- [ ] Stable, Beta and Dev side by side on real Windows installs.
- [ ] Real Scribe, Moonshine, OCR, clipboard, display and Windows integration.
- [ ] GitHub live-role, protected-branch, organization, secret and Copilot-plan scenarios.
- [ ] GH-R-119: timed "find the answer in help" sessions with about five people, using the kit in `docs/qa/github-help-sessions.md`. This is the only GitHub requirement not yet Met.
- [ ] WordPress live-site, payment, OAuth and packaged Practice Site scenarios.
- [ ] Screen-reader verification of Cast list stability and Lite handoffs.

### External blockers

- The original Lite `0xc0000374` crash component is still unidentified. Diagnostics are better, but the native cause is not claimed fixed.
- SwiftLetter PR #11 has not published updated contract fixtures for its merged #13 and #17 server changes. That blocks QUILL PR #2003's sanitized-save and changed-since-review replay.

---

## Future plan: reuse system Whisper resources

Start this only after Beta. The goal is to save model and engine storage without making another project a hidden dependency.

### Preserve the supported baseline

- Keep QUILL's CPU/int8 Faster Whisper path fully supported.
- Keep the automatic CUDA/float16 choice when CTranslate2 detects a usable GPU.
- Don't require a GPU, CUDA, another Python installation or another app.
- Don't scan the whole disk or run a program found unexpectedly on `PATH`.

### Safe model discovery and adoption

- Inspect only documented model-cache locations and folders the user selects.
- Recognize only catalogued Faster Whisper CTranslate2 model layouts, not any folder that happens to contain `model.bin`.
- Verify model family, revision or format, required files, size and recorded SHA-256 before offering adoption.
- Offer one explicit choice: reference the existing model, hard-link it where the file system allows, or copy it into QUILL-managed storage.
- Beside reference mode, explain that removing or changing the other project can break the reference.
- Keep a QUILL-owned metadata record for each adopted model, and revalidate it before transcription.
- If an adopted model disappears or fails validation, disable it for the session and offer QUILL's managed download or the CPU fallback.

### Optional external-engine detection

- Detect a known Faster Whisper installation only in an environment the user approves.
- Probe a compatible `faster-whisper`, CTranslate2 and Python combination in an isolated process. Never import an external environment into QUILL's main interpreter.
- Verify version, ABI, device availability, model compatibility and exit behaviour before enabling it.
- Label the engine clearly as external, and keep QUILL's managed engine as the repair path.
- Never reuse an arbitrary `whisper` or `whisper.exe` command: whisper.cpp, open-source Whisper and Faster Whisper don't share a command contract.

### Updates and consent

- A detected engine or model stays optional; QUILL never adopts or activates one without an explicit user action.
- Revalidate after QUILL, the other app, Python, CUDA or CTranslate2 changes.
- Don't use the network silently while probing external installations.
- QUILL removes only its own copies, links and metadata, never the other project's storage.

### Verification

- Unit tests for model-layout validation, checksums, missing files, broken references, hard-link fallback, incompatible versions, CPU fallback and external-process failure.
- Live Windows tests for installed QUILL, portable QUILL, CUDA, no CUDA, model removal during a session, and use alongside another Whisper project.
- Measure download and engine footprint, model duplication, startup cost, first and warm transcription, and uninstall behaviour.
- Document the external-resource risk and update the speech privacy and network audit before shipping.
