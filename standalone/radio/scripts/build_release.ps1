# Builds every Quill Radio release artifact from one onedir build:
#
#   dist\QuillRadio\                          the staged app folder
#   dist\Quill-Radio-Portable-<ver>.zip       portable (with its data\ folder)
#   dist\Quill-Radio-Setup-Shared-<ver>.exe   the installer (bundles the runtime)
#
# TWO artifacts, not four (3.0.0, 2026-09-26), for the reasons QUILL Lite
# retired the same two on 2026-09-15 (standalone\quilllite\scripts\
# build_release.ps1). The Companion zip installs nothing, so it binds to
# whatever shared runtime is already on the machine -- including one frozen
# before the Radio it is launching, which fails at launch and cannot self-heal
# because the bootstrap only fires when NO runtime resolves. The thin "Lite"
# installer traded a smaller download for a first-launch download of the
# runtime plus a network dependency, which is the wrong trade for a radio a
# listener wants playing the moment the installer closes. Two downloads also
# make Check for Updates a question with one honest answer -- portable, or not
# -- instead of a four-way guess (quill.apps.radio passes match_edition=False).
#
# Retiring them is safe for anyone already on one: both installers share an
# AppId, so the full installer upgrades a thin install in place, and the
# updater falls through to an installable asset when a release publishes none
# for the running edition (core/updates.py::_app_asset_url).
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-FfmpegDir <dir>]
#                               [-LibmpvDir <dir>] [-Iscc <path>]
#                               [-SkipSharedRuntime] [-SkipCatalog] [-Sign]
#
# Everything is bundled; the installer and zip perform no downloads. No GitHub
# token is generated or embedded (2026-09-26): all feedback goes by email to
# support@community-access.org, so there is nothing to bundle.

