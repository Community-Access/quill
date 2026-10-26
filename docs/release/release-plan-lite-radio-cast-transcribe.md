# Releasing QUILL Lite 1.2, Quill Radio 3.2, QUILL Cast 2.0 and QUILL Transcribe 1.0

Everything to do, in order, to publish these four apps as general (Stable)
releases. Written 2026-10-24 from `main` at the commit that added this file.
The general process is [QUILL Release Process](RELEASE.md); this page applies
it to these four apps and says which parts are already done.

Steps marked **(you)** need your accounts, your keys or a person at a
screen reader. Everything else is a command you run in PowerShell at
`D:\QUILL`.

## What is shipping

| App | Version | Tag | Update path | First release of this version |
| --- | --- | --- | --- | --- |
| QUILL Lite | 1.2.0 build 5 | `quill-lite-v1.2.0-build.5` | Release channels (Beta, then Stable) | Yes; 1.1.2 is current |
| Quill Radio | 3.2.0 build 4 | `quill-radio-v3.2.0-build.4` | Release channels | Yes; 3.0.4 is current |
| QUILL Cast | 2.0.0 build 5 | `quill-cast-v2.0.0-build.5` | Release channels | Yes; Cast has never been published |
| QUILL Transcribe | 1.0.0 build 2 | `quill-transcribe-v1.0.0-build.2` | Release channels | Yes; its site page promises 1 November 2026 |

The build numbers are the ones each app's source declares; the release
scripts take them from there. All four were checked against the published
releases on 2026-10-24 (`scripts/check_release_builds.py`): none is published
yet.

**QUILL Transcribe joined the release channels on 2026-10-24**, so all four
apps take the same path: Beta, a week's soak, then Stable. It has Help >
Release Channel... (Alt+H, L), and the publish and promote scripts accept
`transcribe`. Its site page promises 1 November 2026, so publish its Beta by
25 October to have the week's soak, or promote with `--skip-soak` and a reason.

## Already done (2026-10-23 and 24)

- Every quality gate passes on `main` (`python -m quill.tools.platform_report`:
  50 of 50), and PR CI, security, accessibility and docs checks are green.
- No open security alerts: Pillow 13.0.0, pypdf 6.21.2, filelock 4.2.4 and
  setuptools 84.2.1 are required and installed.
- The build environment is complete: every Python package group the builds
  install, the pinned binaries (ffmpeg, libmpv, deno, piper), the built-in
  speech models and the updater's bootstrappers, all checksum-verified.
- Versions agree everywhere; the four changelogs have their versions; all four
  have release notes (`standalone/quilllite/docs/release-notes-1.2.md`,
  `standalone/radio/docs/release-notes-3.2.md`,
  `standalone/cast/docs/release-notes-2.0.md`,
  `standalone/transcribe/docs/release-notes-1.0.md`).
- `build-quill-apps.ps1 -Release` checks every build number against the
  published releases before building.

## Step 1: one-time setup (you)

Only what these four releases need. The Dev-build setup in RELEASE.md (the
`DEV_BUILDS_TOKEN` secret, the dev-builds repository) is **not** needed.

1. **Restore the feed-signing key.** Every publish and promotion signs the
   app's update list with it, and it is not on this computer: neither
   `C:\Users\jeffbis\.config\quill\quill-feed-priv.key` nor
   `QUILL_FEED_KEY_FILE` exists. Put the key file back at that path, or set
   `QUILL_FEED_KEY_FILE` to where it is. It is the same key as the v1 feed's
   (`QUILL_FEED_SIGNING_KEY` in CI). Never commit it.
2. **Code signing (done 2026-10-24: `python scripts/code_signing.py doctor`
   says "Ready to sign" and a test signature verified).** Stable is always
   Authenticode-signed, at build time. On another computer, the Azure Artifact
   Signing steps are in `docs/code-signing.md`; in short:
   - install the client tools once (may need an administrator):
     `winget install -e --id Microsoft.Azure.ArtifactSigningClientTools`;
   - confirm the account, identity validation, certificate profile, and that
     your Entra ID user has **Artifact Signing Certificate Profile Signer**;
   - check `metadata.json` at the repository root names your endpoint, account
     and profile (it exists; see `docs/code-signing.md`);
   - in a normal (not elevated) PowerShell: `az login`, then
     `az account set --subscription "<subscription-id>"`.
3. **GitHub.** `gh auth status` shows you signed in with access to
   `Community-Access/quill`.
4. **Only if you will promote from GitHub rather than your computer:** create
   the Environment **stable-promotion** with yourself as reviewer, and allow
   Actions to create and approve pull requests (Settings > Actions > General).

## Step 2: decisions to settle before building (you)

- **Portable copies of QUILL Lite 1.1.2 must update by hand** (decided
  2026-10-17). The notice is drafted in
  `docs/release/portable-update-by-hand-notice.md` and not yet published.
  Publish it on the website with the release.
