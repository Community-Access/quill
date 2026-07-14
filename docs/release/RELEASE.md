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