# Every path below defaults to "" and is resolved from the checkout itself, so a
# clone builds on any machine. Hardcoded D:\ defaults used to make this script
# runnable on exactly one computer.
param(
    [string]$Python = "",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    [switch]$SkipSharedRuntime,
    [switch]$SkipCatalog,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "3.0.5"

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
# The interpreter/ISCC/token resolution this script used to carry privately now
# lives in scripts\BuildEnv.ps1, shared by every standalone build script so the
# seven copies stop drifting apart.
. (Join-Path $QuillRepo "scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
$Iscc = Resolve-QuillIscc -Preferred $Iscc

# -- station catalog seed (the whole directory, shipped) ----------------------
# Builds quill\data\radio-catalog\seed.db.xz from the live directories with a
# hard 10 MB size gate, so first launch browses 60k+ stations offline. A
# release MUST ship a same-day seed; -SkipCatalog is for dev builds only.
if (-not $SkipCatalog) {
    & $Python (Join-Path $QuillRepo "scripts\build_radio_catalog.py")
    if ($LASTEXITCODE -ne 0) { throw "Station catalog seed build failed (or over budget)." }
} elseif (-not (Test-Path (Join-Path $QuillRepo "quill\data\radio-catalog\seed.db.xz"))) {
    Write-Host "No catalog seed present (-SkipCatalog): the build will browse live until its first refresh."
}

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- refresh the published site's copies of these docs ------------------------
# docs/site/docs/radio-*.html are mirrors of the renders above; unsynced they
# rot (the 2026-08-17 sweep found the site serving pre-3.0 docs). Mechanical
# now, so a release cannot ship current docs and publish stale ones.
& $Python (Join-Path $QuillRepo "scripts\sync_site_radio_docs.py")
if ($LASTEXITCODE -ne 0) { throw "Site radio-docs sync failed (see above)." }

# -- no feedback token (2026-09-26) ------------------------------------------
# This build used to generate and embed the bundled GitHub "feedback token", and
# a public release FAILED without one. It no longer does either: every piece of
# feedback from Quill Radio -- Get Help from Support, Report Bad Station and
# Suggest a Station or Podcast -- goes to support@community-access.org
# through the reader's own mail program, and nothing is filed as a GitHub
# issue, so there is no credential to ship.
# -TokenFile and -SkipToken were removed with it; nothing else here used them.
# One caveat: collect_all("quill") still sweeps up a quill\_feedback_token.py
# that another app's build left in this checkout (it is gitignored, and those
# builds regenerate it). Nothing this app runs reads it any more.

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

# -- deno to bundle -------------------------------------------------------------
# yt-dlp needs a JavaScript runtime to solve YouTube's signature and "n"
# challenges. deno ships in the shared runtime's tools\deno and the portable's,
# pinned and SHA-256-verified by fetch_build_deps.py -- never from PATH, and
# never downloaded at run time (owner's rule, 2026-09-27: nothing on first use).
Write-Host "Staging deno from its pinned release..."
& $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only deno
if ($LASTEXITCODE -ne 0) { throw "Could not stage deno (see scripts/fetch_build_deps.py)." }
$DenoDir = Join-Path $QuillRepo "build\deps\deno"
# -- shared QuillVille Runtime (the onedir the per-app installer ships) -----
# The shared runtime at ..\..\runtime\dist\QuillVilleRuntime\ is what the
# per-app installer (quill-radio.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. ffmpeg/mpv go
# here, not into the per-app $appDir\tools\, so the per-app install
# stays tiny -- the C launcher + docs only. The portable zip below
# still gets its own ffmpeg/mpv copy at $appDir\tools\ so the stick
# is self-contained.
#
# The runtime build itself no longer stages ffmpeg/mpv: Radio declares them
# (quill.apps.radio.REQUIRED_COMPONENTS = ("ffmpeg", "mpv")) and so Radio
# contributes them, which is what keeps the same 304 MB out of Weather,
# Inkwell, Beacon and Social. Radio's installer payload is unchanged, so it
# still plays the instant it finishes installing with no internet.
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
. (Join-Path $QuillRepo "scripts\StageMediaTools.ps1")
Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir -LibmpvDir $LibmpvDir -DenoDir $DenoDir

# -- the runtime must actually contain this app -------------------------------
# The shared runtime carries its OWN frozen copy of the quill package, so a
# runtime reused through -SkipSharedRuntime from before a Radio change can
# compile, install, and then fail at first launch. QUILL Lite shipped exactly
# that once (2026-09-08); one import is the cheapest check that catches it.
# Radio has no no-window diagnostic switch, so no -ProbeArgs: the file check
# and the frozen-tree freshness check are what answer this question anyway.
Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.radio"

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
    --deno-dir $DenoDir `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillRadio.exe"))) {
    throw "Portable build did not produce the native QuillRadio.exe launcher."
}
# The installer ships its own launcher (with the runtime self-heal URL); the
# portable's has none, so a damaged portable never offers a download.
$installerLauncherDir = Join-Path $repoRoot "dist\QuillRadio-installer"
if (-not (Test-Path (Join-Path $installerLauncherDir "QuillRadio.exe"))) {
    throw "Portable build did not produce the installer's QuillRadio.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}

# -- OptiLab Core adapter (required) -----------------------------------------
# quill-optilab.exe links OptiLab Core (Lanes Audio / dgl1984), vendored at
# v1.4.0 under quill/native/optilab/upstream and licensed Apache-2.0 WITH the
# Commons Clause. It is what "exact OptiLab processing" runs. A RELEASE build
# must carry it (owner's rule, 2026-09-27: every component ships in both
# downloads), so a missing C++ toolchain or a failed compile stops the build
# here instead of quietly shipping without it. Its LICENSE and NOTICE ship
# beside it: the engine is redistributed here, not merely imitated.
& $Python (Join-Path $QuillRepo "scripts\build_native_optilab.py") --out $appDir --require
if ($LASTEXITCODE -ne 0) { throw "The OptiLab Core adapter build failed (scripts\build_native_optilab.py)." }
$optilabExe = Join-Path $appDir "quill-optilab.exe"
if (-not (Test-Path $optilabExe)) {
    throw "No quill-optilab.exe was built. Install the MSVC C++ build tools and CMake; a release must ship exact OptiLab processing."
}
$upstream = Join-Path $QuillRepo "quill\native\optilab\upstream"
foreach ($dest in @($appDir, $sharedRuntimeDist)) {
    # Both homes: the portable stick carries its own copy, and the shared
    # runtime is where an *installed* app finds it (the per-app installer
    # ships only the launcher and docs, so the runtime is beside
    # sys.executable -- exactly where optilab_adapter.find_adapter looks).
    $optilabTarget = Join-Path $dest "quill-optilab.exe"
    # ...but `--out $appDir` above already wrote it into the first of those,
    # so that copy is the file onto itself -- which PowerShell treats as a
    # hard error, not a no-op. With $ErrorActionPreference = "Stop" that
    # took the whole release build down at the last step before signing, on
    # any machine with a C++ toolchain to build the adapter in the first
    # place.
    if ([IO.Path]::GetFullPath($optilabTarget) -ne [IO.Path]::GetFullPath($optilabExe)) {
        Copy-Item $optilabExe $optilabTarget -Force
    }
    Copy-Item (Join-Path $upstream "LICENSE") (Join-Path $dest "OptiLabCore-LICENSE.txt") -Force
    Copy-Item (Join-Path $upstream "NOTICE")  (Join-Path $dest "OptiLabCore-NOTICE.txt")  -Force
}
Write-Host "Staged the OptiLab Core adapter and its licence files."

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the shared runtime and the portable app BEFORE they are
# zipped or embedded in the installer, so the signed binaries are what ships.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir $installerLauncherDir --label "radio payload"
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

# -- retired downloads never ride along ----------------------------------------
# dist\ is a work area, and an older build of this script left the thin
# installer and the Companion zip in it. Anything left there is one drag-and-drop
# away from being published beside the real two, so this version's copies go.
foreach ($retired in @("Quill-Radio-Lite-Setup-$version.exe", "Quill-Radio-Companion-$version.zip")) {
    $stale = Join-Path $repoRoot "dist\$retired"
    if (Test-Path $stale) {
        Remove-Item $stale -Force
        Write-Host "Removed retired artifact $retired (Radio ships two downloads since 3.0.0)."
    }
}
$staleCompanion = Join-Path $repoRoot "dist\QuillRadio-Companion"
if (Test-Path $staleCompanion) { Remove-Item $staleCompanion -Recurse -Force }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File -Filter "*-$version.*" | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
