# QUILL remaining work

Updated: 2026-11-25

This file lists only open implementation and release-engineering work.
Completed rows are removed after they land on `main`. Human acceptance, live
tests, credentials, external permissions, and provider confirmations are
tracked in [report2.md](report2.md) and are not counted as code-complete.
Delete this file when its implementation and release-engineering list reaches
zero; [report2.md](report2.md) remains the human and operational record.

## Current implementation summary

- Eleven implementation and release-engineering items remain: two release
  operations, six startup-speed items, one branch/worktree cleanup item, and
  two SwiftLetter items.
- GitHub Workbench implementation is complete on `main`.
- The existing WordPress Workbench and Practice Site implementation is complete
  on `main`; SwiftLetter Phase 1 remains open separately in PR #2003.
- Scribe implementation is complete, including durable conversion and
  transcription queues. Pneuma confirmed the ETA contract, and QUILL now
  follows it. No Scribe code or provider-contract blocker remains.
- Converter queue persistence is complete in PR #2077 and merged to `main`.
- All human, credential, live-service, and external work is kept in
  [report2.md](report2.md) and is not part of the code-work count.

## Release and packaging

- [ ] Run the first catalogue-driven Dev build and inspect every artifact.
- [ ] Build and inventory a real staged shared Windows runtime, then run the
      skipped runtime-inventory gate.

## Startup speed

- [ ] Add a profile read before optional modules import.
- [ ] In Notepad/minimal mode defer Rich Edit/TOM, AI, LSP, Scribe, dictation,
      extensions, printing, and optional menu implementations.
- [ ] Keep crash capture, recovery, atomic save, keymap, focus, announcements,
      TLS, and essential editor behavior in the mandatory core.
- [ ] Preserve the open document/session when moving between light and heavy
      profiles; use an explicit restart when an in-process switch cannot be
      safe.
- [ ] Measure installed-build ready-editor and cold-import startup for QUILL,
      Lite, Radio, Cast, Transcribe, Converter, Studio, Inkwell, Weather,
      Beacon, and Social.
- [ ] Target at least the already achieved 25.5 percent Lite gain as a floor,
      then optimize the minimal profiles separately without weakening
      accessibility or persistence.

## Repository consolidation

- [ ] Audit every remaining worktree and branch, merge unique behavior in small
      green PRs, and remove patch-equivalent, merged, or abandoned worktrees and
      branches. Keep only `main` plus an explicitly recorded SwiftLetter or
      user-owned blocker.

## SwiftLetter integration, last

- [ ] Resolve PR #2003's review and failing documentation-contract shard, sync
      the shared SwiftLetter fixtures, and merge the approved stack to `main`.
- [ ] Complete SwiftLetter Phase 1 editor wiring: open an article, Save to
      SwiftLetter, Compare/Retry, and lossless Markdown/HTML round trips.

## Fast beta-release plan after the startup fixes

This plan covers the nine tasks that lead to an 11-product beta set. It
deliberately excludes SwiftLetter and the future Whisper plan.

### 1. Finish startup once, then freeze `main`

- Complete the live profile-switch and feature-toggle correction in the
  startup branch, including idempotent Radio and Podcasts initialization.
- Push one PR, run its full CI, repeat the all-app real-wx timing probe, and
  merge it to `main`.
- Remove the six startup rows from this file only after the tests, measurements,
  and merged commit agree.
- Do not begin release builds from a feature branch. The beta source is the
  exact merged `main` commit.

### 2. Retire stale branches and worktrees in parallel with review

- Snapshot `git worktree list --porcelain` and every local/remote branch.
- Classify each branch as merged, patch-equivalent, unique, dirty/locked,
  or intentionally deferred.
- Delete merged and patch-equivalent branches after checking both patch
  equivalence and behavioral test evidence; keep no branch merely because its
  commit count is nonzero.
- Turn unique behavior into the smallest coherent PRs, merge them to `main`,
  then delete the source branch and worktree.
- Never force-delete dirty or locked user work. Record the owner and blocker,
  and revisit it in the same cleanup pass.
- After the pass, `main` is the sole build source. The one allowed deferred
  exception is the SwiftLetter stack while its external fixture dependency is
  unresolved.

### 3. Clear the two operational inputs

- Restore `DEV_BUILDS_TOKEN`.
- Supply the Podcast Index key and secret, or make the explicit decision to
  ship the first beta without Podcast Index search. Do not spend build time on
  this question.
- These are release operations in [report2.md](report2.md), not code tasks.

### 4. Run the parallel 11-app compilation matrix

- Dispatch `dev-builds.yml` with `force=true`. The catalogue now supplies the
  11 channel-enabled apps to both build and publish jobs.
- Run it once from the repository root:

  ```powershell
  gh workflow run dev-builds.yml -f force=true
  ```

- Treat one matrix run as the quickest package smoke: every product must emit
  its installer, portable zip, checksums, notes, and expected version.
- Inspect all 11 results before rerunning anything. Fix shared packaging
  defects once, then rerun only failed jobs or the affected products.
- The Dev versions are unsigned by policy.

At the same time, build one fresh shared runtime on the local Windows machine:

```powershell
.\build.ps1 runtime
python scripts\check_runtime_inventory.py standalone\runtime\dist\QuillVilleRuntime
python -m quill.tools.platform_report
```

