# QUILL macOS Signed and Notarized Release Day Checklist

Last updated: 2026-07-02
Audience: Release maintainer
Goal: Produce and verify a trusted QUILL macOS DMG end to end.

## 1. One-time prerequisites

- Apple Developer Program membership is active.
- Developer ID Application certificate exists.
- Certificate is exported from Keychain Access as a password-protected .p12.
- App Store Connect API key (.p8) exists for notarization.
- The following values are available in a secure vault:
  - Team ID
  - API Key ID
  - API Issuer ID
  - P12 password
  - Codesign identity string, for example: Developer ID Application: Team Name (TEAMID)

## 2. Local tools and repo preflight

Run in PowerShell:

```powershell
cd S:\quill
gh auth status
gh repo set-default Community-Access/quill
```

Confirm workflow exists:

- .github/workflows/macos-release.yml

## 3. Create or confirm GitHub environment

Create environment:

```powershell
gh api --method PUT repos/Community-Access/quill/environments/macos-release
```

In GitHub UI, confirm:

- Environment name: macos-release
- Required reviewers enabled
- Deployment branch restrictions set as desired

## 4. Upload required secrets

Set file-based secrets:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\DeveloperID.p12")) | gh secret set -e macos-release BUILD_CERTIFICATE_BASE64
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\AuthKey_ABC123XYZ.p8")) | gh secret set -e macos-release APPLE_API_KEY_B64
```

Set text secrets (prompted):

```powershell
gh secret set -e macos-release P12_PASSWORD
gh secret set -e macos-release KEYCHAIN_PASSWORD
gh secret set -e macos-release MACOS_CODESIGN_IDENTITY
gh secret set -e macos-release APPLE_API_KEY_ID
gh secret set -e macos-release APPLE_API_ISSUER
gh secret set -e macos-release APPLE_TEAM_ID
```

Verify:

```powershell
gh secret list -e macos-release
```

Expected secret names:

- BUILD_CERTIFICATE_BASE64
- P12_PASSWORD
- KEYCHAIN_PASSWORD
- MACOS_CODESIGN_IDENTITY
- APPLE_API_KEY_B64
- APPLE_API_KEY_ID
- APPLE_API_ISSUER
- APPLE_TEAM_ID

## 5. Dry run on branch

Run on working branch first:

```powershell
gh workflow run macos-release.yml --ref <branch-name>
gh run list --workflow macos-release.yml --limit 5
gh run watch
```

Optional browser view:

```powershell
gh run view --web
```

Pass criteria:

- Workflow run is green.
- Smoke job is green (trust checks + startup launch check).
- DMG artifact exists.
- No codesign errors.
- No notarization rejection.

## 6. Tag-time release run

After normal release checks in RELEASE.md are complete, push the version tag:

```powershell
git tag -s v<X> -m "QUILL <X>"
git push origin v<X>
```

Then monitor macOS workflow:

```powershell
gh run list --workflow macos-release.yml --limit 5
gh run watch
```

## 7. Artifact and trust verification

Verify in GitHub Actions artifacts/release assets:

- Quill.dmg exists for this version.
- DMG came from successful signed/notarized workflow run.

Verify on a clean macOS machine:

- Download Quill.dmg.
- Install without bypass commands.
- Launch with no unidentified developer warning.

## 8. External beta go or no-go

Go only if all are true:

- macOS workflow green.
- macOS smoke job green.
- Signed app inside artifact.
- Notarization succeeded.
- Ticket stapled by workflow.
- Clean-machine install and launch succeeded.

No-go if any are missing.

## 9. Fast triage map

- Certificate import failed: re-export .p12 and re-check P12_PASSWORD.
- Identity mismatch: copy exact identity text from Keychain and reset MACOS_CODESIGN_IDENTITY.
- Notary auth failed: verify APPLE_API_KEY_ID, APPLE_API_ISSUER, APPLE_TEAM_ID, and .p8 source key.
- Notary rejection: inspect workflow logs and confirm hardened runtime and entitlements are applied.

## 10. Operations hygiene

- Keep at least two maintainers with access to release credential process.
- Rotate certificate and API key before expiry.
- Re-run dry run after each credential rotation.
- Never publish external beta artifacts when macOS signed/notarized workflow is failing.

## References

- RELEASE.md
- docs/release/quill-macos-signing-notarization-runbook.md
- docs/release/macos-release-day-commands.ps1
