# Builds every QUILL Audio Studio release artifact from one onedir build:
#
#   dist\QuillAudioStudio\                        the staged app folder
#   dist\Quill-AudioStudio-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\Quill-AudioStudio-Setup-<ver>.exe        system installer
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
    # Reuse an already-built shared runtime at ..\..\runtime\dist\QuillVilleRuntime
    # instead of rebuilding it (a full PyInstaller onedir, ~10 min). The installer
    # still needs it to exist.
    [switch]$SkipSharedRuntime
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "2.2.0"

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (hard requirement for a release build) -----------
# A public release must embed the issues-only token; -SkipToken builds a private
# copy whose Report a Bug falls back to opening GitHub manually (same posture as
# the Quill Radio and Quill Weather builds).
if (-not $SkipToken) {
    if (-not (Test-Path $TokenFile)) {
        throw "Token file not found: $TokenFile -- a release build must embed the issues-only token (or pass -SkipToken for a private build)."
    }
    $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
}

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
if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
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
        & (Join-Path $repoRoot "..\runtime\build_runtime.ps1") -Python $Python -FfmpegDir $FfmpegDir -LibmpvDir $LibmpvDir
        if ($LASTEXITCODE -ne 0) { throw "Shared QuillVille Runtime build failed." }
    } finally {
        Pop-Location
    }
}

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

# The old shipping artifact was QUILL-Audio-Studio-Portable-Lean-<ver>.zip;
# keep that name so it slots straight into the release page.
$zipPath = Join-Path $repoRoot "dist\QUILL-Audio-Studio-Portable-Lean-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer ----------------------------------------------------------------
& $Iscc "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-audio-studio.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