- **Dependabot's pip updater still fails** (`unexpected_external_code`). The
  fix is one line in `.github/dependabot.yml` under the `pip` entry,
  `insecure-external-code-execution: allow`, which lets Dependabot run the
  project's build backend in its own sandbox. It was not applied because it is
  a security setting for you to approve. It does not affect the release.

## Step 3: build, signed (about an hour)

```powershell
git switch main
git pull
.\build-quill-apps.ps1 lite,radio,cast,transcribe -Release -Sign -DryRun   # read the plan
.\build-quill-apps.ps1 lite,radio,cast,transcribe -Release -Sign
```

The two inventory stops this build used to expect (the runtime's `lxml`, and
QUILL Lite's portable PDF and OCR packages) were cleared on 2026-10-24 from
real unsigned builds, so the build should run straight through. If an
inventory gate stops it anyway, something on this computer has changed: follow
[Building the QUILL Windows family](../building-windows-family.md), and never
rebaseline a package you cannot explain.

Code signing was proved on 2026-10-24: a test program signed through
`scripts/code_signing.py` verified as `Valid`, signed by Jeffrey Bishop
(Microsoft ID Verified CS AOC CA 04), with a Microsoft timestamp.

**Check the signatures** before going further: every installer and every
program in each portable zip must say `Valid`.

```powershell
Get-ChildItem dist\release-builds -Recurse -Include *.exe |
    Get-AuthenticodeSignature | Select-Object Status, Path
```

Everything lands in `dist\release-builds\<date-time>\upload`, with
`SHA256SUMS.txt`.

## Step 4: test, and sign off (you, or your testers)

1. **Two-minute smoke test of each**, on a computer without the apps: install
   or unzip, start it, and:
   - QUILL Lite: open a `.docx`, type, save, reopen; open a text PDF and a
     scanned PDF (answer Yes to OCR).
   - Quill Radio: play a station; start and stop a recording.
   - QUILL Cast: play an episode; search the Podcast Index.
   - QUILL Transcribe: dictate into Notepad; transcribe a short recording.
2. **Screen-reader testing, then a sign-off sheet per app.** Promotion to
   Stable refuses an app without one. A sheet is ready for each, to fill in:
   - `docs/qa/signoffs/quilllite-1.2.0.md`
   - `docs/qa/signoffs/radio-3.2.0.md`
   - `docs/qa/signoffs/cast-2.0.0.md`
   - `docs/qa/signoffs/transcribe-1.0.0.md`

   Set `Result: pass` only when the tester has done the checks it lists; the
   open screen-reader checks are in `docs/qa/screen-reader-checks-2026-10.md`.
   Commit and push the sheets.

## Step 5: publish all four to Beta

Each app's "What's new" is already written, in `docs/release/whats-new/`. It is
what people read in the update window when Check for Updates offers the build,
and the GitHub release's text, so it is short enough to show whole (the window
stops at 60 lines or 4,000 characters, and `tests/unit/docs/test_whats_new_fits.py`
fails a file that would be cut). It puts anything to do before updating first:
portable QUILL Lite 1.1.2 and Quill Radio 3.0.4 must update by hand this once.
Rehearse, then publish:

```powershell
python scripts/publish_release.py --app quilllite --version 1.2.0 --build 5 --channel beta `
    --dist standalone/quilllite/dist --notes-file docs/release/whats-new/whats-new-quilllite-1.2.0.md --dry-run
python scripts/publish_release.py --app quilllite --version 1.2.0 --build 5 --channel beta `
    --dist standalone/quilllite/dist --notes-file docs/release/whats-new/whats-new-quilllite-1.2.0.md

python scripts/publish_release.py --app radio --version 3.2.0 --build 4 --channel beta `
    --dist standalone/radio/dist --notes-file docs/release/whats-new/whats-new-radio-3.2.0.md --dry-run
python scripts/publish_release.py --app radio --version 3.2.0 --build 4 --channel beta `
    --dist standalone/radio/dist --notes-file docs/release/whats-new/whats-new-radio-3.2.0.md

python scripts/publish_release.py --app cast --version 2.0.0 --build 5 --channel beta `
    --dist standalone/cast/dist --notes-file docs/release/whats-new/whats-new-cast-2.0.0.md --dry-run
python scripts/publish_release.py --app cast --version 2.0.0 --build 5 --channel beta `
    --dist standalone/cast/dist --notes-file docs/release/whats-new/whats-new-cast-2.0.0.md

python scripts/publish_release.py --app transcribe --version 1.0.0 --build 2 --channel beta `
    --dist standalone/transcribe/dist --notes-file docs/release/whats-new/whats-new-transcribe-1.0.0.md --dry-run
