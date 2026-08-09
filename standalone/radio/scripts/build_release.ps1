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

# Every path below defaults to "" and is resolved from the checkout itself, so a
# clone builds on any machine. Hardcoded D:\ defaults used to make this script
# runnable on exactly one computer.
param(
    [string]$Python = "",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = "",
    [string]$TokenFile = "",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$QuillRepo = "",
    [switch]$SkipToken,
    [switch]$SkipSharedRuntime,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "2.2.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run by setting QUILL_SIGN=1, which the shared signer
# (QUILL\scripts\code_signing.py) reads. Without it, the sign-build steps below
# are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\radio -> standalone -> the QUILL checkout root.
if (-not $QuillRepo) {
    $QuillRepo = Split-Path -Parent (Split-Path -Parent $repoRoot)
}
if (-not (Test-Path (Join-Path $QuillRepo "quill\__init__.py"))) {
    throw "QUILL checkout not found at '$QuillRepo' -- pass -QuillRepo."
}
# Existing on disk is not the same as runnable: a venv whose base interpreter has
# been moved or uninstalled still has a python.exe that dies with "did not find
# executable at ...". Preferring it blindly wedged the build several steps later
# with a misleading "Bundled feedback token generation failed", so prove the
# interpreter actually runs before committing to it.
function Test-PythonExe([string]$exe) {
    if (-not $exe -or -not (Test-Path $exe)) { return $false }
    try {
        & $exe -c "import sys" 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if (-not $Python) {
    $venvPython = Join-Path $QuillRepo ".venv\Scripts\python.exe"
    if (Test-PythonExe $venvPython) {
        $Python = $venvPython
    } else {
        if (Test-Path $venvPython) {
            Write-Host "Ignoring $venvPython (present but not runnable); falling back to PATH."
        }
        $onPath = Get-Command python -ErrorAction SilentlyContinue
        if (-not $onPath) { throw "No usable Python found -- pass -Python <python.exe>." }
        $Python = $onPath.Source
    }
}
if (-not (Test-PythonExe $Python)) {
    throw "Python at '$Python' is not runnable -- pass a working -Python <python.exe>."
}
Write-Host "Using Python: $Python"

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (Report a Bug for users with no GitHub setup) -----
# A public release must embed the issues-only token; -SkipToken builds a private
# copy whose Report a Bug falls back to opening GitHub manually (same posture as
# the Quill Weather build).
if (-not $SkipToken) {
    # -TokenFile is one of several sources generate_feedback_token.py accepts
    # (env var, token file, Windows Credential Manager, or a token already
    # bundled by this machine's last build). Pass it when given; otherwise let
    # the generator resolve, and let ITS --require-token error explain every
    # option rather than throwing here about the one source we happen to know.
    if ($TokenFile) {
        if (-not (Test-Path $TokenFile)) {
            throw "Token file not found: $TokenFile."
        }
        $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
    }
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
}

# -- ffmpeg to bundle ---------------------------------------------------------
# SECURITY: ffmpeg is copied verbatim into the shipped runtime, so require an
# explicit, vetted staging directory. We do NOT fall back to Get-Command (the
# builder's PATH), which a stale or malicious local install could poison into a
# planted, unverified binary inside the release.
# When no directory is given, stage it from QUILL's own pinned, SHA-256-verified
# assets-v1 release (scripts/fetch_build_deps.py) instead of failing. That keeps
# the security rule intact -- still no PATH auto-discovery, and the bytes are
# checksum-verified against a pin in the source tree, which is a stronger
# guarantee than a directory the builder assembled by hand -- while letting a
# fresh clone build on a machine with no ffmpeg installed at all.
if (-not $FfmpegDir) {
    Write-Host "Staging ffmpeg from QUILL's pinned release assets..."
    & $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only ffmpeg
    if ($LASTEXITCODE -ne 0) { throw "Could not stage ffmpeg (see scripts/fetch_build_deps.py)." }
    $FfmpegDir = Join-Path $QuillRepo "build\deps\ffmpeg"
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
# Same as ffmpeg above: absent an explicit directory, stage the pinned,
# SHA-256-verified libmpv pack rather than failing. Still never the
# user-writable %APPDATA%\Quill\engine-packs\mpv copy.
if (-not $LibmpvDir) {
    Write-Host "Staging libmpv from QUILL's pinned release assets..."
    & $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only libmpv
    if ($LASTEXITCODE -ne 0) { throw "Could not stage libmpv (see scripts/fetch_build_deps.py)." }
    $LibmpvDir = Join-Path $QuillRepo "build\deps\mpv"
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

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the shared runtime and the portable app BEFORE they are
# zipped or embedded in the installer, so the signed binaries are what ships.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "radio payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\Quill-Radio-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer (Inno signs Setup.exe + the uninstaller when signing is on) ----
# When QUILL_SIGN=1, pass /DSign plus the /Squilltrusted sign-command mapping so
# the .iss SignTool/SignedUninstaller directives activate ($q -> ", $f -> file).
# Inno then signs both the compiled Setup.exe and the embedded uninstaller.
# Without it, $innoSign is empty and the build compiles unsigned.
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-radio.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
