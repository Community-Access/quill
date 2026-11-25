# QUILL remaining work and overnight status

Updated: 2026-11-25

This is the implementation record. Completed work is removed from the open
lists. Human acceptance, live tests, credentials, and external permissions are
listed separately and are never counted as code-complete.

## Current release result

- Merged PR #2072 in squash commit
  `3f3e5465bb2a79260c4c3f8dea188ea5b97a955b`.
- The monorepo release catalogue owns 12 Windows products.
- Weather is in Wave 1. Media Player remains held.
- All 11 buildable products have release-channel profiles, menus, snapshots,
  data-format ownership, and data-root routing.
- Dev and promotion workflows are catalogue-driven.
- `release-feed-signing` exists with the owner as required reviewer and main
  plus trusted `v*` deployment refs.
- Local scorecard: 61 of 61 gates passing.
- PR #2072: 23 of 23 GitHub checks passed before merge.
- Protected feed workflow run 45558506768 completed successfully.
- PR #2073 merged all 11 signed per-app feeds and the signed index to `main`.
- PR #2074 made this file authoritative, retired `complete.md`, and pinned
  signed feed files to LF checkout bytes on Windows.

## Merge rule

Completed implementation is merged to `main` as it becomes green. The primary
`D:\quill` worktree is behind and contains user-owned local files, so code work
uses clean worktrees and merges through reviewed PRs rather than rebasing that
dirty tree.

## Open implementation work

### 1. Release rollout, first

- [x] Approve/complete the all-app feed workflow.
- [x] Verify and merge the generated 11-feed plus signed-index PR.
- [ ] Restore `DEV_BUILDS_TOKEN`.
- [ ] Add `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET` for Cast
      Dev search, or explicitly keep that capability absent in the Dev build.
- [ ] Run the first catalogue-driven Dev build and inspect every artifact.
- [ ] Build and inventory the shared Windows runtime, then run the skipped
      runtime-inventory gate.

### 2. Durable Converter queue

- [ ] Reuse the queue/set primitives in Converter.

### 3. Merge-ready implementation trains

- [ ] Audit every remaining `D:\wt` worktree and open PR for:
      already merged/patch-equivalent code, actual unique fixes, conflicts,
      missing tests, and generated-doc drift.
- [ ] Merge the larger coherent trains first:
      the remaining Converter queue, GitHub/WordPress parity, then startup.
- [ ] Remove worktrees and branches only after their green commits are on main.

### 4. GitHub and WordPress implementation parity

- [ ] Finish the remaining GitHub implementation rows for both editors,
      including workspace/service handoffs and grounded assistance.
- [ ] Reconcile the GitHub requirement audit with the shipped command table.
- [ ] Finish any remaining WordPress implementation gaps for both editors.
- [ ] Keep QAF, forms, payments, and external-site behavior behind the tested
      capability and consent contracts.
- [ ] Regenerate both PRDs, status pages, guides, HTML, and EPUB artifacts when
      implementation lands.

### 5. Practice Site and runtime packaging

- [ ] Bundle the missing `tools\wp-playground-cli` payload and make the
      runtime-inventory gate pass on a real staged runtime.
- [ ] Add asynchronous stop behavior and lifecycle-safe callbacks.
- [ ] Prove lesson markers reflect actual PHP seeding.
- [ ] Complete reset/history/late-completion behavior tests.

### 6. Diagnostics, AI clarity, and broad review

- [ ] Complete diagnostics follow-ups for regex timeout, reader bounds, fault
      ownership, relocation/shutdown queues, and modal cue callbacks.
- [ ] Ensure every AI entry point says provider/model, local/cloud, data sent,
      limits, consent, and fallback before use.
- [ ] Make important settings show effective value, source, and reset route.
- [ ] Continue the confirmed code-review defects; do not widen scope to
      speculative refactors.

### 7. Startup speed, last

- [ ] Add a profile read before optional modules import.
- [ ] In Notepad/minimal mode defer Rich Edit/TOM, AI, LSP, Scribe, dictation,
      extensions, printing, and optional menu implementations.
- [ ] Keep crash capture, recovery, atomic save, keymap, focus, announcements,
      TLS and essential editor behavior in the mandatory core.
- [ ] Preserve the open document/session when moving between light and heavy
      profiles; use an explicit restart when an in-process switch cannot be
      safe.
- [ ] Measure installed-build ready-editor and cold-import startup for QUILL,
      Lite, Radio, Cast, Transcribe, Converter, Studio, Inkwell, Weather,
      Beacon, and Social.
- [ ] Target at least the already achieved 25.5 percent Lite gain as a floor,
      then optimize the minimal profiles separately without weakening
      accessibility or persistence.

## Human-only validation

These remain open and are not implementation-complete claims:

- [ ] Required NVDA/JAWS/Narrator checks for shipped dialogs and family journeys.
- [ ] Clean installed and portable machine updates.
- [ ] Stable/Beta/Dev coexistence on real Windows installs.
- [ ] Real Scribe, Moonshine, OCR, clipboard, display, and Windows integration.
- [ ] GitHub live-role, protected-branch, organization, secret, and Copilot-plan
      scenarios.
- [ ] WordPress live-site, payment, OAuth, and packaged Practice Site scenarios.
- [ ] Screen-reader verification of Cast list stability and Lite handoffs.

## Blocked or operational

- The original Lite `0xc0000374` component remains unidentified; diagnostics
  are improved, but the native root cause is not claimed fixed.
- Pneuma ETA milliseconds contract still needs provider confirmation.
- Dev artifact and Cast index secrets are operational prerequisites.
- `report.md` did not exist before this run and is now the visible status file.
- `status.md` and `report2.md` are not recreated.

