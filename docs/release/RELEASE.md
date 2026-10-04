# QUILL Release Process

This file documents the operational steps for cutting a QUILL release.
It is the canonical checklist referenced from `MAINTAINERS.md` and the
release notes.

## Pre-tag checklist

1. **Wave sign-off.** All issues in the active waves for this release are
   closed, with their PRs merged into the release branch.
2. **Quality gates green.** On the release branch head:
   - `pytest -q`
   - `ruff check .`
   - `ruff format --check .`
   - `mypy quill\core quill\io`
   - `python -m quill.tools.quillin_lint <dir> --strict`
   - `python -m quill.tools.menu_lint`
3. **Docs in sync.** `CHANGELOG.md`, `docs/release notes/release<X>.md`,
   the user guide, and `CONTROL_REFERENCE.md` agree on the closed issues,
   the menu paths, and the shipped feature set.
4. **Translations template current.** `quill/locale/quill.pot` shows the
   target version stamp and a fresh `POT-Creation-Date`.
5. **No `.po` or `.mo` files ship.** Verified with
   `git ls-files | grep -E '\.(po|mo)$'` returning empty.
6. **Manifest regenerated.** `docs/site/updates/manifests/manifest-<X>.json`
   exists for the target version, alongside the historical `0.5.0`
   manifest that the public feed still points at during pre-release.
7. **Quillin Hub service code shipped.** `quillin-hub/` is a Flask
   service in this repo; the registry API, Submission Forge, sync
   worker, and smoke test are all in-tree. Public deployment
   (`hub.quillforall.org` -- DNS, hosting, Postgres) is a separate
   ops track and is tracked separately from the release cut. The
   Ed25519 publisher signature gate (`quill/tools/signing.py` plus
   the Submission Forge fail-closed hook) and the deployment
   runbook (`docs/release/quillin-hub-deployment.md`) are in; the
   protocol is documented in `docs/signing.md`.

## Tag-time flip

7. **Flip the GitHub Pages update feed.** Until the 0.7.0 stable tag is
   cut, `docs/site/updates/manifests/manifest-0.5.0.json` is the public
   feed so testers checking for updates do not see a phantom bump. When
   tagging the stable release, replace the feed manifest with
   `manifest-<X>.json` and re-sign the update feed
   (`python -m quill.tools.generate_signed_feed <X>`).
8. **Verify the feed.** `python -m quill.tools.verify_update_manifest`
   confirms the signature and the version stamp.
9. **Tag and push.** `git tag -s v<X> -m "QUILL <X>"` from the release
   branch, then `git push origin v<X>`.

## Post-tag checklist

10. **GitHub Release.** Create the release on GitHub from the tag, paste
    the release notes, and attach the signed installer artifacts.
11. **Announce.** Post in the community channel and update the website.
12. **Archive old notes.** Move the prior release notes into
    `docs/release notes/archived/`.

## Channels, publishing and promotion

Every QuillVille app with release channels (QUILL, QUILL Lite, Quill Radio,
QUILL Cast) is offered updates from one signed list per app,
`docs/site/updates/v2/<app>.json` plus `<app>.json.sig`, served from the Pages
site. A build is made and signed once; after that only the list changes. The
design is `docs/release-channels-plan.md`.

### The feed key stays on your computer

The lists are signed with the feed key you already use for the v1 feed
(`~/.config/quill/quill-feed-priv.key`, or the file named by
`QUILL_FEED_KEY_FILE`). No workflow signs a v2 list (the old v1 list is the one
exception; see below). Every script that changes a list
signs it as it writes, unless you pass `--no-sign`; then the `.sig` is removed,
GATE-FEED (`tests/unit/docs/test_release_feeds.py`) fails, and the change
cannot merge until you run `python scripts/feed_tool.py sign --app <app>`.

### Build numbers

Every app's version has a build number, so the same release number can ship
more than once. If Quill Radio 3.2.0 goes out and a fix has to follow without
a new number, the fix is 3.2.0 build 2, and Check for Updates offers it to
everyone on build 1.

