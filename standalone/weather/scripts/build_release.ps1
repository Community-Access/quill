# Builds every Quill Weather release artifact from one onedir build:
#
#   dist\QuillWeather\                        the staged app folder
#   dist\Quill-Weather-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\Quill-Weather-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-TokenFile S:\token.txt]
#                               [-Iscc <path>] [-SkipToken]
#
# Quill Weather is a small app: no ffmpeg, no mpv, no media/AI stacks -- so,
# unlike Quill Radio's build, there is nothing to stage under tools\. It is
# versioned in lockstep with Quill Radio (2.2.0) but built and released on its
# own. Everything is bundled; the installer and zip perform no downloads.

param(
    [string]$Python = "D:\QUILL\.venv\Scripts\python.exe",
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
if (-not $SkipToken) {
    if (-not (Test-Path $TokenFile)) {
        throw "Token file not found: $TokenFile -- a release build must embed the issues-only token (or pass -SkipToken for a private build)."
    }
    $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
}

if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
}

# -- shared QuillVille Runtime (the onedir the per-app installer ships) -----
# The shared runtime at ..\..\runtime\dist\QuillVilleRuntime\ is what the
# per-app installer (quill-weather.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. Weather is small
# (no ffmpeg, no mpv), so the build_runtime.ps1 invocation is just for
# the runtime itself -- ffmpeg/mpv staging is a no-op for Weather.
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

# -- portable bundle (self-contained, genuine embeddable runtime) -------------
# NOT a PyInstaller onedir and NOT a stamped pythonw.exe. See build_portable.py
# and docs/design/native-launcher-2026-07-24.md: genuine unmodified
# python.exe/pythonw.exe + the native C launcher (QuillWeather.exe) spawning
# `pythonw.exe -m quill.apps.weather`. Weather is small -- no ffmpeg/mpv/engines.
$appDir = Join-Path $repoRoot "dist\QuillWeather"
& $Python (Join-Path $QuillRepo "standalone\studio\scripts\build_portable.py") `
    --product weather `
    --out $appDir `
    --source-root $QuillRepo `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillWeather.exe"))) {
    throw "Portable build did not produce the native QuillWeather.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}

$zipPath = Join-Path $repoRoot "dist\Quill-Weather-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer ----------------------------------------------------------------
& $Iscc "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-weather.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
