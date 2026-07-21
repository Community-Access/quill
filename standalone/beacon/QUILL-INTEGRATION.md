# QuillBeacon — integration status and what this folder preserves

The QuillBeacon **application code** now lives in the quill monorepo at
`quill/apps/beacon/` (vendored and GATE-green, 2026-07-20), sharing the `quill`
package like radio/podcasts/studio. Its tests are at `tests/unit/apps/beacon/`.

This `standalone/beacon/` folder **preserves everything else** from the original
QuillBeacon repo, which was never pushed to GitHub (the local clone had no
remote), so this is now the safe, version-controlled home for it:

- `docs/` — product docs (PRD, QuillSync user guide, surface/integration plans).
- `server/` — the **QuillSync sync backend** (Flask-style app, client, mailer,
  store). This is a *deployable service*, intentionally **not** bundled into the
  desktop app package; kept here for preservation and future deployment.
- `extensions/` — the **browser extensions** (chromium, firefox) for the capture
  bridge. Non-Python; not bundled into the desktop app.
- `launcher.py`, `scripts/`, `run-quill-beacon.bat`, `pyproject.toml`,
  `README.md`, `CHANGELOG.md` — the original build/tooling scaffolding.

## Build shell (done)
`standalone/beacon/` is now a working build shell modeled on `standalone/radio/`:
`launcher.py` + `quill/apps/beacon/__main__.py` (so `python -m quill.apps.beacon`
runs), `quill-beacon.spec`, `scripts/build_release.ps1`, and
`installer/quill-beacon.iss`. Beacon plays through the **shared audio layer**
(`quill.ui.audio.audio_engine`) like Radio/Cast/Studio, so the build stages
libmpv only *optionally* (wx.media/WMP is the default backend). Still needs a
real build+install+launch to validate, and a `quill-beacon.ico` (the spec ships
the default icon until one is added).

## Not yet done (follow-ups)
- **Known defects to fix before shipping** (from the family audit §16.5): the
  sync-merge data loss (locations dropped on merge), plaintext device bearer
  token, capture-bridge origin check, and the scrypt-params forward-compat trap.
- **Data store:** Beacon still uses its own `%APPDATA%\QuillBeacon` silo; the
  runtime plan (`docs/design/2026-07-20-quillville-runtime-and-component-plan.md`)
  calls to migrate it onto the shared `%APPDATA%\Quill` contract.

Beacon has **no in-app updater** and the `beacon` GitHub repo has **no
releases**, so unlike quill-radio / quill-cast there is nothing to keep alive
for "check for updates."
