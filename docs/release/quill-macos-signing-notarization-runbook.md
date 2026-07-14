# QUILL macOS DMG Signing and Notarization Runbook

**Last updated:** 2026-07-02  
**Owner:** Release Engineering  
**Product:** QUILL  
**Project home:** Community Access, <http://www.community-access.org>  
**Signing owner for first macOS distribution:** Jeff Bishop  
**Recommended bundle identifier:** `org.community-access.quill`  
**Primary release target:** Signed and notarized macOS `.dmg` produced by GitHub Actions

---

## 1. Executive decision

QUILL can and should produce a working macOS DMG through GitHub Actions. GitHub Actions can automate the build, signing, notarization, stapling, verification, and artifact upload steps, but GitHub does not provide Apple trust. Apple trust comes from Jeff Bishop's active Apple Developer Program membership, a Developer ID Application certificate, and Apple notarization credentials.

For the first QUILL macOS beta, sign under:

```text
Developer ID Application: Jeff Bishop (TEAMID)
```

Use Community Access as the project identity:

```text
App display name: QUILL
Bundle identifier: org.community-access.quill
Project / website: Community Access
macOS developer shown by Gatekeeper: Jeff Bishop
Distribution format: signed and notarized DMG
```

Recommended public wording:

> QUILL is a Community Access project. The macOS build is signed and notarized by Apple under Jeff Bishop's Apple Developer account.

For any external beta, sign and notarize. Unsigned builds should be limited to short-lived internal engineering use only.

---

## 2. Why this matters

If QUILL ships as an unsigned or non-notarized macOS app, users may hit Gatekeeper warnings such as unknown developer, app cannot be opened safely, quarantine friction, or managed-device policy blocks. That creates a product trust problem and an accessibility problem.

For QUILL, setup needs to be predictable, keyboard friendly, and supportable. Asking blind and screen reader users to bypass macOS security prompts is not acceptable for public distribution.

Signing and notarization reduce:

- Failed installs.
- Confusing security prompts.
- Support burden.
- Enterprise and managed-device friction.
- Trust concerns around a new assistive technology tool.

Apple describes Developer ID Application certificates as certificates used to sign Mac apps outside the Mac App Store, and Apple’s notarization tools support submitting software to the Apple notary service and stapling the resulting ticket to the distributed artifact. See the reference section for official Apple links.

---

## 3. Beta policy recommendation

| Release type | Signing required? | Notarization required? | Notes |
|---|---:|---:|---|
| Internal alpha, core engineering only | Optional temporarily | Optional temporarily | Accept only if short-lived and clearly marked internal. |
| Private beta with external testers | Yes | Yes | Treat as real software distribution. |
| Public beta | Yes | Yes | Required for user trust. |
| Release candidate | Yes | Yes | Required. |
| Production release | Yes | Yes | Mandatory. |

Go/no-go rule:

QUILL should not publish an external macOS beta unless all of these are true:

- The `.app` is signed.
- The artifact is notarized.
- The notarization ticket is stapled.
- A clean-device install test passed.
- QUILL launches without manual security bypass steps.

---

## 4. What can and cannot be done without a Mac

### 4.1 What can be done from Windows

You can use a Windows browser to do most Apple portal work:

- Sign in to Apple Developer.
- Confirm Apple Developer Program membership.
- View Team ID.
- Create the Developer ID Application certificate record.
- Upload a certificate signing request.
- Download the `.cer` certificate.
- Sign in to App Store Connect.
- Request App Store Connect API access if needed.
- Generate a team API key.
- Download the `.p8` API key.
- Use GitHub CLI to create environments and upload GitHub Actions secrets.

### 4.2 What should not be done from iPhone

Use iPhone only for Apple ID two-factor authentication or emergency account checks. Do not use it as the primary workflow for handling:

- `.csr`
- `.cer`
- `.p8`
- `.p12`
- certificate passwords
- Team ID / Key ID / Issuer ID

The files are too sensitive and too easy to misplace or mishandle from mobile file workflows.

### 4.3 What still needs macOS somewhere

The final signing/notarization workflow needs macOS somewhere because the normal toolchain uses:

```bash
codesign
xcrun notarytool
xcrun stapler
spctl
```

That macOS environment can be:

1. A borrowed Mac used once to create/export the `.p12` and test the process.
2. A rented/cloud Mac.
3. A GitHub Actions macOS runner.
4. A self-hosted Mac runner.

Recommended QUILL path:

```text
Windows = command center
Apple Developer website = one-time credential creation
GitHub Actions macOS runner = build/sign/notarize/staple/release
Borrowed/cloud Mac = optional first-time .p12 creation and VoiceOver smoke test
```

---

## 5. Target architecture: magical but controlled

The desired release path is:

