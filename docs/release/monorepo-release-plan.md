# QuillVille monorepo release plan

**Decision:** `Community-Access/quill` is the one source repository for all
QuillVille Windows products. Unsigned Dev builds are files in one rolling
prerelease of this repository (tag `dev-builds`); there is no second repository
(the separate Dev-builds repository was retired on 2026-11-26).

**Implementation owner:** `quill.core.release_catalog`, checked by
`quill.tools.release_catalog_audit`, and wired into pre-commit and
`quill.tools.platform_report`.

## Goals

- One place decides which products exist, where their versions live, how tags
  and artifacts are named, and which rollout wave owns them.
- A change to shared code selects every affected app instead of relying on a
  person to remember which standalone wrappers ship that code.
- A build is made once. Dev, Beta and Stable listings point at the same release
  bytes when the binary is eligible for promotion.
- Stable never receives a binary that skipped Beta, changed during promotion or
  lacks the required signature and source bundle.
- A held product remains visible in the inventory but cannot silently appear in
  a signed feed or public build.
- QUILL and QUILL Lite receive every shared GitHub and WordPress code path; a
  feature cannot be complete in only one editor.

## Product inventory and waves

The catalogue owns these 12 Windows products:

| Product | Key | Wave | Current release intent |
| --- | --- | --- | --- |
| QUILL | `quill` | Platform | First coordinated official Stable path |
| QUILL Lite | `quilllite` | Platform | 2.0 candidate |
| Quill Radio | `radio` | Platform | 3.2 candidate |
| QUILL Cast | `cast` | Platform | 2.0 first public candidate |
| QUILL Transcribe | `transcribe` | Platform | 1.0 first public candidate |
| Quill Converter | `converter` | Platform | 1.0 candidate |
| Quill Weather | `weather` | Platform | 2.2 first coordinated release |
| QUILL Studio | `studio` | Companion | Build exists; later wave |
| Quill Inkwell | `inkwell` | Companion | Build exists; later wave |
| Quill Media Player | `player` | Held | Catalogue-owned; no release wrapper yet |
| QUILL Social | `social` | Later | Release work waits behind platform/companion waves |
| Quill Beacon | `beacon` | Later | Release work waits behind platform/companion waves |

Radio-on-macOS and Weather-on-iOS are explicit platform variants, not duplicate
Windows products. They cannot enter the Windows sibling/version feed by
accident.

## One-repository boundaries

Everything below stays in `Community-Access/quill`:

- shared product code under `quill/`;
- thin wrappers and installers under `standalone/<app>/`;
- version and build constants;
- GitHub tags and production release objects;
- signed v2 feed files under `docs/site/updates/v2/`;
- installer and portable build scripts;
- update, rollback, revocation and promotion code;
- release notes, website links and source archives;
- release audit history, sign-off references and catalogue waves.

The rolling `dev-builds` release contains only:

- unsigned Windows Dev artifacts;
- SHA-256 files;
- a body naming the exact source commit;
- short-lived prerelease tags.

No app source code, packaging logic or release truth moves to a separate app
repository.

## Catalogue contract

`quill.core.release_catalog.PRODUCTS` is the authoritative list. Each row owns:

- app key and display name;
- tag prefix and release-asset prefix;
- version source file and constant;
- build source file and build constant;
- changelog;
- build entry, when the product is buildable;
- standalone wrapper, when it is a companion app;
- rollout wave;
- shared-runtime status.
- updater profile and channel enrollment;
- the exact settings files a channel snapshot owns;
- which data directory holds each app's persistent state.

These consumers must derive from the catalogue:

- `scripts/release_build_number.py`;
- `scripts/check_sibling_versions.py`;
- `quill/tools/release_feed.py`;
- `build-quill-apps.ps1`, checked by the catalogue audit;
- updater profiles, rollback snapshots and app update menus;
- the Dev and promotion workflow product sets;
- the initial signed-feed bootstrap and signed-index inventory;
- website update rows and release dashboard generation.

The audit fails when:

- a catalogue path or constant is missing;
- a tag or asset prefix is duplicated;
- a new Windows standalone wrapper is not catalogued;
- a held product appears in the signed-feed/publish registry;
- a release wave has no build entry;
- sibling-version, build-number, feed or PowerShell tables drift;
- a product marked for the shared runtime is actually QUILL, or the reverse.
- updater profiles, snapshots, menus or workflow inputs omit a channel-enabled
  product.

## Build identity

Every source build is identified by:

- base version from the catalogue's version constant;
- build number from the catalogue's build constant;
- a canonical file version for Windows;
- a release tag `quill-<app>-v<version>-build.<n>` (or QUILL's existing `v`
  prefix);
- the exact source commit and dependency/third-party source snapshot.

A Dev build uses a dated prerelease version and has no normal build promotion
path. A signed Beta candidate uses the final product version plus its build
number. Stable is a promotion of those exact candidate bytes.

## Cadence

### Dev

- At most once per day from `main`.
- Runs only when `main` changed, unless an owner forces a run.
- Unsigned and plainly labelled Dev.
- Published only as files in the one rolling `dev-builds` release, so Dev builds
  take a single place on the page of releases that installed Quill Radio 3.0.4
  and QUILL Lite 1.1.2 read.
- Contains a SHA-256 list and exact source commit.
- Never enters a signed v2 feed automatically.

### Beta

- A release train decides the changed products and all products affected by a
  shared-runtime or data-format change.
- Each candidate is built once, code-signed when final-numbered, uploaded once
  and listed in its signed per-app v2 feed.
