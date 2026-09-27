# Builds every Quill Converter release artifact from one portable build:
#
#   dist\QuillConverter\                          the staged app folder
#   dist\Quill-Converter-Portable-<ver>.zip       portable (with its data\ folder)
#   dist\Quill-Converter-Setup-Shared-<ver>.exe   the installer (bundles the runtime)
#
# TWO artifacts, the same two Quill Radio 3.0.0 and QUILL Lite publish
# (2026-09-26), for their reasons (standalone\radio\scripts\build_release.ps1):
# there is no Companion zip, because a zip that installs nothing binds to
# whatever shared runtime is already on the machine -- including one frozen
# before this Converter, which fails at launch and cannot self-heal -- and no
# thin installer, because it trades a smaller download for a first-launch
# download plus a network dependency. Two downloads also make Check for Updates
# a question with one honest answer: portable, or not.
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-FfmpegDir <dir>]
#                               [-Iscc <path>] [-QuillRepo <dir>]
#                               [-SkipSharedRuntime] [-Sign]
#
# Everything is bundled; the installer and zip perform no downloads. No GitHub
# token is generated or embedded and feedback-hub is not bundled: Get Help from
# Support goes by email to support@community-access.org, so there is nothing to
# ship. Converter needs ffmpeg (its whole job) and not libmpv (it plays nothing).

# Every path below defaults to "" and is resolved from the checkout itself, so a
# clone builds on any machine.
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
# The app's own number is _VERSION in quill\apps\converter.py (what About and
# Check for Updates report). This literal is what GATE-VC checks against
# pyproject.toml; the guard below fails the build if the two ever disagree.
$version = "1.0.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run by setting QUILL_SIGN=1, which the shared signer
# (QUILL\scripts\code_signing.py) reads. Without it, the sign-build steps below
# are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\converter -> standalone -> the QUILL checkout root.
if (-not $QuillRepo) {
    $QuillRepo = Split-Path -Parent (Split-Path -Parent $repoRoot)
}
# Interpreter and ISCC (Inno Setup 7 only) resolution is shared by every
# standalone build script in scripts\BuildEnv.ps1.
. (Join-Path $QuillRepo "scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
$Iscc = Resolve-QuillIscc -Preferred $Iscc

# -- the version is the app's -------------------------------------------------
$appSource = Get-Content -Raw (Join-Path $QuillRepo "quill\apps\converter.py")
if ($appSource -notmatch '(?m)^_VERSION\s*=\s*"([^"]+)"') {
    throw "Could not read _VERSION from quill\apps\converter.py."
}
if ($Matches[1] -ne $version) {
    throw "quill\apps\converter.py says $($Matches[1]) but this script builds $version -- bump them together (and pyproject.toml, the .iss fallback, CHANGELOG.md)."
}

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- ffmpeg to bundle ---------------------------------------------------------
# SECURITY: ffmpeg is copied verbatim into the shipped runtime, so require an
# explicit, vetted staging directory. We do NOT fall back to Get-Command (the
# builder's PATH), which a stale or malicious local install could poison into a
# planted, unverified binary inside the release. Absent a directory, stage it
# from QUILL's own pinned, SHA-256-verified assets-v1 release
# (scripts/fetch_build_deps.py) instead.
if (-not $FfmpegDir) {
    Write-Host "Staging ffmpeg from QUILL's pinned release assets..."
    & $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only ffmpeg
    if ($LASTEXITCODE -ne 0) { throw "Could not stage ffmpeg (see scripts/fetch_build_deps.py)." }
    $FfmpegDir = Join-Path $QuillRepo "build\deps\ffmpeg"
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found in -FfmpegDir '$FfmpegDir'."
}

# -- shared QuillVille Runtime (the onedir the per-app installer ships) -------
# The shared runtime at ..\..\runtime\dist\QuillVilleRuntime\ is what the
# per-app installer (quill-converter.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. Converter declares
# ffmpeg (quill.apps.converter.REQUIRED_COMPONENTS = ("ffmpeg",)), so it stages
# ffmpeg into the runtime's tools\ and nothing else.
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
# The runtime dist is a communal work area: Radio's or Studio's build leaves
# libmpv in its tools\. Converter's installer does not pack it (no ToolMpv in
# the .iss), but strip it anyway so nothing here depends on build order.
$stagedMpv = Join-Path $sharedRuntimeDist "tools\mpv"
if (Test-Path $stagedMpv) {
    Remove-Item $stagedMpv -Recurse -Force
    Write-Host "Stripped staged mpv from the runtime payload (Converter declares only ffmpeg)."
}
. (Join-Path $QuillRepo "scripts\StageMediaTools.ps1")
Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir

# -- the runtime must actually contain this app -------------------------------
# The shared runtime carries its OWN frozen copy of the quill package, so one
# reused through -SkipSharedRuntime from before a Converter change can compile,
# install, and then fail at first launch (QUILL Lite shipped that, 2026-09-08).
# This also checks the frozen tree is current against this checkout. Converter
# has no no-window diagnostic switch, so no -ProbeArgs.
Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.converter"

# -- portable bundle (self-contained, genuine embeddable runtime) -------------
# NOT a PyInstaller onedir and NOT a stamped pythonw.exe. See build_portable.py
# and docs/design/native-launcher-2026-07-24.md: genuine unmodified
# python.exe/pythonw.exe + the native C launcher (QuillConverter.exe) spawning
# `pythonw.exe -m quill.apps.converter`, with ffmpeg staged into tools\. It
# carries its own data\ folder, so it writes nothing to the host computer.
$appDir = Join-Path $repoRoot "dist\QuillConverter"
& $Python (Join-Path $QuillRepo "standalone\studio\scripts\build_portable.py") `
    --product converter `
    --out $appDir `
    --source-root $QuillRepo `
    --ffmpeg-dir $FfmpegDir `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillConverter.exe"))) {
    throw "Portable build did not produce the native QuillConverter.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}

# -- portable inventory baseline ---------------------------------------------
# build_portable.py fails the build on drift from standalone\converter\
# portable-inventory.json once that file exists. Converter has never had one,
# and it can only be produced from a real bundle -- so the first build writes
# it here. Review it and commit it; from then on it is a ratchet like Radio's.
$inventory = Join-Path $repoRoot "portable-inventory.json"
if (-not (Test-Path $inventory)) {
    & $Python (Join-Path $QuillRepo "scripts\check_runtime_inventory.py") $appDir `
        --layout portable --manifest $inventory --write
    if ($LASTEXITCODE -ne 0) { throw "Could not write the portable inventory baseline." }
    Write-Host "Wrote the first portable inventory baseline to $inventory -- review and commit it."
}

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the shared runtime and the portable app BEFORE they are
# zipped or embedded in the installer, so the signed binaries are what ships.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "converter payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\Quill-Converter-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer (Inno signs Setup.exe + the uninstaller when signing is on) ----
# When QUILL_SIGN=1, pass /DSign plus the /Squilltrusted sign-command mapping so
# the .iss SignTool/SignedUninstaller directives activate ($q -> ", $f -> file).
# Without it, $innoSign is empty and the build compiles unsigned.
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-converter.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File -Filter "*-$version.*" | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
