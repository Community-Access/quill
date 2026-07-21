# QuillVille consolidation program — one repo, many products

Date: 2026-07-20. Supersedes the scope of
`2026-07-20-radio-cast-consolidation-plan.md` (still valid for the update-safety
rules) by widening it to the whole family: Radio, Cast, Audio Studio, Beacon,
Social, and the macOS radio port (QRM). Goal: the `quill` repo is the single
source of truth and can build and ship every standalone product, with no code
duplicated across repos and no shipped user's updater ever broken.

## The family, and why the products differ

There are two fundamentally different kinds of product, and they take very
different amounts of work to consolidate:

**A. Thin wrappers — code already in `quill`.** The app *is* a `quill.apps.*`
entry point; the product repo only ever held packaging. Consolidating = move
the packaging into `quill/standalone/<product>/` and reduce the product repo to
a release host. Cheap and low-risk.

| Product | App entry | Repo | Shipped | Status |
| --- | --- | --- | --- | --- |
| Quill Radio | `quill.apps.radio` | quill-radio | 2.0.2–2.1.2 | tooling in `standalone/radio/` ✓; repo → release host (pending strip) |
| QUILL Cast | `quill.apps.podcasts` | quill-cast | 1.0.0 | tooling in `standalone/cast/` ✓; repo **archived** ✓ |
| Audio Studio | `quill.apps.studio` | (never pushed) | no | code folded in ✓; standalone tooling **to recreate** |

**B. Separate apps — code NOT yet in `quill`.** These have their own multi-file
packages and must be **reverse-vendored** into the `quill` package first (the
same effort as the Audio Studio migration: rewrite imports to `quill.*`, pass
the GATE suite — size budgets, persistence/egress audits, banned patterns,
mypy, tests — then add a `standalone/<product>/` shell). Real work per app.

| Product | Package | Repo | ~Py files | Notes |
| --- | --- | --- | --- | --- |
| Beacon | `quill_beacon` (+ `quillsync`, browser `extensions/`) | beacon | ~38 | Ships browser extensions (chromium/firefox) — extra surface beyond a normal app. |
| Social | `quill_social` | quill-social | ~113 | Largest of the three; its own `tests/`. |
| QRM (macOS radio) | `quill_radio_mac` | (qrm) | ~46 | macOS packaging (py2app), not PyInstoaller/Inno. Radio feature code is already in `quill`; this is a Mac *packaging* port. |

## What is done (this pass)
- `standalone/` created in quill; Radio and Cast packaging shells moved in
  (`launcher`, spec, `build_release.ps1`, Inno `.iss`, docs, assets). The quill
  repo can now build those standalone products directly. Ruff excludes
  `standalone/` as distribution tooling; pytest stays scoped to `tests/`.