```text
Developer pushes a release tag
        ↓
GitHub Actions starts macos-release workflow
        ↓
macOS runner builds QUILL.app
        ↓
Temporary keychain is created
        ↓
Developer ID .p12 is imported
        ↓
QUILL.app is signed with hardened runtime
        ↓
DMG is created
        ↓
DMG/app is submitted to Apple notarization
        ↓
Ticket is stapled
        ↓
Gatekeeper verification runs
        ↓
Signed/notarized DMG is uploaded as a release artifact
```

The release pipeline should fail closed. If signing, notarization, stapling, or Gatekeeper verification fails, the pipeline should fail and no external beta artifact should be published.

---

## 6. Phase 0 — Apple account and release ownership

Assumption: an Apple Developer account exists, but nothing else has been set up.

### 6.1 Confirm Apple Developer Program membership

1. Open <https://developer.apple.com/account>
2. Sign in with the Apple ID tied to the paid Apple Developer Program membership.
3. Go to **Membership details**.
4. Confirm:
   - Membership is active.
   - Role is **Account Holder**.
   - Team name is Jeff Bishop or your personal developer team.
   - Team ID is visible.
5. Copy the Team ID into a secure notes file.

Record:

```text
APPLE_TEAM_ID=__________
APPLE_ACCOUNT_HOLDER=Jeff Bishop
APPLE_SIGNING_DISPLAY_NAME=Jeff Bishop
```

### 6.2 Decide release custody

For QUILL, assign at least two maintainers for operational continuity, even if only Jeff holds the Apple account initially.

Minimum roles:

| Role | Responsibility |
|---|---|
| Apple Account Holder | Owns Apple Developer account, certificates, API keys, legal agreements. |
| Release Maintainer 1 | Maintains GitHub Actions and release secrets. |
| Release Maintainer 2 | Backup for credential rotation and break-glass recovery. |

If only one person currently has Apple access, document that clearly as a temporary risk.

### 6.3 Create a secure release vault

Create a password-manager entry or secure vault folder named:

```text
QUILL Apple Release - Jeff Bishop Developer ID
```

Store only metadata at first:

```text
Team ID:
Apple ID email:
Account Holder:
Signing identity, once known:
API Key ID, once known:
Issuer ID, once known:
P12 password, once created:
Keychain password for CI, once created:
```

Do not store these in the QUILL Git repository.

---

## 7. Phase 1 — Create the Developer ID Application certificate

Apple Developer ID certificates are created from **Certificates, Identifiers & Profiles**. For QUILL, you need a **Developer ID Application** certificate. You only need a **Developer ID Installer** certificate if QUILL ships as a `.pkg` installer.

For the recommended first release as a `.dmg`, start with only:

```text
Developer ID Application: Jeff Bishop (TEAMID)
```

### 7.1 Recommended path if you can access a Mac once

Use this path if you can borrow, rent, or temporarily access a Mac.

#### Step A — Create a certificate signing request on macOS

1. Open **Keychain Access**.
2. Choose **Keychain Access > Certificate Assistant > Request a Certificate From a Certificate Authority**.
3. Enter the Apple Developer email address.
4. For **Common Name**, use:

```text
Jeff Bishop QUILL Developer ID Key
```

5. Leave **CA Email Address** blank.
6. Select **Saved to disk**.
7. Save the file as:

```text
quill-developer-id.certSigningRequest
```

#### Step B — Create the certificate on Apple Developer

1. Open <https://developer.apple.com/account>
2. Go to **Certificates, Identifiers & Profiles**.
3. Select **Certificates** in the sidebar.
4. Click the **+** button.
5. Under **Software**, select **Developer ID**.
6. Select **Developer ID Application**.
7. Click **Continue**.
8. Upload `quill-developer-id.certSigningRequest`.
9. Click **Continue**.
10. Download the `.cer` file.
11. Double-click the `.cer` on the Mac to install it into Keychain Access.

#### Step C — Confirm the identity exists

Run:

```bash
security find-identity -v -p codesigning
```

Look for a line like:

```text
Developer ID Application: Jeff Bishop (TEAMID)
```

Copy the exact string. This becomes:

```text
MACOS_CODESIGN_IDENTITY=Developer ID Application: Jeff Bishop (TEAMID)
```

#### Step D — Export the `.p12`

1. Open **Keychain Access**.
2. Choose the **login** keychain.
3. Select **My Certificates**.
4. Find `Developer ID Application: Jeff Bishop (TEAMID)`.
5. Expand it and confirm a private key appears beneath it.
6. Right-click the certificate.
7. Choose **Export**.
8. Save as:

```text
DeveloperID_Application_JeffBishop.p12
```

9. Set a strong password.
10. Store the `.p12` file and password in the secure release vault.

Exit criteria:

- `.p12` exists.
- `.p12` password is known and stored securely.
- Exact signing identity string is captured.

### 7.2 Advanced path if you only have Windows

