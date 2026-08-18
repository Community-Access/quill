# Builds every QUILL Social release artifact from one onedir build:
#
#   dist\QuillSocial\                        the staged app folder
#   dist\QUILL-Social-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\QUILL-Social-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-TokenFile <path>]
#                               [-Iscc <path>] [-QuillRepo <path>]
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
    [string]$TokenFile = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
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
Assert-QuillBuildEnv -Python $Python -QuillRepo $QuillRepo

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (Report a Bug for users with no GitHub setup) -----
# Best-effort for Social: embed the issues-only token when it is available so
# the shared bug reporter works, but do not fail the build without it (unlike a
# QUILL/Radio release, where it is a hard requirement).
$TokenFile = Resolve-QuillTokenFile -Preferred $TokenFile
if ($TokenFile) { $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile }
# A token file is only one of four sources the generator accepts, so run it
# regardless and treat failure as the warning it always was for Social.
& $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
if ($LASTEXITCODE -ne 0) {
    Write-Warning "No feedback token available -- building without the bundled bug-report token."
}

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

# -- shared-runtime flavors: Setup-Shared + Lite + Companion ------------------
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
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-social-shared.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC (Setup-Shared) failed with exit code $LASTEXITCODE" }
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-social-lite.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC (Lite) failed with exit code $LASTEXITCODE" }
# Companion: the runtime-less stick (launcher + icon + docs, ~1 MB).
$companionZip = Join-Path $repoRoot "dist\QUILL-Social-Companion-$version.zip"
if (Test-Path $companionZip) { Remove-Item $companionZip -Force }
Copy-Item (Join-Path $repoRoot "assets\quill-social.ico") $launcherDir -Force
Compress-Archive -Path (Join-Path $launcherDir "*") -DestinationPath $companionZip

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
