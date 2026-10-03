# Builds every QUILL Cast release artifact from one onedir build:
#
#   dist\QUILLCast\                       the staged app folder
#   dist\QUILL-Cast-Portable-<ver>.zip    portable (with its data\ folder)
#   dist\QUILL-Cast-Setup-<ver>.exe       system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-FfmpegDir <dir>]
#                               [-Iscc <path>]
#
# Every path defaults to "" and is resolved from the checkout itself (see
# scripts\BuildEnv.ps1), so a clone builds on any machine and any drive. These
# used to be literal "S:\QUILL..." defaults, which made this script runnable on
# exactly one computer.
#
# Everything is bundled; the installer and zip perform no downloads. No GitHub
# token is generated or embedded (2026-09-26): all feedback goes by email to
# support@community-access.org, so there is nothing to bundle.

param(
    [string]$Python = "",
    [string]$FfmpegDir = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    [switch]$SkipSharedRuntime,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "2.0.0"

# -- resolve the toolchain ----------------------------------------------------
# standalone\cast -> standalone -> the QUILL checkout root.
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

# -- no feedback token (2026-09-26) ------------------------------------------
# Builds used to generate and embed a bundled GitHub "feedback token" here. No
# QuillVille build does any more: all feedback goes to support@community-access.org
# by email, so there is no credential to ship. -TokenFile and -SkipToken went with
# it. The spec excludes quill._feedback_token and refuses to freeze it or
# feedback_hub (scripts\check_no_credentials.py), so a stale gitignored copy in
# the checkout can no longer ride along.

# -- ffmpeg to bundle ---------------------------------------------------------
# SECURITY: ffmpeg is copied verbatim into shipped artifacts, so it must come
# from a vetted directory. No PATH auto-discovery (the old Get-Command fallback
# here was exactly what Radio's build refuses on purpose -- a stale or planted
# local install would ship unverified). Absent an explicit -FfmpegDir, stage
# the pinned, SHA-256-verified asset the same way Radio and Studio do.
if (-not $FfmpegDir) {
    Write-Host "Staging ffmpeg from QUILL's pinned release assets..."
    & $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only ffmpeg
    if ($LASTEXITCODE -ne 0) { throw "Could not stage ffmpeg (see scripts/fetch_build_deps.py)." }
    $FfmpegDir = Join-Path $QuillRepo "build\deps\ffmpeg"
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found in -FfmpegDir '$FfmpegDir'; audio trim/normalize must ship bundled."
}

# -- shared QuillVille Runtime ------------------------------------------------
# Cast used to be the one app whose build never built the shared runtime -- it
# inherited whatever another app's build had left in ..\..\runtime\dist, the
# same undocumented ordering trap Weather's build retired. Build it here unless
# the caller explicitly reuses one, then stage exactly what Cast declares
# (REQUIRED_COMPONENTS = ("ffmpeg",) -- no libmpv; playback is wx.media).
. (Join-Path $QuillRepo "scripts\StageMediaTools.ps1")
$sharedRuntimeDist = Join-Path $repoRoot "..\runtime\dist\QuillVilleRuntime"
if ($SkipSharedRuntime -and (Test-Path (Join-Path $sharedRuntimeDist "QuillVilleRuntime.exe"))) {
    Write-Host "Reusing existing shared runtime at $sharedRuntimeDist (--SkipSharedRuntime)."
} else {
    Push-Location (Join-Path $repoRoot "..\runtime")
    try {
        & (Join-Path $repoRoot "..\runtime\build_runtime.ps1") -Python $Python
        if ($LASTEXITCODE -ne 0) { throw "Shared QuillVille Runtime build failed." }
    } finally {
        Pop-Location
    }
}
Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir
# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quill-cast.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
$appDir = Join-Path $repoRoot "dist\QUILLCast"
if (-not (Test-Path (Join-Path $appDir "QUILLCast.exe"))) {
    throw "Onedir build did not produce QUILLCast.exe"
}

# -- stage the shared payload (both artifacts ship this) ----------------------
$toolsDir = Join-Path $appDir "tools\ffmpeg"
New-Item -ItemType Directory -Force $toolsDir | Out-Null
Copy-Item (Join-Path $FfmpegDir "ffmpeg.exe") $toolsDir -Force
if (Test-Path (Join-Path $FfmpegDir "ffprobe.exe")) {
    Copy-Item (Join-Path $FfmpegDir "ffprobe.exe") $toolsDir -Force
}
$ffLicense = Join-Path (Split-Path -Parent $FfmpegDir) "LICENSE"
if (Test-Path $ffLicense) { Copy-Item $ffLicense (Join-Path $toolsDir "FFMPEG-LICENSE.txt") -Force }

# -- the chapter engine's model ----------------------------------------------
# Cast infers chapters from a transcript, and most podcasts publish none -- so
# without a local engine the honest answer is always "no chapters could be
# found". The model is 40 MB and Apache-2.0, which is exactly why it was chosen
# over models thirty-five times its size: small enough to ship, so the feature
# answers the first time somebody asks rather than opening with a download.
# Verified against the MD5 the publisher pins (scripts/stage_vosk_model.py).
Write-Host "Staging the Vosk chapter model..."
& $Python (Join-Path $QuillRepo "scripts\stage_vosk_model.py") $appDir
if ($LASTEXITCODE -ne 0) { throw "Could not stage the Vosk chapter model." }
$docsDir = Join-Path $appDir "docs"
New-Item -ItemType Directory -Force $docsDir | Out-Null
# .md + .html for every doc (Help > User Guide / Release Notes / Product
# Requirements... prefers the pre-rendered .html; .md is the fallback source
# if a build ever ships without render_docs.ps1 having run).
Copy-Item (Join-Path $repoRoot "docs\userguide.md") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\userguide.html") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\release-notes-2.0.md") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\release-notes-2.0.html") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\prd.md") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\prd.html") $docsDir -Force
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $appDir "README-QUILL-Cast.md") -Force