- Open wrapper-repo issues moved to quill (#1187/#1188/#1189).
- **quill-cast archived** (reversible; keeps its v1.0.0 release + updater API
  alive so the existing Cast user does not 404). Its packaging is preserved in
  `standalone/cast/`. The stale local `S:\quill-cast` clone can be deleted by
  hand (sandbox blocks removing `S:\` roots).

## Sequenced plan (smallest risk first)

### Phase 1 — finish the thin wrappers (low risk)
1. **Strip quill-radio to a release host.** Its packaging now lives in
   `standalone/radio/`. Reduce the quill-radio repo to a README that points to
   quill; keep the repo (it is the live updater target for 2.x users and hosts
   the release downloads). Publish future Radio releases to it from
   `standalone/radio/scripts/build_release.ps1` via
   `gh release create --repo Community-Access/quill-radio`. **Do not delete or
   rename it** (see update-safety rules below).
2. **Recreate Audio Studio standalone tooling** in `standalone/audio-studio/`
   from the radio template (`quill.apps.studio`, its icon + product docs from
   `docs/audio-studio/`). AS never shipped, so there is no repo and no updater
   constraint — it is pure build tooling.

### Phase 2 — reverse-vendor the separate apps (one at a time, verified)
Do these **individually**, each on its own branch, each fully GATE-green with
tests before the next — exactly how Audio Studio was done. Do **not** batch
them; a half-migrated app that fails the persistence/egress audits or mypy
would block the whole repo.
3. **Beacon** first (smallest, ~38 files). Extra step: decide where the browser
   `extensions/` live (they are not Python — likely `quill/data/beacon-ext/` or
   a top-level `extensions/`, force-included like other package data).
4. **Social** (~113 files, its own tests). Largest; expect real GATE work
   (size budgets, new persistence/egress sites).
5. Each gets a `standalone/<product>/` shell after its code is in `quill`.

### Phase 3 — macOS radio port (QRM)
6. Fold `quill_radio_mac` packaging into the repo under a macOS path (e.g.
   `standalone/radio/macos/` using py2app, sibling to the Windows shell). The
   radio *feature* code is already shared via `quill.apps.radio`; QRM is only
   the Mac packaging. Keep it beside the Windows Radio tooling so both ship the
   same app.

## Update-safety rules (unchanged, apply to every shipped repo)
Every shipped product's updater polls its own repo (`quill/apps/<app>.py:
_REPO`). Therefore:
- **Never delete or rename a shipped product's GitHub repo.** Its
  `/releases` API is live infrastructure. To retire one, follow the migration
  in `2026-07-20-radio-cast-consolidation-plan.md` (repoint `_REPO`, ship a
  transitional release from the old repo, wait for adoption) and then
  **archive, not delete**.
- Archiving is the safe "remove": read-only, reversible, releases stay served.
  That is what was done to quill-cast.
- Audio Studio and any never-shipped product are exempt (no users, no updater).

## Status (2026-07-21)

- **Radio, Cast, Beacon, Audio Studio** each have a full `standalone/<product>/`
  build shell (launcher, PyInstaller spec, Inno `.iss` supporting per-user OR
  per-machine, `build_release.ps1` producing an installer `.exe` + a portable
  `.zip`, docs). Beacon is reverse-vendored into `quill/apps/beacon`; Radio /
  Cast / Studio *are* `quill.apps.*` entry points.
- **QUILL Social and the macOS Radio port (QRM)** are captured verbatim into
  `standalone/social/` and `standalone/radio-mac/` with `MIGRATION.md` notes;
  the external `s:\quill-social` and `s:\qrm` repos are removed (content lives in
  quill + git history). Social's build shell and the QRM→shared-Radio merge are
  the remaining follow-ups.
- The shared runtime is **Hugging-Face-free by default**: whisper.cpp, Faster
  Whisper, and all Piper voices are mirrored, SHA-verified, on QUILL's own
  `assets-v1` release; `huggingface_hub` is no longer a base dependency (only the
  gated pyannote diarization extra pulls it).

## Benefits of this approach (distribution and beyond)

Why one repo of shared code with thin per-product shells beats separate
per-product codebases:

**Distribution.**
- One `onedir` build per product feeds *both* deliverables — zip it for the
  portable, point Inno Setup at it for the installer — and each `.iss` carries
  per-user **and** per-machine install in one script (`PrivilegesRequired=lowest`
  + dialog override). One build recipe, two install types, every product.
- Everything is bundled (no install- or first-run downloads); the heavy speech
  engines are fetched on demand through the shared, **SHA-256-verified**
  `assets-v1` component system, so base builds stay small and no product depends
  on a third-party host (Hugging Face) staying up.
- Every product inherits the same verified self-update path (Quill's signed
  release feed + the decompression-safety fix), so "Install and restart" behaves
  identically everywhere.

**Maintenance and correctness.**
- Single source of truth: a fix or feature written once in the `quill` package
  reaches *every* product at once — no vendoring, no re-pinning, no drift. The
  design rule holds: "if it breaks, it breaks everywhere," so a defect surfaces
  once across the whole family instead of hiding in a stale copy.
- One gate suite guards all shared code — ruff, strict mypy on `core`/`io`,
  module-size budgets, the dialog-surface inventory, the accessible-name audit,
  the network-egress audit, and the banned-pattern check — so quality is uniform,
  not per-repo.
- Apps declare `REQUIRED_COMPONENTS` and a refcount registry shares downloaded
  components (ffmpeg, mpv) across co-installed products, so a listener with Radio
  *and* Studio downloads ffmpeg once.

**Accessibility.** One accessibility contract (`dialog_contract`, accessible-name
inference, region-entry/-exit announcements, the transition-cue policy) is
enforced across every surface of every product, so the screen-reader experience
is consistent — a fix to focus or naming lands everywhere.

**Footprint and the user.** A shared `%APPDATA%\Quill` data store means favorites,
settings, voices, and recordings are shared across QUILL, Radio, Cast, and
Studio; the total on-disk footprint is one codebase plus small shells; and users
get every product's fixes automatically.

**Velocity.** Contributors work in one repo with one test suite and one CI; a new
product is a thin `standalone/` shell over the existing package, not a fork to
keep in sync.

## Recommendation
Phase 1 is safe and finishes the easy consolidation — do it next (strip
quill-radio to a release-host README; recreate the AS shell). Treat Phase 2
(Beacon, Social) as separate, verified migrations on their own branches, and
Phase 3 (QRM/macOS) after. Resist doing all reverse-vendors at once — one
GATE-green app at a time keeps `main` shippable throughout.
