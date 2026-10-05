# Builds every QUILL Audio Studio release artifact from one onedir build:
#
#   dist\QuillAudioStudio\                        the staged app folder
#   dist\Quill-AudioStudio-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\Quill-AudioStudio-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-FfmpegDir <dir>]
#                               [-Iscc <path>]
#
# Every path defaults to "" and is resolved from the checkout itself (see
# scripts\BuildEnv.ps1), so a clone builds on any machine and any drive. These
# used to be literal "D:\QUILL..." defaults, which made this script runnable on
# exactly one computer.
#
# Everything is bundled; the installer and zip perform no downloads. No GitHub
# token is generated or embedded (2026-09-26): all feedback goes by email to
# support@community-access.org, so there is nothing to bundle.

param(
    [string]$Python = "",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    # Reuse an already-built shared runtime at ..\..\runtime\dist\QuillVilleRuntime
    # instead of rebuilding it (a full PyInstaller onedir, ~10 min). The installer
    # still needs it to exist.
    [switch]$SkipSharedRuntime,
    # Build the Offline Edition installer as well: stages the pinned, verified
    # whisper.cpp engine + starter model into the runtime payload (fetched from
    # the same vault the in-app download uses), compiles a second Setup.exe
    # named -Offline-, then ALWAYS unstages -- a later app build packs the same
    # runtime dist and must not inherit hundreds of MB of speech models.
    [switch]$Offline,
    [int]$Build = 0,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "2.2.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\studio -> standalone -> the QUILL checkout root.
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
$build, $fileVersion = Resolve-QuillReleaseBuild -QuillRepo $QuillRepo -Python $Python -App "studio" -Version $version -Build $Build
Assert-QuillBuildEnv -Python $Python -QuillRepo $QuillRepo

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
if (-not $FfmpegDir) {
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpeg) { $FfmpegDir = Split-Path -Parent $ffmpeg.Source }
}
if (-not $FfmpegDir -or -not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found. Pass -FfmpegDir; recording must ship bundled."
}

# -- libmpv to bundle ----------------------------------------------------------
# The mpv playback engine: gapless audio playback with exact seeking and
# output-device routing in the Audio Studio editor and player.
# Bundled under tools\mpv exactly like ffmpeg under tools\ffmpeg (found via
# QUILL_APP_ROOT, the same pattern QUILL's Offline Edition uses); a release
# without it silently guts the 1.1.0 headline features, so it is required.
if (-not $LibmpvDir) {
    $packDir = Join-Path $env:APPDATA "Quill\engine-packs\mpv"
    if (Test-Path (Join-Path $packDir "libmpv-2.dll")) { $LibmpvDir = $packDir }
}
if (-not $LibmpvDir -or -not (Test-Path (Join-Path $LibmpvDir "libmpv-2.dll"))) {
    throw "libmpv-2.dll not found. Pass -LibmpvDir; the mpv engine must ship bundled."
}

# -- shared QuillVille Runtime (the onedir the per-app installer ships) -----
# The shared runtime at ..\..\runtime\dist\QuillVilleRuntime\ is what the
# per-app installer (quill-audio-studio.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. Audio Studio uses
# both ffmpeg (recording) and the mpv engine (player preview) -- both go
# into the shared runtime's tools\, not the per-app $appDir\tools\, so the
# per-app install stays tiny. The portable zip below still gets its own
# ffmpeg/mpv copy at $appDir\tools\ so the stick is self-contained.
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
# The runtime build no longer stages ffmpeg/mpv -- the app that needs them
# contributes them, which is what keeps 304 MB out of Weather, Inkwell, Beacon
# and Social. Studio stages both: ffmpeg for recording (which is all its
# REQUIRED_COMPONENTS declares) and libmpv for the player preview, which this
# build has always shipped. Studio's own installer payload is unchanged.
. (Join-Path $QuillRepo "scripts\StageMediaTools.ps1")
Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir -LibmpvDir $LibmpvDir

# -- portable bundle (self-contained "Lean" edition) --------------------------
# The portable is NOT a PyInstaller onedir and NOT a stamped pythonw.exe. It is
# a genuine CPython embeddable runtime (unmodified python.exe / pythonw.exe)
# with the native C launcher (QuillAudioStudio.exe) spawning
# `pythonw.exe -m quill.apps.studio`, plus the offline speech/TTS engines
# staged into data\ and ffmpeg/mpv into tools\. See build_portable.py and
# docs/design/native-launcher-2026-07-24.md for why the stamped-pythonw shape
# (the AV-flagged pattern) is gone. build_portable.py hard-fails if the native
# launcher cannot be compiled -- it must never fall back to a stamped pythonw.
$appDir = Join-Path $repoRoot "dist\QuillAudioStudio"
& $Python (Join-Path $PSScriptRoot "build_portable.py") `
    --product studio `
    --out $appDir `
    --source-root $QuillRepo `
    --ffmpeg-dir $FfmpegDir `
    --mpv-dir $LibmpvDir `
    --engines-dir (Join-Path $env:APPDATA "Quill") `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillAudioStudio.exe"))) {
    throw "Portable build did not produce the native QuillAudioStudio.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the shared runtime and the portable app BEFORE they are
# zipped or embedded in the installer. Opt-in via -Sign / QUILL_SIGN; else no-op.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "studio payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

# The old shipping artifact was QUILL-Audio-Studio-Portable-Lean-<ver>.zip;
# keep that name so it slots straight into the release page.
$zipPath = Join-Path $repoRoot "dist\QUILL-Audio-Studio-Portable-Lean-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer ----------------------------------------------------------------
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" "/dAppBuild=$build" "/dAppFileVersion=$fileVersion" (Join-Path $repoRoot "installer\quill-audio-studio.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

# -- Offline Edition installer (optional second flavor) -----------------------
if ($Offline) {
    $stager = Join-Path $QuillRepo "scripts\stage_offline_speech.py"
    & $Python $stager --root $sharedRuntimeDist
    if ($LASTEXITCODE -ne 0) { throw "Offline speech staging failed." }
    try {
        & $Iscc @innoSign "/DOffline" "/dAppVersion=$version" "/dAppBuild=$build" "/dAppFileVersion=$fileVersion" (Join-Path $repoRoot "installer\quill-audio-studio.iss") "/O$(Join-Path $repoRoot 'dist')"
        if ($LASTEXITCODE -ne 0) { throw "ISCC (Offline Edition) failed with exit code $LASTEXITCODE" }
    } finally {
        # Unstage unconditionally: the shared runtime dist is packed by every
        # other app's build, and none of them may inherit the speech stack.
        & $Python $stager --root $sharedRuntimeDist --remove
    }
}

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
