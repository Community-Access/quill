# QUILL update-process rehearsal harness

A simple, repeatable way to verify QUILL's in-app self-update (discover ->
download -> install-over) **without touching production or any real user**.

## How the isolation works

QUILL's updater reads the `QUILL_UPDATE_API_URL` environment variable (added in
`quill/core/updates.py`). Unset, it queries the production endpoint
(`Community-Access/quill`). Set, it queries whatever repo you point it at. These
scripts point it at a throwaway public repo, `Community-Access/quill-update-selftest`,
which holds rehearsal-only prereleases. Production releases and the GitHub Pages
update feed are never involved, so no user ever sees these builds.

The override only redirects update *discovery*. Asset downloads still enforce
HTTPS + the trusted-host allowlist, so this cannot weaken update security. The
override lives only in the environment variable on this machine and in the test
repo -- it is **not** baked into any installer (the same installer ships to
production unchanged).

## The installers

Put the installers you want to test in `installers\` (gitignored). Expected names:

- `installers\Quill-for-All-Setup-0.8.0 Beta 1.exe`
- `installers\Quill-for-All-Setup-0.8.1 Beta 1.exe`

Build them with `scripts/build_windows_distribution.py --bundle-python --compile-installer`
(bump `build/version.toml` `prerelease_number` between the two), then copy from
`windows-distribution\installer\Output\` into `installers\`.

## Simple path

1. `install-beta1.cmd` - silently installs 0.8.0 Beta 1 (per-user, no elevation).
2. `launch-quill.cmd` - launches QUILL with the rehearsal endpoint active for that
   run. In QUILL: **Help > Check for Updates**. Expect 0.8.1 Beta 1 -> **Install now**.
3. After the upgrade, confirm **Help > About** shows 0.8.1 Beta 1 and your
   settings/sessions survived.
4. `reset-to-production.cmd` - removes the override so this machine returns to the
   production update endpoint. Run this when you are done.

## Other scripts

- `set-test-endpoint.cmd` - persist the rehearsal endpoint for your user (survives
  restarts; useful if you want repeated checks). `reset-to-production.cmd` undoes it.
- `install-beta2.cmd` - silently install the new release (0.8.1 Beta 1) directly (to
  reset state or test the installer alone).
- `status.cmd` - show the current/persisted override and whether QUILL is installed.

## What this validates vs. not

Validates the real production path: GitHub Releases discovery, version ordering
(0.8.1 Beta 1 > 0.8.0 Beta 1), platform `.exe` asset selection, download from
`objects.githubusercontent.com`, and the Inno in-place upgrade (data in
`%APPDATA%\Quill` preserved, first-run wizard re-runs). It does **not** exercise
the signed-manifest feed (needs `QUILL_UPDATE_MANIFEST_KEY`) or the app_updater
delta path.
