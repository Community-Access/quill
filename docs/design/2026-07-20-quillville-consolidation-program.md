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

## Recommendation
Phase 1 is safe and finishes the easy consolidation — do it next (strip
quill-radio to a release-host README; recreate the AS shell). Treat Phase 2
(Beacon, Social) as separate, verified migrations on their own branches, and
Phase 3 (QRM/macOS) after. Resist doing all reverse-vendors at once — one
GATE-green app at a time keeps `main` shippable throughout.