- **Where it lives.** Next to each app's version constant: `_BUILD` in
  `quill/apps/radio.py` (and Converter, Weather, Inkwell, Player, Studio,
  Beacon), `APP_BUILD` in `quill/core/lite/__init__.py` and
  `quill/apps/podcasts_menu.py`, `__build__` in `quill/__init__.py` (QUILL) and
  in `standalone/social/quill_social/__init__.py`. A new version starts at
  build 1.
- **How it is written.** The canonical form is `3.2.0+2` (and
  `3.3.0-beta.2+5` for a pre-release). People see "3.2.0 (build 2)" in About,
  Update History, update notices and the Release Channel window. Release notes,
  changelog headings and file names keep saying `3.2.0`.
- **Tags.** A build is tagged as a pre-release identifier, never with a plus:
  `quill-radio-v3.2.0-build.2`, `quill-lite-v1.2.0-build.1`,
  `v1.0.0-build.1`, `v1.1.0-beta.1.build.3`. Copies installed before build
  numbers read a `+` in a sibling's tag as no version at all and in QUILL's own
  tag as part of the patch number (`v1.0.0+2` was 1.0.2 to them). They read
  `-build.2` as a pre-release of 3.2.0, so a copy on an older release (3.1.1)
  still sees the rebuild as newer and takes the newest build. Tag the first
  build of a version `-build.1` too, so those copies never pick the first build
  over a later one. Tags made before build numbers stay valid; they count as
  build 0.
- **Order.** The build only breaks ties: 3.2.0-rc.1 build 40 < 3.2.0 (no
  build) < 3.2.0 build 1 < build 2 < 3.2.1. A commit after a plus
  (`+g1a2b3c4`, Dev builds) is still identity, not order. GATE-VERSORT
  (`tests/unit/core/test_release_versioning.py`) holds the table.
- **What installed copies do.** A copy that already understands builds (this
  release onwards) is offered build 2 over build 1. A copy from before build
  numbers that is on the same number (3.2.0) is not offered the rebuild of
  3.2.0; it gets it with the next release. A copy on an older release is
  offered the newest build.
- **The installer.** Each `.iss` takes `/dAppBuild=` and `/dAppFileVersion=`
  from `build_release.ps1`. Windows shows `X.Y.Z.B` (3.2.0.2) in the file's
  Details tab, and the installer writes `version_build=3.2.0+2` beside
  `version=3.2.0` in `quill-app-version.ini`. It is a separate key so older
  runtimes, which read only `version`, are not confused, and it repeats the
  version so a stale key left by a newer install is ignored.

**Shipping a rebuild:**

1. Fix the problem. Keep the version; set the build constant to the next build
   (`_BUILD = 2`).
2. Add a line under the existing version's section in the app's changelog.
   There is no new section; the build is not a new release.
3. Build: `.\standalone\radio\scripts\build_release.ps1`. Without `-Build`, the
   script asks `scripts/release_build_number.py` for the next build after the
   newest tag published for this version, and stops if the build constant
   disagrees or the build is already published. Pass `-Build 2` when the
   published releases cannot be read. A Dev build (`-DevVersion`) has no build
   number.
4. Publish: `python scripts/publish_release.py --app radio --version 3.2.0
   --channel beta --dist standalone/radio/dist`. Without `--build` it lists the
   next build (`3.2.0+2`) under the tag `quill-radio-v3.2.0-build.2`. For
   QUILL, tag `v1.0.0-build.2` and use `--existing`, which lists the newest
   build already on GitHub.
5. Promote that exact build: `python scripts/promote_release.py --app radio
   --version 3.2.0+2 --to stable`. A version without a build is refused with
   the builds it could mean.

GATE-SIBVER compares builds when both the source and the published tag carry
one, and GATE-APPVER checks that each app's build constant, its installers'
`AppBuild` and `AppFileVersion`, and its build script agree.

### Publishing to Beta

A sibling app built on this computer:

```powershell
.\standalone\radio\scripts\build_release.ps1
python scripts/publish_release.py --app radio --version 3.3.0-beta.1 `
    --channel beta --dist standalone/radio/dist --notes-file notes.md
