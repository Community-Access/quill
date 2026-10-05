# Windows code signing (Authenticode via Azure Trusted Signing)

This is how QUILL and its companion apps get an **Authenticode** signature --
the operating-system code signature Windows checks on an `.exe`/`.dll` and the
one SmartScreen and the UAC prompt read to show a real publisher instead of
"Unknown publisher". It is a **different** thing from
[`docs/signing.md`](signing.md), which is Ed25519 *provenance* signing (minisign
sidecars) for Quillins and other Hub artifacts. Both exist on purpose:

| System | Covers | Mechanism | Doc |
| --- | --- | --- | --- |
| **Authenticode code signing** | shipped `.exe`/`.dll` + the installers | Azure Trusted Signing + `signtool` | this file |
| **Artifact provenance signing** | Quillins, agents, packs (Hub downloads) | Ed25519 `.minisig` sidecars | `docs/signing.md` |
| **Update-feed signing** | the autoupdate feed JSON | a separate Ed25519 keypair | `docs/signing.md` |

## What signs what

There is no PFX or private key on disk. Signing goes through **Azure Trusted
Signing** (formerly Azure Code Signing): `signtool.exe` loads a Microsoft signing
dlib (`Azure.CodeSigning.Dlib.dll`) that submits a file digest to the account's
`wus2.codesigning.azure.net` endpoint and receives a short-lived certificate.
The signed leaf certificate's subject is the identity-validated publisher
(`CN=Jeffrey Bishop`), chained under `Microsoft ID Verified Code Signing PCA
2021`. Every signature is timestamped against
`http://timestamp.acs.microsoft.com`, so it stays valid after the short-lived
signing certificate expires.

The account and certificate profile live in a small `metadata.json` at the repo
root:

```json
{
  "Endpoint": "https://wus2.codesigning.azure.net/",
  "CodeSigningAccountName": "JeffBishopSigningCert",
  "CertificateProfileName": "QUILL"
}
```

## The one tool: `scripts/code_signing.py`

Everything routes through a single, reusable module. It is import-safe (build
scripts call it in-process) and a CLI.

```powershell
python scripts\code_signing.py doctor            # is the toolchain + credential ready?
python scripts\code_signing.py ensure-dlib       # stage the signing dlib (pinned + SHA-256 verified)
python scripts\code_signing.py sign a.exe b.dll  # sign specific files (fails closed)
python scripts\code_signing.py sign-tree dist\portable   # sign every *.exe/*.dll under a tree
python scripts\code_signing.py sign-build dist\App --label app   # opt-in/fail-open (build scripts use this)
python scripts\code_signing.py verify a.exe      # verify the embedded Authenticode signature
python scripts\code_signing.py build-decision --version 3.3.0-beta.1   # does this build sign? (last line: sign or skip)
```

It:

- **Locates `signtool.exe`** from the installed Windows 10/11 SDK
  (`Windows Kits\10\bin\<version>\x64\signtool.exe`), newest SDK first, then PATH.
- **Stages the signing dlib** by downloading the pinned
  `Microsoft.Trusted.Signing.Client` NuGet package, SHA-256-verifying it, and
  extracting `Azure.CodeSigning.Dlib.dll` into `build/deps/trusted-signing/`
  (gitignored, the same cache `fetch_build_deps.py` uses). Pinned + verified
  exactly like every other build dependency.
- **Invokes `signtool` with an argv list** (never a shell). This matters:
  passing `/fd`-style switches through Git Bash / MSYS mangles them into paths
  and yields the misleading `No file digest algorithm specified` error. Always
  drive signing from PowerShell or `subprocess`, never from an MSYS shell.

## Authentication

The dlib authenticates with the ambient Azure credential (`DefaultAzureCredential`):

- **Dev box:** `az login` once. `python scripts\code_signing.py doctor` reports
  whether a credential is visible.
- **CI:** a workload identity / service principal (an `AZURE_*` env credential or
  a federated GitHub OIDC login) that has the **Trusted Signing Certificate
  Profile Signer** role on the account.

## The opt-in / fail-open contract

Signing never changes a plain build. It is controlled by two environment
variables (or the `-Sign` switch on the standalone build scripts, which sets the
first):

