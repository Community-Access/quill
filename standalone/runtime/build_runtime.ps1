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
#
# -Python defaults to the newest installable system Python (see
# scripts\BuildEnv.ps1). It used to default to a literal
# "S:\QUILL\.venv\Scripts\python.exe", so a direct invocation worked on exactly
# one machine, on one drive letter.

param(
    [string]$Python = "",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$dist = Join-Path $repoRoot "dist\QuillVilleRuntime"

# standalone\runtime -> standalone -> the QUILL checkout root. Derived from this
# script's own location, so no drive letter is ever assumed.
$quillRepo = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "..\.."))
. (Join-Path $quillRepo "scripts\BuildEnv.ps1")
$quillRepo = Resolve-QuillRepo -Preferred $quillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $quillRepo

# -- the build environment must match the declared runtime manifest -----------
# quillville-runtime.spec builds with collect_all("quill"), so PyInstaller
# bundles whatever is importable in THIS interpreter's environment. A drifted
# virtualenv therefore changes what ships without changing a line of source, and
# the build still exits 0: one such drift shipped a runtime with no offline
# dictation and wxPython below the pin in [ui], and it was only caught by
# unpacking the installer and diffing it against a known-good one. Check the
# venv against pyproject's [runtime] group first -- it costs a second.
$envCheck = Join-Path $quillRepo "scripts\check_build_env.py"
if (Test-Path $envCheck) {
    # runtime = what the shared runtime ships; packaging = the build tools that
    # produce it. Checking only [runtime] let a missing PyInstaller through: the
    # gate passed, then PyInstaller failed seconds later with a bare import error.
    & $Python $envCheck --groups runtime,packaging --python $Python
    if ($LASTEXITCODE -ne 0) {
        throw "Build environment does not match pyproject [runtime, packaging] -- see above."
    }
} else {
    Write-Warning "Build-environment check not found at $envCheck; skipping."
}

# -- ffmpeg + libmpv to bundle (shared by every app that records/plays) -------
# SECURITY: ffmpeg/ffprobe and libmpv-2.dll are copied verbatim into the shipped
# runtime, so they must come from a vetted staging directory passed explicitly.
# We deliberately DO NOT fall back to resolving ffmpeg from the builder's PATH
# (Get-Command) or libmpv from the user-writable %APPDATA%\Quill\engine-packs\mpv:
# either could be poisoned by a stale/local install or a malicious file and would
# then be planted, unverified, into every app's runtime. Pass -FfmpegDir /
# -LibmpvDir pointing at directories you control.
if (-not $FfmpegDir) {
    throw "ffmpeg not staged: pass -FfmpegDir pointing at a vetted directory containing ffmpeg.exe (PATH auto-discovery is refused for release builds)."
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found in -FfmpegDir '$FfmpegDir'."
}
if (-not $LibmpvDir) {
    throw "libmpv not staged: pass -LibmpvDir pointing at a vetted directory containing libmpv-2.dll (%APPDATA% auto-discovery is refused for release builds)."
}
if (-not (Test-Path (Join-Path $LibmpvDir "libmpv-2.dll"))) {
    throw "libmpv-2.dll not found in -LibmpvDir '$LibmpvDir'."
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

# -- prune dead weight PyInstaller can't drop via `excludes` -------------------
# pywin32 ships an IDE (Pythonwin\) and a compiled help file (PyWin32.chm) that
# collect_all bundles as data. Nothing in any QuillVille app opens either at
# runtime, so strip them (~17 MB) after the build. Also drop *.pdb debug symbols
# if any slipped in. Best-effort: absence is a no-op.
$internal = Join-Path $dist "_internal"
foreach ($dead in @("Pythonwin")) {
    $p = Join-Path $internal $dead
    if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "pruned $dead" }
}
Get-ChildItem $internal -Recurse -Include *.chm, *.pdb -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue }
# libx265 is the H.265 VIDEO encoder that ffmpeg's shared build links; these are
# audio/text apps, so ~22 MB of video encoder is dead weight. (Kept as a
# standalone DLL, so PyInstaller `excludes` can't drop it.)
Get-ChildItem $internal -Filter "libx265*.dll" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Force $_.FullName; Write-Host "pruned $($_.Name)" }

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
# A sortable UTC stamp, not a bare date: the installer's skip-if-present check
# compares this string, and two runtimes built on the SAME DAY are different
# payloads (they carry the whole quill package). With date-only ids the second
# build of a day looked identical to the first, so an update installed over it
# was skipped and the app kept running yesterday's code.
$build = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
& $Python -c "from pathlib import Path; from quill.core import runtime_marker as m; m.write_marker(Path(r'$dist'), python_version='$pyver', build_id='$build'); print('marker', m.read_marker(Path(r'$dist')))"

Write-Host "Shared runtime ready: $dist (Python $pyver)"