```

This hashes the files locally, creates the GitHub release as a prerelease that
is never "Latest", uploads the files, lists the build on Beta, and signs the
list. QUILL's own release is still built by `windows-release.yml` from a tag;
list it afterwards with `--existing`, which downloads and hashes the files
here rather than trusting GitHub's numbers:

```powershell
python scripts/publish_release.py --app quill --version 1.0.0-rc.1 --channel beta --existing
```

QUILL 1.0.0 becomes Stable this way: tag `v1.0.0-rc.1`, list it on Beta, then
build the final `v1.0.0` candidate, list it on Beta, and promote it.

**The page budget.** Installed Quill Radio 3.0.4 and QUILL Lite 1.1.2 read only
the first 30 releases of `Community-Access/quill`. `publish_release.py`
refuses to publish when any app's newest Stable release would be more than 20
releases down, and when a newer Beta is published it deletes the older Beta
release objects (the tags stay) and drops them from the list. Pass
`--keep-superseded` to keep them. `--dry-run` shows everything without
creating or writing anything.

Commit `docs/site/updates/v2` through a pull request as usual.

### Promoting

```powershell
python scripts/promote_release.py --app radio --version 3.3.0 --to stable --dry-run
python scripts/promote_release.py --app radio --version 3.3.0 --to stable
```

Every check is printed as PASS, WARN or FAIL, and one FAIL stops it: the
release exists; every file downloads again with the size and SHA-256 in the
list; the list's signature is valid; Stable takes only a final-numbered build
that was on Beta first; Authenticode when `QUILL_SIGN_REQUIRED=1`; tag, version
and file names agree; nothing the build carries is ahead of that app's own
channel; the changelog has the version; for Stable, a screen-reader sign-off
sheet at `docs/qa/signoffs/<app>-<version>.md` with `Result: pass`, `Tester:`,
`Screen readers:` and `Date:` lines; at least 7 days on Beta (1 on Dev before
Beta); and the documentation gates. A warning says when going back to the
previous Stable would need a saved copy.

A shorter soak needs a reason, and the reason is written into the build's
history in the list: `--skip-soak "fixes a crash on start in 3.2.0"`.

**Stable release notes.** A promotion to Stable rolls the notes up for you:
every changelog section after the current Stable build, up to this one, merged
into "What's new since 3.2.0". Lines marked `[beta-only]` are left out (with
anything indented under them), so are each Beta's "Known rough edges", and
"Before you update" comes first when a data format moved. `--dry-run` prints
the result; the real run makes it the GitHub release body and the feed's
summary. `--notes-file` gives your own notes instead. To see or save them
before promoting:

```powershell
python scripts/rollup_release_notes.py --app radio --from 3.2.0 --to 3.3.0
python scripts/rollup_release_notes.py --app radio --to 3.3.0 --out notes.md
python scripts/rollup_release_notes.py --app radio --to 3.3.0 --summary
```

On success the GitHub release stops being a prerelease (only QUILL's own
Stable release becomes "Latest"), its title says when it was promoted, the
list moves it to Stable with a fresh 90-day expiry, and a line goes into
`docs/release/promotions.log`.

**From GitHub instead.** Actions > promote-release runs the same script. The
checks job always runs as a dry run and uploads its report. The Stable job
runs in the GitHub Environment **stable-promotion**, so nothing reaches Stable
until you press Approve. Because the workflow has no key, it promotes with
`--no-sign` and opens a pull request on `promote/<app>-<version>-stable`; sign
it locally and push before merging.

### Dev builds

`dev-builds.yml` runs once a day at 06:17 UTC, and only builds when `main` has
changed since the last Dev build (`scripts/dev_build_plan.py` decides; Run
workflow with **force** overrides both rules). It builds every app unsigned,
with a version like `3.3.1-dev.20261003.1`, and publishes them to
**Community-Access/quillville-dev-builds**, never to the main repository.

Dev builds reach the Dev channel only when you list them, from your computer:

```powershell
python scripts/publish_release.py --app radio --version 3.3.1-dev.20261003.1 --channel dev --existing
```

A good Dev build can go to Beta as-is: `promote_release.py --to beta`.

### Withdrawing a build

```powershell
python scripts/revoke_release.py --app radio --version 3.4.0-beta.1 `
    --reason "can lose favorites on first start" --replacement 3.4.0-beta.2 --dry-run
python scripts/revoke_release.py --app radio --version 3.4.0-beta.1 `
    --reason "can lose favorites on first start" --replacement 3.4.0-beta.2
