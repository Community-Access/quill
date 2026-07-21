# Builds the shared QuillVille Runtime onedir that every app reuses.
#
#   dist\QuillVilleRuntime\   the shared runtime (CPython + wxPython + quill +
#                             quill_social), with ffmpeg/mpv staged into tools\
#                             and a quillville-runtime.json version marker.
#
# An app installer installs this once (installer\shared-runtime.iss skips it when
# a matching version is already present) and launches apps through it with
#   QuillVilleRuntime.exe -m <the app's module>.
#
# Usage:
#   .\build_runtime.ps1 [-Python <python.exe>] [-FfmpegDir <dir>] [-LibmpvDir <dir>]

param(
    [string]$Python = "S:\QUILL\.venv\Scripts\python.exe",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$dist = Join-Path $repoRoot "dist\QuillVilleRuntime"

# -- ffmpeg + libmpv to bundle (shared by every app that records/plays) -------
if (-not $FfmpegDir) {
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpeg) { $FfmpegDir = Split-Path -Parent $ffmpeg.Source }
}
if (-not $FfmpegDir -or -not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found. Pass -FfmpegDir."
}
if (-not $LibmpvDir) {
    $packDir = Join-Path $env:APPDATA "Quill\engine-packs\mpv"
    if (Test-Path (Join-Path $packDir "libmpv-2.dll")) { $LibmpvDir = $packDir }
}
if (-not $LibmpvDir -or -not (Test-Path (Join-Path $LibmpvDir "libmpv-2.dll"))) {
    throw "libmpv-2.dll not found. Pass -LibmpvDir."
}

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quillville-runtime.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
if (-not (Test-Path (Join-Path $dist "QuillVilleRuntime.exe"))) {
    throw "Runtime build did not produce QuillVilleRuntime.exe"
}

# -- stage shared binaries into the runtime's tools\ --------------------------
# Apps resolve these via QUILL_APP_ROOT, which (when frozen) is the runtime dir.
$toolsFfmpeg = Join-Path $dist "tools\ffmpeg"
$toolsMpv = Join-Path $dist "tools\mpv"
New-Item -ItemType Directory -Force $toolsFfmpeg, $toolsMpv | Out-Null
Copy-Item (Join-Path $FfmpegDir "ffmpeg.exe") $toolsFfmpeg -Force
if (Test-Path (Join-Path $FfmpegDir "ffprobe.exe")) {
    Copy-Item (Join-Path $FfmpegDir "ffprobe.exe") $toolsFfmpeg -Force
}
Copy-Item (Join-Path $LibmpvDir "libmpv-2.dll") $toolsMpv -Force
Get-ChildItem $LibmpvDir -File -Filter *.txt -ErrorAction SilentlyContinue |
    ForEach-Object { Copy-Item $_.FullName $toolsMpv -Force }

# -- stamp the version marker (installer's skip-if-present check reads this) ---
$pyver = (& $Python -c "import platform; print(platform.python_version())").Trim()
$build = Get-Date -Format "yyyy-MM-dd"
& $Python -c "from pathlib import Path; from quill.core import runtime_marker as m; m.write_marker(Path(r'$dist'), python_version='$pyver', build_id='$build'); print('marker', m.read_marker(Path(r'$dist')))"

Write-Host "Shared runtime ready: $dist (Python $pyver)"