Apple’s official instructions show creating the CSR with Keychain Access on macOS. However, a CSR is a standard certificate signing request. If you cannot access a Mac at all, you can generate the private key and CSR from Windows using OpenSSL, upload the CSR to Apple Developer, download the `.cer`, and create the `.p12` yourself.

Use this only if you are comfortable managing private keys.

#### Step A — Install OpenSSL on Windows

Use a trusted OpenSSL distribution or Git Bash environment that includes OpenSSL.

Verify:

```powershell
openssl version
```

#### Step B — Generate private key and CSR

From a secure folder:

```powershell
mkdir C:\QUILL-Apple-Release
cd C:\QUILL-Apple-Release

openssl genrsa -out quill-developer-id.key 2048

openssl req -new `
  -key quill-developer-id.key `
  -out quill-developer-id.csr `
  -subj "/CN=Jeff Bishop QUILL Developer ID Key"
```

Important:

- `quill-developer-id.key` is the private key.
- Never commit it to Git.
- Never email it.
- Store it in the secure release vault.

#### Step C — Upload CSR to Apple

1. Open <https://developer.apple.com/account>
2. Go to **Certificates, Identifiers & Profiles**.
3. Select **Certificates**.
4. Click **+**.
5. Under **Software**, select **Developer ID**.
6. Select **Developer ID Application**.
7. Upload `quill-developer-id.csr`.
8. Download the `.cer` file.
9. Save it as:

```text
DeveloperID_Application_JeffBishop.cer
```

#### Step D — Convert Apple `.cer` and private key into `.p12`

Apple certificates may need to be converted before packaging with OpenSSL. Try:

```powershell
openssl x509 -inform DER `
  -in DeveloperID_Application_JeffBishop.cer `
  -out DeveloperID_Application_JeffBishop.pem

openssl pkcs12 -export `
  -inkey quill-developer-id.key `
  -in DeveloperID_Application_JeffBishop.pem `
  -out DeveloperID_Application_JeffBishop.p12
```

Set a strong export password when prompted.

Exit criteria:

- `DeveloperID_Application_JeffBishop.p12` exists.
- P12 password is stored securely.
- Private key is stored securely or archived according to release policy.

Important caveat:

This Windows-only certificate path can produce the `.p12`, but QUILL still needs a macOS runner to actually sign, notarize, staple, and verify.

---

## 8. Phase 2 — Create App Store Connect API key for notarization

Use an App Store Connect API key rather than Apple ID + app-specific password. It is better for CI and easier to rotate.

### 8.1 Request API access if required

1. Open <https://appstoreconnect.apple.com>
2. Sign in.
3. Go to **Users and Access**.
4. Open **Integrations**.
5. The page should open with **App Store Connect API** selected.
6. If prompted, click **Request Access**.
7. Agree to the terms and submit.

Only the Account Holder can request App Store Connect API access.

### 8.2 Generate a team API key

1. Open <https://appstoreconnect.apple.com>
2. Go to **Users and Access**.
3. Open **Integrations**.
4. Select **App Store Connect API**.
5. Select **Team Keys**.
6. Click **Generate API Key** or the **+** button if a key already exists.
7. Name it:

```text
QUILL Notarization
```

8. Assign the least role that works for notarization in your build process. If unsure for the first pass, use a key created by the Account Holder and document the role used.
9. Click **Generate**.
10. Download the `.p8` file immediately.

Important:

Apple API keys are private and can only be downloaded once. If you lose the `.p8`, revoke the key and create a new one.

Record:

```text
APPLE_API_KEY_ID=__________
APPLE_API_ISSUER=__________
APPLE_TEAM_ID=__________
APPLE_API_KEY_FILENAME=AuthKey_XXXXXXXXXX.p8
```

Store the `.p8` in the secure release vault.

---

## 9. Phase 3 — Choose QUILL app identity and artifact names

Use stable values now so future updates keep the same identity.

Recommended values:

```text
APP_NAME=QUILL
BUNDLE_ID=org.community-access.quill
MACOS_CODESIGN_IDENTITY=Developer ID Application: Jeff Bishop (TEAMID)
DMG_NAME=QUILL-macOS.dmg
RELEASE_ENVIRONMENT=macos-release
```

Avoid:

```text
com.jeffbishop.quill
```

The signing account is Jeff Bishop, but the project home is Community Access. The bundle ID should reflect the long-term project home.

---

## 10. Phase 4 — GitHub environment and secrets

Use GitHub environment secrets rather than broad repository secrets. The release environment should be protected so accidental workflow changes or branch pushes cannot publish a public beta without review.

Recommended environment:

```text
macos-release
```

### 10.1 Create the GitHub environment from Windows PowerShell

From the repository root:

```powershell
cd S:\quill
gh auth status
gh repo set-default Community-Access/quill
```

Create the protected environment:

```powershell
gh api --method PUT repos/Community-Access/quill/environments/macos-release
```

Then configure protection rules in the GitHub web UI:

1. Open the QUILL repository on GitHub.
2. Go to **Settings**.
3. Go to **Environments**.
4. Select **macos-release**.
5. Add required reviewers.
6. Restrict deployment branches or tags if desired.
7. Save.

Recommended protection:

- Required reviewer: Jeff Bishop or a designated release maintainer.
- Allowed branches/tags: release branches and version tags only.
- No external beta job should run without environment approval.

### 10.2 Required secrets

Use these exact names to match the workflow examples later:

| Secret | Meaning |
|---|---|
| `BUILD_CERTIFICATE_BASE64` | Base64-encoded `DeveloperID_Application_JeffBishop.p12`. |
| `P12_PASSWORD` | Password used when exporting the `.p12`. |
| `KEYCHAIN_PASSWORD` | Temporary keychain password used inside GitHub Actions. |
| `MACOS_CODESIGN_IDENTITY` | Exact identity string from `security find-identity`. |
| `APPLE_API_KEY_B64` | Base64-encoded `AuthKey_XXXXXXXXXX.p8`. |
| `APPLE_API_KEY_ID` | Key ID from App Store Connect. |
| `APPLE_API_ISSUER` | Issuer ID from App Store Connect. |
| `APPLE_TEAM_ID` | Apple Developer Team ID. |

Optional secrets:

| Secret | Meaning |
|---|---|
| `DMG_SIGNING_IDENTITY` | Usually same as `MACOS_CODESIGN_IDENTITY`; useful if signing DMG separately. |
| `APPLE_ID` | Only for fallback Apple ID notarization path; not recommended. |
| `APPLE_APP_SPECIFIC_PASSWORD` | Only for fallback Apple ID notarization path; not recommended. |

### 10.3 Add file-based secrets from Windows PowerShell

Replace paths with your actual files.

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\DeveloperID_Application_JeffBishop.p12")) | gh secret set -e macos-release BUILD_CERTIFICATE_BASE64

[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\AuthKey_ABC123XYZ.p8")) | gh secret set -e macos-release APPLE_API_KEY_B64
```

### 10.4 Add prompt-based text secrets

```powershell
gh secret set -e macos-release P12_PASSWORD
gh secret set -e macos-release KEYCHAIN_PASSWORD
gh secret set -e macos-release MACOS_CODESIGN_IDENTITY
gh secret set -e macos-release APPLE_API_KEY_ID
gh secret set -e macos-release APPLE_API_ISSUER
gh secret set -e macos-release APPLE_TEAM_ID
```

Suggested `KEYCHAIN_PASSWORD`:

- Generate a long random value.
- It only protects the temporary keychain on the runner.
- Store it in the password manager anyway.

### 10.5 Verify secrets were created

```powershell
gh secret list -e macos-release
```

Exit criteria:

- All required secrets exist.
- Secrets are scoped to `macos-release`.
- Environment has approval protection.

---

## 11. Phase 5 — Add local helper scripts

Create these scripts in the repository:

```text
scripts/macos/
  check-apple-signing-ready.sh
  sign-notarize-quill.sh
  verify-gatekeeper.sh
```

These are useful on a borrowed/cloud Mac or a self-hosted Mac runner.

### 11.1 `scripts/macos/check-apple-signing-ready.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-$HOME/QUILL-Apple-Release/quill-apple-release.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

echo "Checking Apple command line tools..."
xcrun --find codesign >/dev/null
xcrun --find notarytool >/dev/null
xcrun --find stapler >/dev/null

echo "Checking Developer ID signing identity..."
security find-identity -v -p codesigning | grep -F "$MACOS_CODESIGN_IDENTITY" >/dev/null

echo "Checking App Store Connect API key..."
if [[ ! -f "$APPLE_API_KEY_PATH" ]]; then
  echo "Missing API key: $APPLE_API_KEY_PATH"
  exit 1
fi

if [[ -z "${APPLE_TEAM_ID:-}" ]]; then
  echo "APPLE_TEAM_ID is empty"
  exit 1
fi

echo "QUILL Apple signing setup looks ready."
echo "Signing identity: $MACOS_CODESIGN_IDENTITY"
echo "Team ID: $APPLE_TEAM_ID"
```

### 11.2 `scripts/macos/sign-notarize-quill.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-$HOME/QUILL-Apple-Release/quill-apple-release.env}"
APP_PATH="${2:-dist/QUILL.app}"
OUTPUT_DIR="${3:-dist}"

# shellcheck source=/dev/null
source "$ENV_FILE"

ZIP_PATH="$OUTPUT_DIR/QUILL-macOS-notary.zip"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app bundle: $APP_PATH"
  exit 1
fi

echo "Signing QUILL with hardened runtime..."
codesign \
  --force \
  --deep \
  --timestamp \
  --options runtime \
  --sign "$MACOS_CODESIGN_IDENTITY" \
  "$APP_PATH"

echo "Verifying code signature..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