```

The build is marked withdrawn in the list, so it is never offered again and is
never a way back. Each channel that offered it falls back to the build before
it, and the script says which. Its GitHub release title gains "(withdrawn)".
Nothing is deleted: people who have it can still move forward or back, and the
files stay downloadable. The list is signed as it is written, or left unsigned
with `--no-sign` for `python scripts/feed_tool.py sign --app radio` later.
`feed_tool.py revoke` does exactly the same; this script is the one to use.

### Data formats (GATE-DATAFMT)

Going back to Stable is allowed only when the older build can read what the
newer one saved, and that is decided from the version numbers in
`quill/core/data_formats.py`. GATE-DATAFMT keeps them honest: it fingerprints
what each format is saved from (dataclass fields and types, QUILL's settings
groups, schema stamps, and the serializer code for stores with no dataclass)
against `tests/unit/core/fixtures/data_format_fingerprints.json`. It runs in
`tests/unit/core/test_data_formats.py` and as the data-formats row of
`platform_report`.

When it fails, decide which it is:

- **An older build would misread or lose the data.** Bump `current` (and
  `reads_up_to`) for that format in `data_formats.py`, then record it:
  `python -m quill.tools.data_format_audit --write`.
- **Older builds read it safely** (an added field they ignore):
  `python -m quill.tools.data_format_audit --write --accept radio.favorites --note "adds a station note; older builds ignore it"`.
  A field whose type changed cannot be accepted this way; that is a bump.

### Rehearsing the whole cycle

`tests/unit/scripts/test_channel_rehearsal_offline.py` runs in CI: publish on
Dev, promote to Beta and Stable, publish the next Beta, withdraw it, and go
back to Stable, with the real scripts, a fake `gh` and a throwaway key, the app
reading the lists through `QUILL_UPDATE_FEED_BASE`. Before a first real
promotion, run the same flow over HTTPS against a throwaway server:

```powershell
$env:QUILL_CHANNEL_REHEARSAL = "1"
$env:QUILL_UPDATE_FEED_BASE = "https://rehearsal.example/updates/v2/"
$env:QUILL_REHEARSAL_SERVE_DIR = "D:/rehearsal/updates/v2"
pytest tests/integration/test_channel_rehearsal.py -v
```

The server's host must be trusted (`QUILL_UPDATE_TRUSTED_HOSTS` if it is not
GitHub's). Nothing touches the real lists, your key or GitHub.

### Feed expiry and the 14-day warning

Each list expires 90 days after it was last written. A list past its date is
treated as "couldn't check" on every computer, so an expired list stops every
update. Every publish or promotion refreshes it. Between releases,
`publish_release.py`, `promote_release.py`, `feed_tool.py verify` and
`platform_report` (the release-feeds row) warn once any list is within 14 days
of expiring. To refresh one without a release:

```powershell
python scripts/feed_tool.py refresh --app radio
```

### Runtime slots

Beta and Dev apps run on their own copy of the shared runtime
(`Runtime\3.13-beta`, `Runtime\3.13-dev`). Publish a Stable runtime with
`build_runtime_installer.ps1 -Publish` (it goes to `runtime-stable` and to
`runtime-latest`, which installed launchers know and which stays for ever) and
a Beta runtime with `-Publish -Channel beta` (`runtime-beta`). There is no Dev
runtime installer: Dev runtimes do not repair themselves.

### One-time setup (owner)

- Create the repository **Community-Access/quillville-dev-builds** with a README
  so it has a `main` branch.
- Add the repository secret **DEV_BUILDS_TOKEN** to `Community-Access/quill`: a
  fine-grained token with Contents read and write on the dev-builds repository
  only.
- Create the GitHub Environment **stable-promotion** in `Community-Access/quill`
  with yourself as the required reviewer.
- Publish the first signed list for each app before the first channel-aware
  release ships; until a list exists, apps keep using the GitHub path.

### The old v1 list and its CI key (decided 2026-10-04)

The old v1 update list (`.quill-update-feed-v1.json`) is still signed in CI by
`windows-release.yml` with the `QUILL_FEED_SIGNING_KEY` secret, because copies
from before release channels read it. Leave that alone for now. Once every
app's channel-aware release (QUILL 1.0.0, QUILL Lite 1.2.0, Quill Radio 3.2.0,
QUILL Cast 2.0.0) has been out for one full release cycle, remove the secret
from CI and stop signing the v1 list. Until then, do not touch it.

## macOS signed/notarized DMG runbook (start to finish)

Use this when onboarding a maintainer or standing up macOS release signing for
the first time. This is the canonical operational path from fresh Apple account
to a shipped, trusted DMG.

### 1) Apple account and certificate setup (one-time)

1. Join and activate Apple Developer Program membership.
2. In Apple Developer, create a **Developer ID Application** certificate.
3. On macOS, install the certificate in Keychain Access, then export it as a
   password-protected `.p12`.
4. In App Store Connect, create an API key for notarization and download the
   `.p8` key file.
5. Record these values in your release vault:
   - Team ID
   - API Key ID
   - API Issuer ID
   - `.p12` password
   - Exact codesign identity string (example: `Developer ID Application: Team Name (TEAMID)`).

### 2) Local prerequisites

1. Install GitHub CLI (`gh`) and authenticate with repo admin/maintainer scope.
2. Ensure the target repo contains `.github/workflows/macos-release.yml`.
3. From terminal:

```powershell
cd S:\quill
gh auth status
gh repo set-default Community-Access/quill
```

### 3) Create release environment

1. Create the protected GitHub Actions environment:

```powershell
gh api --method PUT repos/Community-Access/quill/environments/macos-release
```

2. In GitHub UI, configure environment protections for `macos-release`:
   - Required reviewers for manual approval.
   - Restrict deployment branches as needed.

### 4) Upload all required secrets

1. File secrets:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\DeveloperID.p12")) | gh secret set -e macos-release BUILD_CERTIFICATE_BASE64
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\AuthKey_ABC123XYZ.p8")) | gh secret set -e macos-release APPLE_API_KEY_B64
```

