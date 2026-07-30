# Builds every Quill Radio release artifact from one onedir build:
#
#   dist\QuillRadio\                        the staged app folder
#   dist\Quill-Radio-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\Quill-Radio-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-FfmpegDir <dir>]
#                               [-TokenFile S:\token.txt] [-Iscc <path>]
#
# Everything is bundled; the installer and zip perform no downloads. The
# bundled feedback token (Report a Bug for users with no GitHub setup) is
# generated into the quill package before PyInstaller runs -- a release
# build FAILS if the token file is missing rather than shipping a build
# with a silently broken bug reporter.

param(
    [string]$Python = "D:\QUILL\.venv\Scripts\python.exe",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = "",
    [string]$TokenFile = "D:\token.txt",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$QuillRepo = "D:\QUILL",
    [switch]$SkipToken,
    [switch]$SkipSharedRuntime
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "2.2.0"

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (Report a Bug for users with no GitHub setup) -----
# A public release must embed the issues-only token; -SkipToken builds a private
# copy whose Report a Bug falls back to opening GitHub manually (same posture as
# the Quill Weather build).
if (-not $SkipToken) {
    if (-not (Test-Path $TokenFile)) {
        throw "Token file not found: $TokenFile -- a release build must embed the issues-only token (or pass -SkipToken for a private build)."
    }
    $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
}

# -- ffmpeg to bundle ---------------------------------------------------------
# SECURITY: ffmpeg is copied verbatim into the shipped runtime, so require an
# explicit, vetted staging directory. We do NOT fall back to Get-Command (the
# builder's PATH), which a stale or malicious local install could poison into a
# planted, unverified binary inside the release.
if (-not $FfmpegDir) {
    throw "ffmpeg not staged: pass -FfmpegDir pointing at a vetted directory containing ffmpeg.exe; recording must ship bundled (PATH auto-discovery is refused for release builds)."
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found in -FfmpegDir '$FfmpegDir'."
}

# -- libmpv to bundle ----------------------------------------------------------
# The mpv playback engine (1.1.0): output-device routing, pause/rewind live
# radio, Volume Boost, native Sound Enhancements, Ogg/Opus/HLS stations.
# Bundled under tools\mpv exactly like ffmpeg under tools\ffmpeg (found via
# QUILL_APP_ROOT, the same pattern QUILL's Offline Edition uses); a release
# without it silently guts the 1.1.0 headline features, so it is required.
# SECURITY: libmpv is bundled verbatim, so require an explicit, vetted
# -LibmpvDir. We do NOT fall back to the user-writable
# %APPDATA%\Quill\engine-packs\mpv, which any process running as the user (or a
# malicious download) could overwrite -- that DLL would then be planted,
# unverified, into every shipped copy.
if (-not $LibmpvDir) {
    throw "libmpv not staged: pass -LibmpvDir pointing at a vetted directory containing libmpv-2.dll; the mpv engine must ship bundled (%APPDATA% auto-discovery is refused for release builds)."
}
if (-not (Test-Path (Join-Path $LibmpvDir "libmpv-2.dll"))) {
    throw "libmpv-2.dll not found in -LibmpvDir '$LibmpvDir'."
}
if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
}

# -- shared QuillVille Runtime (the onedir the per-app installer ships) -----
# The shared runtime at ..\..\runtime\dist\QuillVilleRuntime\ is what the
# per-app installer (quill-radio.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. ffmpeg/mpv go
# here, not into the per-app $appDir\tools\, so the per-app install
# stays tiny -- the C launcher + docs only. The portable zip below
# still gets its own ffmpeg/mpv copy at $appDir\tools\ so the stick
# is self-contained.
$sharedRuntimeDist = Join-Path $repoRoot "..\runtime\dist\QuillVilleRuntime"
if ($SkipSharedRuntime -and (Test-Path (Join-Path $sharedRuntimeDist "QuillVilleRuntime.exe"))) {
    Write-Host "Reusing existing shared runtime at $sharedRuntimeDist (--SkipSharedRuntime)."
} else {
    Push-Location (Join-Path $repoRoot "..\runtime")
    try {
        & (Join-Path $repoRoot "..\runtime\build_runtime.ps1") -Python $Python -FfmpegDir $FfmpegDir -LibmpvDir $LibmpvDir
        if ($LASTEXITCODE -ne 0) { throw "Shared QuillVille Runtime build failed." }
    } finally {
        Pop-Location
    }
}

# -- portable bundle (self-contained, genuine embeddable runtime) -------------
# NOT a PyInstaller onedir and NOT a stamped pythonw.exe. See build_portable.py
# and docs/design/native-launcher-2026-07-24.md: genuine unmodified
# python.exe/pythonw.exe + the native C launcher (QuillRadio.exe) spawning
# `pythonw.exe -m quill.apps.radio`, with ffmpeg/mpv staged into tools\.
$appDir = Join-Path $repoRoot "dist\QuillRadio"
& $Python (Join-Path $QuillRepo "standalone\studio\scripts\build_portable.py") `
    --product radio `
    --out $appDir `
    --source-root $QuillRepo `
    --ffmpeg-dir $FfmpegDir `
    --mpv-dir $LibmpvDir `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillRadio.exe"))) {
    throw "Portable build did not produce the native QuillRadio.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}

$zipPath = Join-Path $repoRoot "dist\Quill-Radio-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer ----------------------------------------------------------------
& $Iscc "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-radio.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