| Variable | Effect |
| --- | --- |
| `QUILL_SIGN=1` | Turn signing **on** for this build. Unset (default) -> every sign step is a logged no-op. |
| `QUILL_SIGN_REQUIRED=1` | A signing failure **aborts** the build. Unset -> a failure logs a warning and the build continues (fail-open). Use this in the release pipeline. |
| `QUILL_SIGN_PATTERNS` | Comma/semicolon list of globs a tree-sign covers. Default `*.exe,*.dll`. Widen to `*.exe,*.dll,*.pyd` to also sign CPython extension modules. |
| `QUILL_SIGN_METADATA` | Path to an alternate `metadata.json`. Default: repo-root `metadata.json`. |
| `QUILL_SIGN_VERSION`, `QUILL_SIGN_DEV` | Set by the build itself (`Resolve-QuillSigning`), not by you: the version being built, and whether it is a Dev build. Every later signing call in that build refuses a Beta or Dev version on its own. |

So CI, offline builds, and contributor clones without the certificate build
exactly as before; a release machine sets `QUILL_SIGN=1` (and
`QUILL_SIGN_REQUIRED=1`) and gets signed output -- for a final-numbered build.

## Which builds are signed (decided 2026-10-04)

The owner's decision: **Beta and Dev builds are not code-signed.** Stable always
is. The version being built decides, in one helper every build asks
(`build_decision` in `scripts/code_signing.py`, and
`python scripts\code_signing.py build-decision --version <v>` from PowerShell):

| Version being built | Signed? |
| --- | --- |
| `3.2.0`, `3.2.0+2` (final-numbered: a Stable candidate) | Yes, when `-Sign` / `QUILL_SIGN=1` asks, exactly as before |
| `3.3.0-beta.2`, `1.0.0-rc.1`, `3.3.0-alpha.1` | Never |
| `3.3.1-dev.20261003.1`, or any build made with `-DevVersion` | Never |
| The Beta runtime slot (`build_runtime_installer.ps1 -Channel beta`) | Never |

For a version that is never signed, the build prints one line --
`Beta and Dev builds are not code-signed; signing skipped.` -- and carries on
unsigned. `-Sign`, `QUILL_SIGN=1`, `QUILL_SIGN_REQUIRED=1` and `--require`
cannot change that: the build switches signing off, ISCC gets no `/DSign`, and
the signer itself refuses the version the build declared, so `sign-build`
quietly does nothing and Inno's `sign` command fails the compile rather than
sign.

**Why a final-numbered build on Beta is signed.** Stable takes the same files
that were on Beta (`docs/release-channels-plan.md`, section 4). A Stable
candidate (`3.3.0`) is built once, listed on Beta, and promoted unchanged. It
cannot be signed later: the installer carries its programs compressed inside
`Setup.exe`, so signing them at promotion would mean rebuilding the installer,
which makes new files that were never on Beta, and signing only the outer
`Setup.exe` would ship Stable with unsigned programs inside. So the candidate
is signed when it is built, and the ones that are really Beta -- `-beta.N`,
`-rc.N`, `-alpha.N` -- and every Dev build never are. A final-numbered build is
not a Beta build; it is a release candidate of Stable that waits on Beta.

**What enforces it.**

- `scripts/publish_release.py` refuses to list a final-numbered build whose
  installer or portable programs are not signed ("rebuild it with -Sign"), and
  a Beta or Dev build whose installer is signed. Nothing is created first.
- `scripts/promote_release.py` check **P5** always runs for Stable: every
  installer and every `.exe` in the portable zip must carry an Authenticode
  signature. It reads the signature from the file itself, so it works on the
  Linux promote runner too; where `signtool` is installed it also verifies it.
  A build that fails P5 is rebuilt with `-Sign` as the next build number,
  listed on Beta, and promoted from there.
- `tests/unit/scripts/test_release_code_signing_policy.py` pins the rule per
  version form, the wiring in every `build_release.ps1`, and both checks.

## How it is wired into the builds

Three things are signed for every app: **each shipped binary** (so the launcher
shows a real publisher and no embedded DLL is unsigned), **the installer**, and
**the uninstaller** (so both the SmartScreen download prompt and the later
Add/Remove Programs "unins000.exe" are clean). The split is deliberate:

- **Payload `.exe`/`.dll`** are signed by `code_signing.py` **before** packaging,
  so the signed copies are what land in both the portable ZIP and the installer.
- **The `Setup.exe` and the uninstaller** are signed by **Inno Setup itself**
  during compile, via its native `SignTool` mechanism (`SignTool=quilltrusted`
  + `SignedUninstaller=yes` in the `.iss`). The uninstaller is generated and
  embedded at compile time, so Inno's own signing is the only way to sign it --
  an external post-compile pass over the finished `Setup.exe` cannot reach it.

All seven installers wire this the same way: each `[Setup]` carries an
`#ifdef Sign` block, and the build invokes ISCC with `/DSign` plus a
`/Squilltrusted=<command>` mapping that points Inno at
`python code_signing.py sign $f` (Inno's `$q` -> `"`, `$f` -> the file). Without
`/DSign` the directives are compiled away, so an unsigned build is unchanged.

### Main app (`QUILL for All`)

`scripts/build_windows_distribution.py` signs the assembled `portable/` tree,
then compiles the installer. When `QUILL_SIGN=1`, `compile_inno_setup_installer`
passes `/DSign` + the sign-command mapping so Inno signs
`Quill-for-All-Setup-<ver>.exe` **and its uninstaller** during compile. No new
flags -- it honours `QUILL_SIGN`. The version comes from `build/version.toml`:
`channel = "stable"` is final-numbered and may sign; `beta`, `rc`, `alpha` and
`dev` never do.

`windows-release.yml` has no Azure credential, so a QUILL tag built in CI is
unsigned. That is right for `v1.0.0-rc.1`. For the final `v1.0.0` candidate,
build it on your computer with `QUILL_SIGN=1`, upload the signed installer and
portable zip over the CI ones (`gh release upload v1.0.0 <files> --clobber`),
then list it with `publish_release.py --existing`; the publish check refuses
the unsigned CI files otherwise.

```powershell
$env:QUILL_SIGN = "1"
python scripts\build_windows_distribution.py --bundle-python --compile-installer
```

### Standalone apps (Radio, Weather, Cast, Beacon, Social, Audio Studio)

Each `standalone/<app>/scripts/build_release.ps1` takes a `-Sign` switch. With
it, the script signs the shared runtime (where present) and the portable app
dir before zipping, then passes `/DSign` + the mapping to ISCC so Inno signs the
`Setup.exe` and uninstaller during compile:

```powershell
.\scripts\build_release.ps1 -Sign
```

Without `-Sign`, the payload `sign-build` step prints a "skipped" line and ISCC
is invoked with no sign arguments, so the build is byte-for-byte what it was
before. Each script calls `Resolve-QuillSigning` (in `scripts\BuildEnv.ps1`)
right after it knows its version and build number, before anything is signed;
for a Beta or Dev version that turns `-Sign` off for the whole build, with the
one line above.

## Cost note

Trusted Signing bills per signature, and every file is one remote round-trip, so
signing time scales with file count. The default `*.exe,*.dll` set keeps this to
the launcher, the installer, and the bundled DLLs. Widening
`QUILL_SIGN_PATTERNS` to include `*.pyd` signs every CPython extension module
too (hundreds of files across the embedded runtime + wxPython) -- thorough, but
slower and more expensive. Choose per release.

## Verifying a signature

```powershell
python scripts\code_signing.py verify dist\...\Quill-for-All-Setup-<ver>.exe
# or, authoritatively:
signtool verify /pa /v <file>
```

`signtool verify /pa /v` is the source of truth for the embedded signature. Note
that `Get-AuthenticodeSignature` can report a *catalog* signer (e.g.
`CN=Microsoft Windows`) for a file that is also catalog-signed by the OS; that is
the Windows security-catalog match, independent of the embedded Authenticode
signature `signtool` reports.

## Rotation / account changes

The signing identity is entirely in `metadata.json` plus the Azure account's
certificate profile. To move accounts or profiles, edit `metadata.json` (or point
`QUILL_SIGN_METADATA` at a different file); nothing else in the tree hard-codes
the endpoint, account, or profile. To bump the signing dlib, change
`TRUSTED_SIGNING_CLIENT_VERSION` / `TRUSTED_SIGNING_CLIENT_SHA256` in
`scripts/code_signing.py`.