2. Prompted text secrets:

```powershell
gh secret set -e macos-release P12_PASSWORD
gh secret set -e macos-release KEYCHAIN_PASSWORD
gh secret set -e macos-release MACOS_CODESIGN_IDENTITY
gh secret set -e macos-release APPLE_API_KEY_ID
gh secret set -e macos-release APPLE_API_ISSUER
gh secret set -e macos-release APPLE_TEAM_ID
```

3. Verify:

```powershell
gh secret list -e macos-release
```

### 5) Dry run on branch

1. Trigger a manual build on your working branch:

```powershell
gh workflow run macos-release.yml --ref <branch-name>
gh run list --workflow macos-release.yml --limit 5
gh run watch
```

2. Confirm artifacts exist:
   - `Quill.dmg`
   - `Quill.app` (if workflow uploads app bundle)

3. If the run fails, triage quickly:
   - Certificate import errors: re-export `.p12`, recheck `P12_PASSWORD`.
   - Identity mismatch: re-copy `MACOS_CODESIGN_IDENTITY` from Keychain.
   - Notary auth errors: verify Team ID, Issuer ID, Key ID, and `.p8` source.

### 6) Gate beta publication

1. Do not publish external beta artifacts unless macOS workflow is green.
2. Require the macOS signed/notarized workflow in PR/release policy for any
   beta that includes non-engineering testers.

### 7) Release execution

1. Complete normal release pre-tag checks from this file.
2. Push tag (`v<X>`) to trigger release workflows.
3. Verify GitHub release includes signed Windows artifacts and signed/notarized
   macOS DMG.
4. Perform clean-machine install checks on macOS:
   - Download DMG from release artifacts.
   - Install without bypass commands.
   - Launch with no unidentified-developer warnings.

### 8) Ongoing operations

1. Track certificate and API key expiry on calendar.
2. Rotate credentials before expiry and validate with a branch dry run.
3. Keep at least two maintainers with documented recovery access.

Full runbook:
`docs/release/quill-macos-signing-notarization-runbook.md`

Quick operator checklist:
`docs/release/macos-signed-notarized-release-day-checklist.md`

Command-only script:
`docs/release/macos-release-day-commands.ps1`