echo "Creating notarization zip..."
rm -f "$ZIP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

echo "Submitting to Apple notarization..."
xcrun notarytool submit "$ZIP_PATH" \
  --key "$APPLE_API_KEY_PATH" \
  --key-id "$APPLE_API_KEY_ID" \
  --issuer "$APPLE_API_ISSUER" \
  --team-id "$APPLE_TEAM_ID" \
  --wait

echo "Stapling notarization ticket to app..."
xcrun stapler staple "$APP_PATH"
xcrun stapler validate "$APP_PATH"

echo "Running Gatekeeper assessment..."
spctl --assess --type execute --verbose "$APP_PATH"

echo "QUILL is signed, notarized, stapled, and Gatekeeper-verified."
```

### 11.3 `scripts/macos/verify-gatekeeper.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-dist/QUILL.app}"

if [[ ! -e "$TARGET" ]]; then
  echo "Missing target: $TARGET"
  exit 1
fi

echo "Checking code signature..."
codesign --verify --deep --strict --verbose=2 "$TARGET"

echo "Checking notarization staple..."
xcrun stapler validate "$TARGET"

echo "Checking Gatekeeper assessment..."
spctl --assess --type execute --verbose "$TARGET"

echo "Gatekeeper verification passed: $TARGET"
```

---

## 12. Phase 6 — GitHub Actions workflow

Create:

```text
.github/workflows/macos-release.yml
```

This workflow is intentionally conservative:

- Runs on macOS.
- Uses environment secrets.
- Creates a temporary keychain.
- Imports the Developer ID certificate.
- Writes the App Store Connect API key to disk.
- Builds QUILL.
- Signs QUILL.
- Creates a DMG.
- Notarizes and staples.
- Uploads the final artifact.

You must adapt the build commands to QUILL's actual macOS build process.

```yaml
name: macOS Release

on:
  workflow_dispatch:
  push:
    tags:
      - "v*"

permissions:
  contents: read

env:
  APP_NAME: QUILL
  BUNDLE_ID: org.community-access.quill
  DMG_NAME: QUILL-macOS.dmg

