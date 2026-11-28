# QUILL work record

Updated: 2026-11-26

This is the only status file for QUILL. It replaces `report2.md` (human and external checks) and `report3.md` (deferred branch queue), which have been folded in here and deleted.

The file has three separate parts. Don't mix them:

1. **[Code work](#part-1-code-work)** is what someone has to build, fix or change in the repository, in priority order.
2. **[Repository cleanup](#part-2-repository-cleanup)** covers worktrees, folders and branches: what was removed, what remains, and what happens to each remaining branch.
3. **[Human checks and external blockers](#part-3-human-checks-and-external-blockers)** is what only a person, a real service, a real install or another project can confirm. None of it counts as missing code.

Ideas in `new.md` (Gitview, Drop Deck, EdSharp, AccessCode and BlindPilot comparisons) are **new feature ideas**. They are not Beta work and are not counted anywhere in this file.

## Where things stand

- **Branches: 89 → 11**, the same 11 locally and on GitHub. **Worktrees: 30 folders → 1**, the root checkout `D:\QUILL`. Every deleted branch's tip hash is logged in `D:\quill-local-backup-2026-11-26\deleted-branches.txt`.
- **All six Beta fixes found by the branch review are merged:** #2086, #2087, #2088, #2089, #2090 and #2091.
- **Verified complete as code on `main`:** GitHub Workbench, WordPress Workbench and Practice Site, and Scribe (including the Pneuma ETA contract). Their remaining items are human or live checks (Part 3).
- **Still to verify:** startup across all 11 apps (item 1).
- **Next code work:** publish Dev builds inside the monorepo (1.2, step 0), which is required before any Dev or Beta build can run.
- Open PRs: only **#2003** (SwiftLetter follow-ups, deliberately deferred).

---

## Part 1: Code work

Items are ordered by how much they block a trustworthy 11-app Beta. "Done when" is the test that removes the row.

### 1.1 Beta blockers

| # | Work | Why it matters | Done when |
|---|---|---|---|
| 1 | **Verify startup is finished across all 11 apps.** Main's plan listed six startup items: profile read before optional imports; minimal and Notepad mode defers heavy features; essential behaviour stays in the core; profile switching keeps the open document; installed-build timing for all 11 apps; Lite gain of at least 25.5 percent. PR #2083 landed most of this. *Pending review.* | Startup speed and launch safety are the first impression of every app. | Each item is marked done with evidence, or the remaining gap is fixed in one green PR. |
| 2 | ~~Verify Scribe is complete.~~ **Verified complete as code (2026-11-26).** The Pneuma ETA contract is implemented in `model.py` (#2078): whole milliseconds, MP3 speech only, `null` for unknown. The only consumer reads it through that parser, so no old progress path remains. 505 Scribe tests pass; 106 are live tests skipped without the corpus and account (Part 3). `feat/scribe-sets` is a new feature for after Beta. | | Done. |
| 3 | ~~Verify the GitHub Workbench is complete.~~ **Verified complete as code (2026-11-26).** 99 of 100 live requirements are Met, and the API coverage gate shows nothing still planned (`planned_ceiling: 0`). Roadmap GX01 to GX16 have all shipped. The one Partly-met item, GH-R-119, needs human help sessions (see Part 3). | | Done. |
| 4 | ~~Verify the WordPress Workbench and Practice Site are complete.~~ **Verified complete as code (2026-11-26).** Section 15.12 Across Sites (Make Them the Same for terms, plugins, settings, people, patterns, menus, styles and the network) is in `workbench_across_ops.py`. The newest recorded live run is 173 passed, 0 failed, 33 need you, 10 not run. All 13 WordPress branches were superseded and deleted. | | Done. |
| 5 | **Fix the Dependabot alerts in `scripts/wp_playground/package-lock.json`**: `isomorphic-git` to 1.38.6 (1 high: arbitrary file write through a directory symlink; 3 moderate) and `qs` to 6.16.1 (2 moderate). | A high-severity alert on `main` is a release risk if this tooling ships with the packaged Practice Site, and noise if it doesn't. | Lockfile updated in a green PR, and `main` shows no open high alerts. |
| 6 | ~~Cast: automatic feed check never runs in standalone Cast.~~ **Fixed: merged in #2086.** `check_settings` reads the store each app's Preferences writes. A cadence-only change takes effect at once, and each show's own schedule decides when it's due. | | Done. |
| 7 | ~~Cast: download status is written to a fixed column.~~ **Fixed: merged in #2087.** Rows update by column id; the Inbox and other all-podcast views use the listener's columns too. | | Done. |
| 8 | ~~QUILL and Lite crash recovery loses drafts.~~ **Fixed: merged in #2088.** Every unsaved document is offered after any unclean exit, named, with how it differs from the saved file. | | Done. Screen-reader check of the window in Part 3. |
| 9 | ~~Damaged files are silently overwritten.~~ **Fixed: merged in #2089** (from `feat/m6-drafts-backups`). Damaged abbreviation and GitHub draft files are copied aside, and a Beacon rollback can be undone. | | Done. |
| 10 | ~~Chapter Workbench Close discards unsaved edits without asking.~~ **Fixed: merged in #2090.** | | Done. |
| 11 | ~~Lite Scribe resume and the Transcribe exit question.~~ **Fixed: merged in #2091** (Lite now uses one Scribe controller). The rest was already on `main` (#2071, #2075). | | Done. |
| 12 | *Optional one-liner:* `quill/ui/dictation_transcription.py:55` calls `frame._speech_provider(registry=registry)`, but `MainFrame._speech_provider` takes no arguments. It raises TypeError only when the provider ladder returns an id that isn't registered. | A latent crash. | Fix the call, or the signature. |

### 1.2 Release engineering (the Beta path)

**Step 0: publish Dev builds inside the monorepo (in progress, 2026-11-26).** Every Dev build currently stops at its first step, because `DEV_BUILDS_TOKEN`, a personal token for the separate `quillville-dev-builds` repository, is gone. The owner decided not to restore it; Dev builds move into `Community-Access/quill` instead.

- **Requirement:** anyone can download Beta and Dev builds without signing in, from a release page and through the in-app update channel.
- **Constraint:** installed Radio 3.0.4 and Lite 1.1.2 read only the first 30 releases, and `publish_release.py` refuses once a Stable release would be more than 20 places down (`PAGE_BUDGET`). One release per Dev build would break their updates within two days.
- **Design:** **one permanent "Dev builds" prerelease** in `Community-Access/quill`, whose files are replaced on each build. It takes a single page slot whose position never rises. File names carry the version, so the newest few builds per app stay downloadable, and Beta promotion still copies the exact bytes. The workflow writes with its own `GITHUB_TOKEN` (`contents: write` on the publish job only), so no personal token is needed.
- **Code to change:** `dev-builds.yml`, `scripts/dev_build_plan.py`, `scripts/promote_release_batch.py`, `scripts/publish_release.py`, `quill/tools/release_feed.py`, their tests (`test_release_workflows.py`, `test_promote_release_batch.py`, `test_release_page_budget.py`, `test_release_publish_promote.py`), and `docs/release/RELEASE.md`.
- **Secrets to document in `RELEASE.md`:** `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET` (set 2026-11-26; Cast's Podcast Index search in Dev and Beta builds), `QUILL_FEED_SIGNING_KEY` (protected `release-feed-signing` environment), and the retirement of `DEV_BUILDS_TOKEN`.
- **After one full Dev → Beta cycle works this way,** the owner can archive or delete `quillville-dev-builds`.


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

### 1.3 Documentation gate: all apps, after the last code change

Run this **once**, after the code work for Beta is finished. The goal is that every reader-facing document, for every app, matches every change merged to `main`.

**Releases go out one app at a time (owner decision, 2026-11-26).** Each app's release is its own story, so its documents must read as one coherent, professional account of that release, not a diary of commits.

- **Changelogs are reorganized, not just appended to.** Each app's `## Unreleased` section (and its root `CHANGELOG.md` share) is regrouped to cover **everything since that app's last public release**, by feature rather than by date:
  - `###` headings name the feature area as a user knows it (for example "Listening and playback", "Your library", "Recovery and safety", "Accessibility", "Getting started"). `####` subheadings name individual features.
  - Each feature is described once, in its final form. Entries that changed the same feature over several days are merged, and intermediate states that never shipped are dropped.
  - Fixes are grouped under a closing "Fixes" heading by area, each saying what the user experienced and what happens now.
  - Dates move out of headings. The release's own version and date head the section when it ships.
  - The engineering detail a maintainer needs stays, but under the user-facing heading, not instead of it.
- **Every release's documents tell the same story at their own depth:** the announcement (why it matters), the release notes and What's New (what's new and how to try it), the changelog (the complete organized record), the user guide and help (how to use it), and the PRD and technical guides (how it works and why). Each names the same features with the same words.
- **Order:** one app at a time, in the release order the owner sets. Finish an app's full document set, run the docs gates, release it, then start the next.
- **Mechanics:** use the single-app path, the protected `promote-release.yml` workflow (or `promote_release_batch.py --apps <app>` once the monorepo change adds that option), so one app can be listed and promoted without the other ten.

**Scope, for each of the 11 apps (QUILL, Lite, Radio, Cast, Transcribe, Converter, Studio, Inkwell, Weather, Beacon, Social) plus the family docs:**

- user guides and their chapters, tutorials, and keyboard references
- F1 and context help (`docs/f1-help-reference.md` is generated from the help catalogues)
- release notes, What's New and each app's `CHANGELOG.md`, plus the root `CHANGELOG.md`
- PRDs and design docs that describe shipped behaviour
- `docs/release/RELEASE.md`, including the secrets section (see 1.2, step 0)
- the generated HTML, EPUB and DOCX copies, and the GitHub Pages copies under `docs/site/docs`

**How:**

1. List every PR merged since the last documentation pass, and check each one's user-visible change against its app's guide, help, What's New and changelog.
2. Regenerate generated references with their tools: `python -m quill.tools.build_help_reference --write`, `python -m quill.tools.build_github_guide_book --write`, and the keyboard reference and settings inventory gates.
3. Render every app's docs with its own `standalone/<app>/scripts/render_docs.ps1`, and render root docs the same way, with the accessible template. Never use plain Pandoc.
4. Run `scripts/sync_site_docs.py` and commit the site copies.
5. Run the docs gates until green: docs HTML/EPUB parity, help reference, keyboard reference, settings documentation, `test_no_tick_wording`, and the docs-contract shard.

**Known problems going in (found 2026-11-26):**

- **Eight site pages are already stale on `main`:** `converter-prd`, `converter-userguide`, `player-prd`, `quilllite-changelog`, three Lite guide chapters and the Lite GitHub guide chapter 12 under `docs/site/docs`.
- **Use the repository's renderer.** The app `render_docs.ps1` scripts (and `scripts/DocRender.ps1`) apply the accessible template (`docs/pandoc/quill-accessible.html5`: page language, skip link, `<main>` landmark), the first-heading page title, `gfm+smart`, and stable EPUB identifiers. Plain `pandoc` drops all of these.
- **Pandoc version:** this PC has Pandoc 3.12.1; the committed outputs were made with the pinned 3.10. Restore any output whose Markdown didn't change.
- **Wording gate:** say "update" or "check", never "tick" (screen-reader users hear check boxes).

**Done when:** every docs gate passes on `main`, each app's What's New names its Beta changes, and no guide documents a menu or feature that a new install doesn't have. The `View > Load More` mismatch in PR #2003 is the known example.

### 1.4 After Beta

| Work | Notes |
|---|---|
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
| `ext\swl-server`, `ext\swl-dash`, `ext\swl-ci` | Three clean clones of the external SwiftLetter repository (`payown/SwiftLetter`), last updated 21–22 November. They are the reference copies for QUILL's SwiftLetter client work (PR #2003) while its contract fixtures are pending. | **Keep** until SwiftLetter Phase 1 merges. Nothing in them is unique (all clean and on GitHub), so they can be re-cloned at any time. |
| `ext\StreamSift`, `ext\StreamSift-build` | A clean clone of `OnjLouis/StreamSift` (another developer's project, studied for Radio and Cast), plus its local build output. | **Low value.** Delete both whenever you like; the clone can be re-made from GitHub. |
| `swl-client` | Empty folder. | **Delete.** |
| `voice-prototype` | Two files from 8 November: `output\liquid-e2e-tts.md` and `liquid-e2e.log`, notes and a log from an end-to-end text-to-speech prototype run. | **Delete**, after copying the two files to the backup folder if the notes are still wanted. |
| About 80 loose files | Old helper scripts, transcripts, PR conflict notes, gateway compose files, `jev_*` evaluation data, plans | Keep anything not already in a repository by moving it to the backup folder; delete the rest. |

### Branch queue

**89 branches → 11 (2026-11-26).** Every deletion was verified by content, not ancestry, because `main` squash-merges: every file the branch added had to exist on `main`, its commit subjects had to appear in a merged PR, or its work had just landed in one of today's PRs. Every tip is logged in the backup folder's `deleted-branches.txt`; to restore one, run `git branch <name> <hash>`.

Deleted, by family:

- **GitHub (18):** all `gh/*`, `feat/github-*`, `docs/github-*` and `deferred/github-*` branches, and `claude/command-key-phase3-jev`. Superseded by #1991, #1809, #1830, #1833, #1835 and #1801.
- **WordPress (14):** `wp/*`, `wp-finish/*`, `feat/wordpress-*`, `deferred/wordpress-workbench-15-12`, `docs/wp-live-run`, and `worktree-agent-a3cb…` with its `rescue/` copy. Section 15.12 is on `main`, and the newer live run (173 passed, 0 failed) supersedes the 20 November one.
- **Family UX (38):** all of M1, M2, M4, M7 to M12, M14 and M15; `train/family-m1-m2-m7`; and, once their fixes landed today, `feat/m6-quill-lite`, `feat/m6-drafts-backups`, `feat/m13-*`, `feat/m2-workbench`, `train/editor-recovery`, `train/handoff-cast` and `claude/festive-meitner-3e3470`.
- **Other (13):** `feat/scribe-live-regression`, `feat/mobi-reading`, `codex/coverage-stage1-2026-11-11`, `wip/auphonic-backlog`, `wip/dictation-benchmarks`, `fix/ai-and-settings-legible`, `fix/settings-apps` (its leftover test was already on `main`), `train/batch-release-feed`, `fix/lite-listening-mutagen`, `fix/lite-ffmpeg`, `feat/radio-add-folder-path`, and the stale `pr/1999` and `pr/2000` refs.
- **Today's merged PR branches,** each deleted after merging.

**The 11 that remain, and why:**

| Branch | What it is | Plan |
|---|---|---|
| `main` | The single build source. | |
| `feat/swiftletter`, `feat/swiftletter-client-followups` (PR #2003), `fix/swl-browse-review` | SwiftLetter Phase 1. | **Keep**, deferred until SwiftLetter PR #11 publishes its contract fixtures. Then collapse into one stack and finish (1.4). |
| `train/media-recovery` | Preserved, unfinished work: FUX-13 availability and freshness wording (Cast, Radio, Player, Workbench, Weather, Beacon); M5 "Where Is the Sound?"; M6 Radio resume and Studio unfinished-recording wording; plus 7 stray `.audit-*.patch` files. | **Keep until after Beta. Never merge it as is:** it predates #2083, and its `main_frame_radio.py` would undo Radio's startup deferral. Rebuild on current `main` as 3 small PRs (FUX-13 wording, M5, M6 wording), drop the patch files, then delete it. |
| `feat/m5-radio-studio` | FUX-03 "Where Is the Sound?" (Alt+Shift+A) in Radio and Studio; 834 new lines. | **Keep**, after Beta: a new feature with a new key. Land it with the M5 part of `train/media-recovery`, then delete both copies. |
| `feat/m6-radio-studio` | The rest of FUX-05 for Radio and Studio (resume-offer wording, no duplicate " (2)" recording). The Close prompt landed in #2090. | **Keep**, after Beta, with the M6 part of `train/media-recovery`. |
| `feat/m6-transcribe-converter` | Converter's close question with counts, and dictation-history wording. Its Transcribe exit question is obsolete (#2075 keeps the queue). | **Keep**, after Beta: port the Converter and dictation wording only. |
| `feat/m16-editors` | FUX-16 plain-language failure boxes in QUILL Lite and the assistant (Save As default, Copy Details). | **Keep**, after Beta: wording and buttons, no data handling. |
| `feat/scribe-sets` | Named Scribe document sets and the Set Details dialog. | **Keep**, after Beta. Rebase onto the durable queue (#2075) and ETA contract (#2078); conflict risk is high. |
| `train/workbench-sets` | `a37fd7c76`: the Workbench keeps list place and selection on refresh (FUX-06, 4 files). `62a01151c`: core of Scribe document sets. | Land `a37fd7c76` as a small PR when convenient (it helps screen-reader users, no conflicts). The sets commit goes with `feat/scribe-sets`. |

### Old Git stashes (found 2026-11-26)

`git stash list` in `D:\QUILL` holds five stashes from 5–6 November. A stash is work set aside without a commit or a branch; it isn't on GitHub, so it's the last place unsaved work can hide.

| Stash | Made on | Size | Next step |
|---|---|---|---|
| `stash@{0}` "Preserve primary Studio work before payment merge 2026-11-06" | `feature/report-findings-family-completion` | 30 files, +947 / −107 | Compare with `main`'s Studio code; push as a `rescue/` branch if anything is unique, then drop. |
| `stash@{1}` "paused-for-main-consolidation-payments-2026-11-05" | `payments-stripe-paypal` | 2 files, +20 | Same check; very likely superseded by the WordPress payment work on `main`. |
| `stash@{2}` "paused-for-main-consolidation-github-2026-11-05" | `agents/use-s-code-ghmanage-if-it-helps-you` | 4 files, +55 / −4 | Same check; GitHub Workbench is complete on `main`. |
| `stash@{3}` "paused-for-main-consolidation-main-2026-11-05" | `main` | no tracked changes | Drop after a quick look at its untracked part. |
| `stash@{4}` "docs-before-main-merge" | `docs/rich-documentation` | 64 files, +7,412 / −116,835 | Mostly a generated-docs snapshot; check the Markdown files only, then drop. |

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