If the Dev workflow is unavailable, the fallback is:

```powershell
.\build-quill-apps.ps1 all -KeepGoing
```

The fallback rebuilds the shared runtime once, builds all 11 apps in family
order, and writes one upload folder with logs, licences, copyleft manifests,
and SHA-256 sums. Fix common failures before repeating the whole matrix;
afterwards, rerun only failed apps with `-SkipRuntime`.

### 5. Smoke the exact artifacts that will become Beta

- Test the installer and portable copy for every product on clean data.
- For each app, verify first launch, one useful action, persistence after
  restart, clean exit, and update-check behavior.
- Verify data roots and shared-runtime slots do not let Stable, Beta, and Dev
  overwrite one another.
- Compare each app's build version, marker, release tag, executable metadata,
  and feed entry.
- Put NVDA/JAWS/Narrator and external-service acceptance in
  [report2.md](report2.md). Do not mislabel them as missing implementation.

The build is a beta candidate only when all 11 products pass the same smoke
sheet. One failing shared-runtime condition blocks every product; one failing
app blocks only that app.

### 6. List and promote the same binaries

For each catalogue app, use the version from the successful Dev release:

```powershell
python scripts\publish_release.py --app <app> --version <dev-version> --channel dev --existing --dry-run
python scripts\promote_release.py --app <app> --version <dev-version> --to beta --dry-run
```

When both dry runs pass:

1. List each Dev build on the Dev channel.
2. Promote the exact same files to Beta.
3. Use `--skip-soak` only with a written, specific reason; otherwise keep the
   normal one-day Dev-to-Beta check.
4. Open and merge the signed feed PRs.
5. Verify all 11 feeds and the signed index before announcing anything.

Use the Dev planner's `versions` JSON or the release tags to drive a loop;
do not hand-copy eleven app/version pairs into separate commands. Keep one
audit row per app with the release tag, SHA-256 file, dry-run result, and final
feed sequence.

Do not rebuild between Dev and Beta promotion. The beta tester gets exactly
the hash that passed the smoke run.

### 7. Release, observe, and repair narrowly

- Publish one concise beta announcement naming the 11 products, hashes, known
  rough edges, and the location of each feed.
- Watch launch, update, persistence, and crash reports for the first cohort.
- A release-blocking defect produces a new build for only the affected app;
  reuse the passing runtime unless its contents changed.
- Keep the original beta immutable. Do not overwrite tags or artifacts.
- When the beta list is stable, run the cleanup pass again and delete the
  remaining spent branches and worktrees.

## Future plan after the remaining tasks: reuse system Whisper resources

Run this work only after the release-blocking items above are complete. The goal
is to save model and engine space without making another project a hidden
dependency.

### 1. Preserve the supported baseline

- Keep QUILL's CPU/int8 Faster Whisper path fully supported.
- Keep the existing automatic CUDA/float16 choice when CTranslate2 detects a
  usable GPU.
- Do not require a GPU, CUDA, another Python installation, or another app.
- Do not scan the whole disk or execute a program found unexpectedly on
  `PATH`.

### 2. Add safe model discovery and adoption

- Inspect only documented model-cache locations and user-selected folders.
- Recognize only catalogued Faster Whisper CTranslate2 model layouts, not an
  arbitrary folder that merely contains `model.bin`.
- Verify model family, revision/format, required files, size, and recorded
  SHA-256 before offering adoption.
- Present one explicit choice: reference the existing model, hard-link it when
  the filesystem permits, or copy it into QUILL-managed storage.
- Explain the failure mode beside reference mode: removing or changing the
  other project can make that reference unusable.
- Keep a QUILL-owned metadata record for adopted models and revalidate it
  before transcription.
- If an adopted model disappears or fails validation, disable it for that
  session and offer QUILL's managed download or CPU fallback.

### 3. Add optional external-engine detection

- Detect a known Faster Whisper installation only in a user-approved
  environment or virtual environment.
- Probe a compatible `faster-whisper`/CTranslate2/Python combination in an
  isolated process; never import an external environment into QUILL's main
  interpreter.
- Verify version, ABI, device availability, model compatibility, and exit
  behavior before enabling it.
- Clearly label the engine as external and keep QUILL's on-demand managed
  engine as the repair path.
- Never reuse an arbitrary `whisper` or `whisper.exe` command; whisper.cpp,
  open-source Whisper, and Faster Whisper do not share the same command
  contract.

### 4. Keep updates and consent predictable

- A detected external engine or model remains optional; QUILL never adopts or
  activates it without an explicit user action.
- Revalidate external resources after QUILL, the other app, Python, CUDA, or
  CTranslate2 changes.
- Do not silently network when probing external installations.
- Keep model removal separate from the other project's storage; QUILL may
  remove only its own copies, links, and metadata.

### 5. Verify behavior and space savings

- Add unit tests for model-layout validation, checksums, missing files,
  broken references, hard-link fallback, incompatible versions, CPU fallback,
  and external-process failure.
- Run live Windows tests for installed QUILL, portable QUILL, CUDA, no-CUDA,
  model removal during a session, and use alongside another Whisper project.
- Measure download/engine footprint, model duplication, startup cost, first
  transcription, warm transcription, and uninstall behavior.
- Document the external-resource risk and update the speech privacy/network
  audit before shipping.