jobs:
  build-sign-notarize:
    name: Build, sign, notarize, and package QUILL for macOS
    runs-on: macos-latest
    environment: macos-release
    timeout-minutes: 90

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Show macOS and Xcode environment
        run: |
          sw_vers
          xcodebuild -version || true
          xcrun --find codesign
          xcrun --find notarytool
          xcrun --find stapler

      - name: Decode signing certificate and API key
        env:
          BUILD_CERTIFICATE_BASE64: ${{ secrets.BUILD_CERTIFICATE_BASE64 }}
          APPLE_API_KEY_B64: ${{ secrets.APPLE_API_KEY_B64 }}
        run: |
          mkdir -p "$RUNNER_TEMP/apple"
          echo "$BUILD_CERTIFICATE_BASE64" | base64 --decode > "$RUNNER_TEMP/apple/developer_id.p12"
          echo "$APPLE_API_KEY_B64" | base64 --decode > "$RUNNER_TEMP/apple/AuthKey.p8"
          chmod 600 "$RUNNER_TEMP/apple/AuthKey.p8"

      - name: Create temporary keychain and import Developer ID certificate
        env:
          KEYCHAIN_PASSWORD: ${{ secrets.KEYCHAIN_PASSWORD }}
          P12_PASSWORD: ${{ secrets.P12_PASSWORD }}
        run: |
          KEYCHAIN_PATH="$RUNNER_TEMP/quill-signing.keychain-db"

          security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
          security set-keychain-settings -lut 21600 "$KEYCHAIN_PATH"
          security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"

          security import "$RUNNER_TEMP/apple/developer_id.p12" \
            -P "$P12_PASSWORD" \
            -A \
            -t cert \
            -f pkcs12 \
            -k "$KEYCHAIN_PATH"

          security list-keychain -d user -s "$KEYCHAIN_PATH" login.keychain-db
          security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
          security find-identity -v -p codesigning "$KEYCHAIN_PATH"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then python -m pip install -r requirements.txt; fi
          if [ -f requirements-macos.txt ]; then python -m pip install -r requirements-macos.txt; fi

      - name: Build QUILL.app
        run: |
          # Replace this block with the actual QUILL macOS build command.
          # Examples might include PyInstaller, Briefcase, or a custom build script.
          if [ -f scripts/macos/build-app.sh ]; then
            bash scripts/macos/build-app.sh
          else
            echo "Missing scripts/macos/build-app.sh. Add the real QUILL macOS build command here."
            exit 1
          fi

          test -d "dist/QUILL.app"

      - name: Sign QUILL.app
        env:
          MACOS_CODESIGN_IDENTITY: ${{ secrets.MACOS_CODESIGN_IDENTITY }}
        run: |
          codesign \
            --force \
            --deep \
            --timestamp \
            --options runtime \
            --sign "$MACOS_CODESIGN_IDENTITY" \
            "dist/QUILL.app"

          codesign --verify --deep --strict --verbose=2 "dist/QUILL.app"
          codesign -dv --verbose=4 "dist/QUILL.app" || true

      - name: Create DMG
        run: |
          mkdir -p dist/dmg-root
          cp -R "dist/QUILL.app" "dist/dmg-root/QUILL.app"
          ln -s /Applications "dist/dmg-root/Applications"

          hdiutil create \
            -volname "QUILL" \
            -srcfolder "dist/dmg-root" \
            -ov \
            -format UDZO \
            "dist/${DMG_NAME}"

          hdiutil verify "dist/${DMG_NAME}"

      - name: Notarize DMG
        env:
          APPLE_API_KEY_ID: ${{ secrets.APPLE_API_KEY_ID }}
          APPLE_API_ISSUER: ${{ secrets.APPLE_API_ISSUER }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: |
          xcrun notarytool submit "dist/${DMG_NAME}" \
            --key "$RUNNER_TEMP/apple/AuthKey.p8" \
            --key-id "$APPLE_API_KEY_ID" \
            --issuer "$APPLE_API_ISSUER" \
            --team-id "$APPLE_TEAM_ID" \
            --wait \
            --output-format json | tee "$RUNNER_TEMP/notary-result.json"

      - name: Staple notarization ticket to DMG
        run: |
          xcrun stapler staple "dist/${DMG_NAME}"
          xcrun stapler validate "dist/${DMG_NAME}"

      - name: Verify final artifact
        run: |
          spctl --assess --type open --verbose "dist/${DMG_NAME}"
          hdiutil attach "dist/${DMG_NAME}" -nobrowse -readonly -mountpoint "$RUNNER_TEMP/quill-dmg"
          spctl --assess --type execute --verbose "$RUNNER_TEMP/quill-dmg/QUILL.app"
          hdiutil detach "$RUNNER_TEMP/quill-dmg"

      - name: Upload notarization log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: macos-notarization-logs
          path: |
            ${{ runner.temp }}/notary-result.json
          if-no-files-found: ignore

      - name: Upload signed and notarized DMG
        uses: actions/upload-artifact@v4
        with:
          name: QUILL-macOS-signed-notarized
          path: dist/QUILL-macOS.dmg
          if-no-files-found: error
```

---

## 13. Phase 7 — First live run

From Windows PowerShell:

```powershell
cd S:\quill

gh workflow run macos-release.yml --ref main

gh run list --workflow macos-release.yml --limit 5

gh run watch
```

Optional:

```powershell
gh run view --web
```

If using a feature branch first:

```powershell
gh workflow run macos-release.yml --ref feature/agent-harness-buildout
```

First-pass success criteria:

- Workflow finishes green.
- DMG artifact exists in run outputs.
- No signing rejection appears in logs.
- No notary rejection appears in logs.
- Stapler validation passes.
- Gatekeeper assessment passes.

---

## 14. Phase 8 — Clean-device validation

A clean-device test is mandatory before external beta.

Use one of:

- Borrowed Mac.
- Cloud Mac.
- Self-hosted Mac test machine.
- Trusted external tester with a clean macOS account.

Validation steps:

1. Download the DMG from the GitHub Actions artifact or GitHub Release.
2. Open the DMG normally from Finder.
3. Drag `QUILL.app` to Applications.
4. Launch QUILL from Applications.
5. Confirm no manual security bypass is required.
6. Confirm macOS does not report unknown developer.
7. Turn on VoiceOver.
8. Launch QUILL again.
9. Confirm first-run focus lands somewhere sensible.
10. Confirm menus are reachable from keyboard.
11. Confirm a basic document can be opened or created.
12. Confirm quit/relaunch works.

Record:

```text
macOS version:
Apple Silicon or Intel:
VoiceOver tested: yes/no
Install required bypass: yes/no
Launch warning observed: yes/no
Tester:
Date:
Result:
```

Exit criteria:

- User can install and launch without bypass commands.
- VoiceOver smoke check passes.
- Any first-run prompts are understandable and keyboard accessible.

---

## 15. Phase 9 — Beta rollout controls

Before publishing a public or external beta:

- Require the `macos-release` workflow to pass.
- Require environment approval for release jobs.
- Do not manually upload unsigned local builds to public release pages.
- Keep unsigned artifacts clearly marked as internal-only.
- Keep a rollback link to the last known-good signed/notarized DMG.

Recommended release checklist item:

```markdown
- [ ] macOS DMG was produced by the protected `macos-release` workflow.
- [ ] App is signed with Developer ID Application: Jeff Bishop (TEAMID).
- [ ] DMG is notarized.
- [ ] Stapler validation passed.
- [ ] Gatekeeper validation passed.
- [ ] Clean-device install and VoiceOver smoke test completed.
```

---

## 16. Troubleshooting guide

### 16.1 Certificate import failure

Symptoms:

- `security import` fails.
- `security find-identity` does not show Developer ID identity.
- `codesign` says identity not found.

Check:

- `BUILD_CERTIFICATE_BASE64` was created from the `.p12`, not the `.cer`.
- `P12_PASSWORD` exactly matches the export password.
- The `.p12` contains the private key.
- The workflow imported the certificate into the same keychain used by codesign.

Fix:

- Re-export the `.p12` from Keychain Access.
- Re-upload `BUILD_CERTIFICATE_BASE64`.
- Reset `P12_PASSWORD`.

### 16.2 Signing identity mismatch

Symptoms:

- `codesign` cannot find identity.
- Identity appears in keychain but workflow fails.

Check:

```bash
security find-identity -v -p codesigning
```

The secret must exactly match the identity string, for example:

```text
Developer ID Application: Jeff Bishop (TEAMID)
```

Fix:

```powershell
gh secret set -e macos-release MACOS_CODESIGN_IDENTITY
```

Paste the exact value.

### 16.3 Notary authentication failure

Symptoms:

- `notarytool submit` fails quickly.
- Error mentions key, issuer, team, or authorization.

Check:

- `APPLE_API_KEY_ID` matches the `.p8` key.
- `APPLE_API_ISSUER` is the issuer ID from App Store Connect.
- `APPLE_TEAM_ID` is the Apple Developer Team ID.
- `APPLE_API_KEY_B64` was generated from the correct `.p8` file.
- The API key was not revoked.

Fix:

- Recreate the App Store Connect API key.
- Download the new `.p8` immediately.
- Update all API secrets.

### 16.4 Notary rejection

Symptoms:

- Apple accepts credentials but rejects the submitted artifact.

Check:

- Hardened runtime is enabled: `--options runtime`.
- All nested binaries are signed.
- Native libraries, helper binaries, frameworks, and executable resources are signed.
- Entitlements are correct.
- DMG contains the signed app, not a stale unsigned app.

Fix:

- Inspect notarization log.
- Add explicit signing for nested `.dylib`, `.so`, helper executables, frameworks, or plug-ins.
- Rebuild clean and retry.

### 16.5 Stapling failure

Symptoms:

- Notarization passes but `stapler staple` fails.

Check:

- You are stapling the same artifact that was notarized.
- The DMG was not modified after notarization.
- Apple notary result is complete.

Fix:

- Recreate DMG.
- Submit DMG to notarization.
- Staple the unchanged DMG.

### 16.6 Gatekeeper failure after download

Symptoms:

- CI passed but tester sees warning.

Check:

- Tester downloaded the signed/notarized artifact, not an older unsigned one.
- The download host did not repackage the DMG.
- Stapler validation passes on the downloaded file.
- Quarantine behavior is tested from an actual browser download, not only a local file copy.

Fix:

- Re-upload the verified DMG.
- Rename artifacts clearly.
- Remove old unsigned artifacts from public pages.

---

## 17. Risk register

| Risk | Impact | Likelihood without controls | User effect | Mitigation |
|---|---:|---:|---|---|
| Unsigned or non-notarized beta distributed externally | High | Medium | Security warnings, failed installs, trust erosion | Block public beta unless signed/notarized workflow passes. |
| Certificate expiration or revocation | High | Medium | New builds fail trust checks | Calendar renewal reminders, two-owner custody, pre-expiry rotation drill. |
| Secret leakage or mis-scoped access | High | Low to Medium | Signing abuse and incident response | GitHub environments, limited maintainers, mandatory reviews, secret rotation. |
| Notarization service outage or API change | Medium | Low to Medium | Delayed beta | Retry policy, release buffer, preserve logs. |
| No physical Mac for final accessibility smoke testing | Medium | Medium | VoiceOver-specific issues escape | Use borrowed/cloud Mac or trusted tester before public beta. |
| Individual Apple account used for a Community Access project | Low to Medium | High by design | User may ask why macOS says Jeff Bishop | Explain in release notes and download page. |

---

## 18. Credential rotation and recovery

### 18.1 Rotation schedule

| Credential | Rotate when |
|---|---|
| Developer ID certificate | Before expiration, suspected compromise, maintainer transition. |
| `.p12` password | Whenever `.p12` is re-exported or maintainer access changes. |
| App Store Connect API key | Annually, suspected compromise, maintainer transition. |
| GitHub environment secrets | When any underlying credential changes. |
| Keychain password | Anytime; low-risk but should still be refreshed periodically. |

### 18.2 Break-glass recovery

If a signing secret is compromised:

1. Disable the `macos-release` environment temporarily.
2. Revoke the compromised App Store Connect API key if affected.
3. Revoke/recreate Developer ID certificate if the certificate/private key is affected.
4. Create new `.p12` and/or `.p8` credentials.
5. Update GitHub environment secrets.
6. Run a clean test release.
7. Document incident and rotation date.

---

## 19. Operator notes for maintainers

- Do not commit `.p12`, `.p8`, `.key`, `.csr`, or certificate passwords.
- Do not paste secrets into GitHub issue comments, pull requests, logs, or AI chats.
- Do not use Apple ID + app-specific password unless the API-key route is blocked.
- Do not allow release workflows to run with secrets on untrusted pull requests.
- Keep the release workflow under branch protection.
- Treat signing as part of accessibility quality, not just security compliance.
- Keep the first public Mac experience calm, predictable, and boring in the best possible way.

---

## 20. Complete implementation checklist

### Apple setup

- [ ] Apple Developer Program membership confirmed.
- [ ] Account Holder role confirmed.
- [ ] Team ID recorded.
- [ ] Developer ID Application certificate created.
- [ ] `.p12` exported or generated.
- [ ] `.p12` password stored securely.
- [ ] Exact signing identity captured.
- [ ] App Store Connect API access requested if needed.
- [ ] Team API key generated.
- [ ] `.p8` downloaded and stored securely.
- [ ] Key ID recorded.
- [ ] Issuer ID recorded.

### GitHub setup

- [ ] `macos-release` environment created.
- [ ] Environment protection rules configured.
- [ ] Required reviewers assigned.
- [ ] `BUILD_CERTIFICATE_BASE64` set.
- [ ] `P12_PASSWORD` set.
- [ ] `KEYCHAIN_PASSWORD` set.
- [ ] `MACOS_CODESIGN_IDENTITY` set.
- [ ] `APPLE_API_KEY_B64` set.
- [ ] `APPLE_API_KEY_ID` set.
- [ ] `APPLE_API_ISSUER` set.
- [ ] `APPLE_TEAM_ID` set.
- [ ] Secrets verified with `gh secret list -e macos-release`.

### Workflow setup

- [ ] `.github/workflows/macos-release.yml` added.
- [ ] QUILL macOS build command wired into workflow.
- [ ] App signing step enabled.
- [ ] DMG creation step enabled.
- [ ] Notarization step enabled.
- [ ] Stapling step enabled.
- [ ] Gatekeeper verification step enabled.
- [ ] Notary logs uploaded as artifact.
- [ ] Signed/notarized DMG uploaded as artifact.

### Release validation

- [ ] Workflow run completed green.
- [ ] DMG downloaded from workflow artifact.
- [ ] Clean macOS install tested.
- [ ] Launch tested with no security bypass.
- [ ] VoiceOver smoke test completed.
- [ ] Release notes clarify Community Access project / Jeff Bishop signing.
- [ ] Public beta go/no-go approved.

---

## 21. Suggested tester-facing release note

Use this in the first macOS beta release notes:

```markdown
QUILL for macOS is a Community Access project. This beta is signed and notarized by Apple under Jeff Bishop's Apple Developer account, so macOS should allow installation without unidentified-developer bypass steps.

Expected install process:

1. Download `QUILL-macOS.dmg`.
2. Open the DMG.
3. Drag QUILL to Applications.
4. Launch QUILL from Applications.

If macOS reports that the app is from an unidentified developer, please stop and report the exact message. That likely means the wrong artifact was downloaded or the release pipeline failed.
```

---

## 22. Official references

- Apple Developer: Developer ID certificates  
  <https://developer.apple.com/help/account/certificates/create-developer-id-certificates/>

- Apple Developer: Notarizing macOS software before distribution  
  <https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution>

- Apple Developer: App Store Connect API setup  
  <https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api/>

- Apple Developer: App Store Connect role permissions  
  <https://developer.apple.com/help/app-store-connect/reference/account-management/role-permissions/>

- GitHub Docs: GitHub-hosted runners  
  <https://docs.github.com/actions/using-github-hosted-runners/about-github-hosted-runners>

- GitHub Docs: Using secrets in GitHub Actions  
  <https://docs.github.com/actions/security-guides/using-secrets-in-github-actions>

---

## 23. Final recommended path for QUILL

Do this in order:

1. Use Windows to confirm Apple Developer membership and Team ID.
2. Use a borrowed/cloud Mac if available to create the CSR, install the cert, and export `.p12`.
3. If no Mac is available, use the Windows/OpenSSL path to create the CSR and `.p12`, then rely on GitHub Actions macOS for signing.
4. Create an App Store Connect team API key and download the `.p8` immediately.
5. Create the `macos-release` GitHub environment.
6. Add all secrets to that environment.
7. Add the `macos-release.yml` workflow.
8. Run the workflow manually.
9. Fix signing/notarization issues until the run is green.
10. Download the DMG and test on a clean Mac with VoiceOver.
11. Only then publish the external beta.

The goal is a release process that feels almost magical to maintainers and completely ordinary to users: download, open, drag to Applications, launch QUILL, and get to work.
