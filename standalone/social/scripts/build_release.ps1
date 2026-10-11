# Builds the full QUILL Social installer and portable ZIP from one onedir build:
#
#   dist\QuillSocial\                        the staged app folder
#   dist\QUILL-Social-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\QUILL-Social-Setup-Shared-<ver>.exe system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-Iscc <path>]
#                               [-QuillRepo <path>]
#
# Every path defaults to "" and is resolved from the checkout itself (see
# scripts\BuildEnv.ps1), so a clone builds on any machine and any drive. These
# used to be literal "S:\QUILL..." defaults, which made this script runnable on
# exactly one computer.
#
# Mirrors quill-radio's build_release.ps1, minus the ffmpeg/mpv staging (Social
# is text-and-network; media playback is an optional runtime extra, not bundled).
# Everything else is bundled; the installer and zip perform no downloads.

param(
    [string]$Python = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    [int]$Build = 0,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "0.3.0"

# -- resolve the toolchain ----------------------------------------------------
# standalone\social -> standalone -> the QUILL checkout root.
if (-not $QuillRepo) {
    $QuillRepo = Split-Path -Parent (Split-Path -Parent $repoRoot)
}
. (Join-Path $QuillRepo "scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
$Iscc = Resolve-QuillIscc -Preferred $Iscc

# The build number: -Build, else the next one after the newest tag published
# for $version. It must equal the app's build constant in source, which the
# runtime carries; the installer records it and Windows shows X.Y.Z.B.
$build, $fileVersion = Resolve-QuillReleaseBuild -QuillRepo $QuillRepo -Python $Python -App "social" -Version $version -Build $Build

# Beta and Dev builds are never code-signed (owner decision 2026-10-04). For a
# -dev, -alpha, -beta or -rc version, or a Dev build, this says so in one line
# and switches -Sign off for the whole build, Inno's /DSign included; a
# final-numbered build (a Stable candidate) signs as before. The rule is
# scripts\code_signing.py build-decision; see docs\code-signing.md.
$null = Resolve-QuillSigning -QuillRepo $QuillRepo -Python $Python -Version $version
Assert-QuillBuildEnv -Python $Python -QuillRepo $QuillRepo

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- no feedback token (2026-09-26) ------------------------------------------
# Builds used to generate and embed a bundled GitHub "feedback token" here. No
# QuillVille build does any more: all feedback goes to support@community-access.org
# by email, so there is no credential to ship. -TokenFile and -SkipToken went with
# it. The spec excludes quill._feedback_token and refuses to freeze it or
# feedback_hub (scripts\check_no_credentials.py), so a stale gitignored copy in
# the checkout can no longer ride along.

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quill-social.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
$appDir = Join-Path $repoRoot "dist\QuillSocial"
if (-not (Test-Path (Join-Path $appDir "QuillSocial.exe"))) {
    throw "Onedir build did not produce QuillSocial.exe"
}

# -- stage docs (both artifacts ship these) -----------------------------------
$stagedDocs = Join-Path $appDir "docs"
New-Item -ItemType Directory -Force $stagedDocs | Out-Null
Get-ChildItem (Join-Path $repoRoot "docs") -File |
    Where-Object { $_.Extension -in ".md", ".html" } |
    ForEach-Object { Copy-Item $_.FullName $stagedDocs -Force }
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $appDir "README-QUILL-Social.md") -Force

# -- portable zip (adds the data\ folder = portable-mode switch) --------------
# launcher.py exports QUILLSOCIAL_DATA when a data\ folder sits next to the exe,
# so the whole local store travels on a stick. The installed flavor ships no
# data\ folder and keeps using the platform app-data store.
$dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Set-Content (Join-Path $dataDir "README.txt") @"
This folder makes QUILL Social portable: your accounts, drafts, schedules,
and settings live here, right next to the app, so the whole thing travels on
a stick. Delete this folder and the app uses the shared Quill data in your
Windows profile instead.
"@
# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the app BEFORE it is zipped or embedded in the installer.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $appDir --label "social payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\QUILL-Social-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $appDir -DestinationPath $zipPath
# The installed flavor must NOT carry the data folder (it would flip the
# installed copy into portable mode), so remove it before the installer runs.
Remove-Item $dataDir -Recurse -Force

# -- shared-runtime installer --------------------------------------------------
# Social now consumes the shared QuillVille Runtime like Radio, Weather,
# Studio and Inkwell (2026-08-18): its quill_social package ships inside the
# runtime (the quill-social wheel declared in pyproject [runtime]), so the
# installed app is a native launcher + docs. Setup-Shared supersedes the old
# self-contained Setup -- same AppId, so it upgrades it in place. The onedir
# above remains the Portable zip's payload.
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
$sharedRuntimeDist = Join-Path $repoRoot "..\runtime\dist\QuillVilleRuntime"
if (-not (Test-Path (Join-Path $sharedRuntimeDist "QuillVilleRuntime.exe"))) {
    Push-Location (Join-Path $repoRoot "..\runtime")
    try {
        & (Join-Path $repoRoot "..\runtime\build_runtime.ps1") -Python $Python
        if ($LASTEXITCODE -ne 0) { throw "Shared QuillVille Runtime build failed." }
    } finally { Pop-Location }
}
# Social declares no media components; the runtime dist is a communal work
# area, so strip anything a media app's build left staged there.
foreach ($tool in @("ffmpeg", "mpv")) {
    $staged = Join-Path $sharedRuntimeDist "tools\$tool"
    if (Test-Path $staged) {
        Remove-Item $staged -Recurse -Force
        Write-Host "Stripped staged $tool from the runtime payload (Social declares no media tools)."
    }
}
$launcherDir = Join-Path $repoRoot "dist\QuillSocial-shared"
& $Python (Join-Path $QuillRepo "scripts\build_native_launcher.py") --product social --out $launcherDir
if ($LASTEXITCODE -ne 0) { throw "Native launcher build failed." }
New-Item -ItemType Directory -Force (Join-Path $launcherDir "docs") | Out-Null
Copy-Item (Join-Path $appDir "docs\*") (Join-Path $launcherDir "docs") -Recurse -Force
& $Python $signer sign-build $sharedRuntimeDist $launcherDir --label "social shared payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (shared payload) failed." }
& $Iscc @innoSign "/dAppVersion=$version" "/dAppBuild=$build" "/dAppFileVersion=$fileVersion" (Join-Path $repoRoot "installer\quill-social-shared.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC (Setup-Shared) failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