# -- portable zip (adds the data\ folder = portable-mode evidence) ------------
$dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Set-Content (Join-Path $dataDir "README.txt") @"
This folder makes QUILL Cast portable: your subscriptions, downloads,
queue, notes, and settings live here, right next to the app, so the
whole thing travels on a stick. Delete this folder and the app uses
the shared Quill data in your Windows profile instead.
"@
# The storage-mode marker is what actually routes data here (the folder
# alone is only the portable-bundle evidence); QUILL portable ships the
# same marker.
Set-Content (Join-Path $dataDir "storage-mode.json") '{"mode": "portable"}'

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the app BEFORE it is zipped or embedded in the installer.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "cast payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\QUILL-Cast-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $appDir -DestinationPath $zipPath
# The installed flavor must NOT carry the data folder (it would flip the
# installed copy into portable mode), so remove it before the installer runs.
Remove-Item $dataDir -Recurse -Force

# -- shared-runtime flavors: Setup-Shared + Lite + Companion ------------------
# Cast now consumes the shared QuillVille Runtime like Radio, Weather, Studio
# and Inkwell (2026-08-18). Setup-Shared supersedes the old self-contained
# Setup -- same AppId, so it upgrades it in place. The onedir above remains
# the Portable zip's payload.
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
# Cast declares ffmpeg only (already staged above). The runtime dist is a
# communal work area, so strip any libmpv another app's build left there --
# 110 MB Cast never calls (playback is wx.media).
$stagedMpv = Join-Path $sharedRuntimeDist "tools\mpv"
if (Test-Path $stagedMpv) {
    Remove-Item $stagedMpv -Recurse -Force
    Write-Host "Stripped staged mpv from the runtime payload (Cast declares ffmpeg only)."
}
$launcherDir = Join-Path $repoRoot "dist\QuillCast-shared"
& $Python (Join-Path $QuillRepo "scripts\build_native_launcher.py") --product cast --out $launcherDir
if ($LASTEXITCODE -ne 0) { throw "Native launcher build failed." }
New-Item -ItemType Directory -Force (Join-Path $launcherDir "docs") | Out-Null
Copy-Item (Join-Path $appDir "docs\*") (Join-Path $launcherDir "docs") -Recurse -Force
& $Python $signer sign-build $sharedRuntimeDist $launcherDir --label "cast shared payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (shared payload) failed." }
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-cast-shared.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC (Setup-Shared) failed with exit code $LASTEXITCODE" }
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-cast-lite.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC (Lite) failed with exit code $LASTEXITCODE" }
# Companion: the runtime-less stick (launcher + icon + docs, ~1 MB).
$companionZip = Join-Path $repoRoot "dist\QUILL-Cast-Companion-$version.zip"
if (Test-Path $companionZip) { Remove-Item $companionZip -Force }
Copy-Item (Join-Path $repoRoot "assets\quill-cast.ico") $launcherDir -Force
Compress-Archive -Path (Join-Path $launcherDir "*") -DestinationPath $companionZip

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