python scripts/publish_release.py --app transcribe --version 1.0.0 --build 2 --channel beta `
    --dist standalone/transcribe/dist --notes-file docs/release/whats-new/whats-new-transcribe-1.0.0.md
```

Each creates a GitHub prerelease, uploads the files, lists the build on Beta
and signs the list. These are the **first** update lists for all four apps
(`docs/site/updates/v2/` does not exist yet); until they exist the apps keep
using the GitHub path. Commit `docs/site/updates/v2` and push to `main`; the
website republishes within minutes and Beta users are offered the builds.

Then update one portable copy and one installed copy of each by hand, and read
`apply-update.log` in the app's `updates` folder.

## Step 6: soak on Beta (7 days)

Promotion refuses a build that has been on Beta for less than seven days. A
shorter soak needs a reason, recorded in the list:
`--skip-soak "the reason"`.

## Step 7: promote to Stable

```powershell
python scripts/promote_release.py --app quilllite --version 1.2.0+5 --to stable --dry-run `
    --notes-file docs/release/whats-new/whats-new-quilllite-1.2.0.md
python scripts/promote_release.py --app quilllite --version 1.2.0+5 --to stable `
    --notes-file docs/release/whats-new/whats-new-quilllite-1.2.0.md
python scripts/promote_release.py --app radio --version 3.2.0+4 --to stable --dry-run `
    --notes-file docs/release/whats-new/whats-new-radio-3.2.0.md
python scripts/promote_release.py --app radio --version 3.2.0+4 --to stable `
    --notes-file docs/release/whats-new/whats-new-radio-3.2.0.md
python scripts/promote_release.py --app cast --version 2.0.0+5 --to stable --dry-run `
    --notes-file docs/release/whats-new/whats-new-cast-2.0.0.md
python scripts/promote_release.py --app cast --version 2.0.0+5 --to stable `
    --notes-file docs/release/whats-new/whats-new-cast-2.0.0.md
python scripts/promote_release.py --app transcribe --version 1.0.0+2 --to stable --dry-run `
    --notes-file docs/release/whats-new/whats-new-transcribe-1.0.0.md
python scripts/promote_release.py --app transcribe --version 1.0.0+2 --to stable `
    --notes-file docs/release/whats-new/whats-new-transcribe-1.0.0.md
```

Every check prints PASS, WARN or FAIL, and one FAIL stops it: the files
download with the hashes in the list, the list's signature, a signed build that
was on Beta, the changelog, the sign-off sheet, and the documentation gates.
The `--notes-file` keeps Stable's "What's new" the same as Beta's. Without it,
the notes are rolled up from the changelog, which for these first update lists
runs far past what the update window shows (QUILL Lite's would merge every
section back to 1.0.0). Commit `docs/site/updates/v2` and push.

## Step 8: the website and announcements

1. **Download links.** The site links to specific release files, today
   `quill-lite-v1.1.2` and `quill-radio-v3.0.4`, on `index.html`,
   `quilllite.html`, `radio.html`, `compare.html`, `dictation.html` and
   `meet-quillbert-and-quillbee.html`. Point them at the new releases, and add
   Cast's and Transcribe's. `tests/unit/docs/test_site_links.py` must pass.
2. **Transcribe's page** (`docs/site/docs.html`) says "its downloads arrive
   that day": change it to say they are here.
3. **Announcements**: QUILL Lite's (`standalone/quilllite/docs/announcement.md`),
   Radio's (`standalone/radio/docs/announcement-3.0.md`, written for 3.0: update
   it for 3.2 or write a 3.2 one), and new ones for Cast and Transcribe if you
   want them.
4. Publish the portable update-by-hand notice (Step 2).
5. Push to `main`; GitHub Pages republishes the site.

## Step 9: afterwards

- Watch the support inbox (FreeScout) for the first days.
- The update lists expire 90 days after they were last written; any publish
  refreshes them, and `platform_report` warns 14 days before.
- After one full release cycle with every app on channels, remove the old v1
  feed key from CI (RELEASE.md, "The old v1 list and its CI key").

## At a glance

| | QUILL Lite 1.2.0 | Quill Radio 3.2.0 | QUILL Cast 2.0.0 | QUILL Transcribe 1.0.0 |
| --- | --- | --- | --- | --- |
| Feed key restored (you) | needed | needed | needed | needed |
| Code signing set up (you) | done (2026-10-24) | done | done | done |
| Built signed (Step 3) | to do | to do | to do | to do |
| Smoke test (Step 4) | to do | to do | to do | to do |
| Sign-off sheet passed (you) | to do | to do | to do | to do |
| On Beta (Step 5) | to do | to do | to do | to do |
| 7 days on Beta (Step 6) | to do | to do | to do | to do |
| Stable (Step 7) | to do | to do | to do | to do |
| Website and announcement (Step 8) | to do | to do | to do | to do |