- The same installer/portable files move forward after verification.
- A minimum seven-day soak applies unless an owner records a reason in the
  promotion history.

### Stable

- Runs every promotion check: feed signature, hashes, fresh downloads,
  final-numbered version, Beta age, data-format compatibility, source archive,
  notices, rollback target and build signature.
- No rebuild, re-pack, re-sign-only payload or unrecorded substitution.
- The GitHub prerelease flag is removed; the signed feed moves the exact entry
  from Beta to Stable.
- The release is expired/revoked through the signed list, never by erasing
  evidence from history.

## Release waves

### Wave 1: platform and editor outcome

QUILL, QUILL Lite, Radio, Cast, Transcribe, Converter and Weather.

This wave proves:

- shared runtime installation and channel slots;
- editor and companion startup;
- Scribe and transcription queues;
- signed feeds and exact-byte promotion;
- rollback and installer/portable replacement;
- the common GitHub and WordPress surfaces in QUILL and QUILL Lite;
- Weather as a first-class platform app from the first release train, not as a
  deferred companion.

### Wave 2: companion apps

Studio and Inkwell. Add Media Player only after it gains a real build wrapper,
notices, source archive and sign-off path.

### Wave 3: later products

Social and Beacon. Shared code and security improvements flow to them
immediately, but their first public promotion waits until the first two waves
are stable.

## One-command release train

The family build command remains:

```powershell
.\build-quill-apps.ps1 <app-list> -Release -Sign -DryRun
.\build-quill-apps.ps1 <app-list> -Release -Sign
```

The dry run prints selected products, shared-runtime impact, expected assets,
signing decision and every gate. The real run refuses if:

- a selected app is `held`;
- a changed shared/runtime area selected no dependent app;
- a version/build constant disagrees with the catalogue;
- the catalog or feed gate is red;
- an installer, portable artifact, licence file or source archive is absent;
- a final-numbered candidate is unsigned;
- Sibling-version checks disagree.

Normal publishing is one of two equivalent paths. A protected GitHub Actions
environment reads `QUILL_FEED_SIGNING_KEY` in process memory; the owner's local
file remains the recovery and manual path:

```powershell
python scripts\publish_release.py --app <key> --version <version> `
  --channel beta --dist <dist> --notes-file <notes.md> --dry-run

python scripts\promote_release.py --app <key> --version <version+build> `
  --to stable --dry-run
```

The `release-feeds.yml` workflow creates every catalogue feed and the signed
index. `promote-release.yml` signs a Beta or Stable promotion after its
required environment review. Both verify every signature against
`quill/core/feed-pub.key` before opening the feed pull request. Neither writes
the seed to disk, places it in a command argument, nor exposes it to pull
request or ordinary build jobs.

## Secrets and owner-only actions

Protected release environments may use:

- the workflow's own token, with `contents: write` only in the jobs that publish
  Dev builds (no personal token);
- source-only build secrets needed by a Dev matrix, such as Podcast Index
  credentials;
- `QUILL_FEED_SIGNING_KEY`, a repository secret available only to feed-signing
  jobs after `release-feed-signing` or `stable-promotion` approval.

CI may not receive:

- release-account recovery secrets;
- a payment provider key.

The GitHub copy is the durable operational signing copy. The owner should
still keep the encrypted and physical backups described in `docs/signing.md`;
GitHub never reveals an existing secret value, so backup copies are what
provide offline recovery. Local signing can use `QUILL_FEED_KEY_FILE` or
`~/.config/quill/quill-feed-priv.key`, but ordinary code, tests and pull
request workflows never receive the seed. Authenticode uses the owner's
ambient Azure identity and never a PFX in the repository.

## Required gates

For every release candidate:

- ruff format, ruff check and strict typing for `quill/core`/`quill/io`;
- unit, stability, accessibility and source-contract tests;
- module-size, banned-pattern, dialog, announcement, braille and access-key
  gates;
- release catalogue, sibling versions, app versions, feed and data-format
  gates;
- network egress and persistence audits;
- shared-runtime inventory against a real staged build;
- exact notices, licences and copyleft source manifests;
- Authenticode on every Stable installer and every executable in its portable
  copy;
- exact SHA-256 hashes in the feed;
- signed v2 feed and non-expiring evidence in repository history.

Human acceptance is intentionally separate from the automation record. The
manual checklist records real-device, screen-reader and clean-machine results;
passing source-contract tests never substitutes for those observations.

## First execution plan

1. Finish the startup and Scribe fixes already on their release train.
2. Make the queue/conversion work durable and pass the editor behavior gates.
3. Approve the protected `release-feed-signing` environment, verify that the
   existing GitHub feed secret matches `quill/core/feed-pub.key`, and run the
   all-app feed bootstrap.
4. Run the catalogue audit and a full release dry-run for Wave 1.
5. Build and publish Lite/Radio/Cast/Transcribe/Converter/Weather candidates to Beta.
6. Add QUILL's own signed candidate and publish the same wave.
7. Run the separately maintained clean-machine and screen-reader acceptance pass.
8. Promote the exact bytes after the seven-day soak.
9. Generate the release dashboard from the catalogue and update the website.
10. Reuse the same process for Wave 2, then Wave 3.

## Anti-patterns this plan rejects

- one source repository per app;
- a second hand-maintained list in every workflow;
- different update/feed code in each standalone app;
- publishing a final-numbered Stable candidate directly;
- rebuilding or re-signing only the outer installer after Beta;
- treating a `held` app as released because source code exists;
- counting source tests as a manual screen-reader run;
- deleting old releases or source archives to simplify the site;
- bypassing a runtime, signature or format gate just to meet a date.
