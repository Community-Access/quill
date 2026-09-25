# Builds every QUILL Lite release artifact from one onedir build:
#
#   dist\QuillLite\                        the staged app folder
#   dist\QuillLite-Portable-<ver>.zip      portable (with its data\ folder)
#   dist\QuillLite-Setup-Shared-<ver>.exe  the installer (bundles the runtime)
#
# TWO artifacts, not four (2026-09-15). QUILL Lite used to publish the thin
# "Lite" installer and the launcher-only Companion zip as well, and both were
# wrong for THIS product. The Companion zip installs nothing, so it binds to
# whatever shared runtime is already on the machine -- including one built
# before QUILL Lite existed, which fails at launch with "No module named
# quill.apps.lite" and cannot self-heal, because the bootstrap only fires when
# NO runtime resolves and a stale one resolves fine. The thin installer traded
# a 114 MB download for a 110 MB first-launch download plus a network
# dependency, on the one app people install BECAUSE they have nothing else --
# so the runtime is usually absent and the saving is notional. And it was
# called Lite twice.
#
# Retiring them is safe for anyone already on one: both installers share an
# AppId, so the full one upgrades a thin install in place, and the updater
# falls through to an installable asset when a release publishes none for the
# running edition (core/updates.py::_pick_app_asset). The other eight apps are
# unchanged and still ship all four.
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-TokenFile <path>]
#                               [-Iscc <path>] [-SkipToken] [-SkipSharedRuntime]
#                               [-Sign]
#
# QUILL Lite is a text editor: no ffmpeg, no libmpv, no media, AI or speech
# stacks -- so, unlike Quill Radio's build, there is nothing to stage under its
# own tools\. -FfmpegDir/-LibmpvDir are still accepted so an existing build
# command keeps working; they are unused here. Pass -SkipSharedRuntime to reuse
# a runtime another app already built. Everything is bundled; the installer
# and the zip perform no downloads.

param(
    [string]$Python = "",
    # QUILL Lite's own payload bundles neither ffmpeg nor mpv, and the shared
    # QuillVille Runtime no longer bundles them either -- the apps that declare
    # them (Radio, Cast, Studio) stage them in themselves. Both switches are
    # still accepted so an existing build command keeps working; they are simply
    # unused here, which is exactly the 304 MB QUILL Lite stops installing.
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = "",
    [string]$TokenFile = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    [switch]$SkipToken,
    [switch]$SkipSharedRuntime,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "1.0.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\quilllite -> standalone -> the QUILL checkout root.
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

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (Report a Bug for users with no GitHub setup) -----
if (-not $SkipToken) {
    # -TokenFile is one of several sources generate_feedback_token.py accepts
    # (env var, token file, Windows Credential Manager, or a token already
    # bundled by this machine's last build). Pass it when given; otherwise let
    # the generator resolve, and let ITS --require-token error explain every
    # option rather than throwing here about the one source we happen to know.
    $TokenFile = Resolve-QuillTokenFile -Preferred $TokenFile
    if ($TokenFile) { $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile }
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
}

# -- shared QuillVille Runtime (the onedir the per-app installer ships) -----
# The shared runtime at ..\..\runtime\dist\QuillVilleRuntime\ is what the
# per-app installer (quill-lite.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. It no longer carries
# ffmpeg or libmpv, so this is a plain runtime build with nothing to stage.
$sharedRuntimeDist = Join-Path $repoRoot "..\runtime\dist\QuillVilleRuntime"
if ($SkipSharedRuntime -and (Test-Path (Join-Path $sharedRuntimeDist "QuillVilleRuntime.exe"))) {
    Write-Host "Reusing existing shared runtime at $sharedRuntimeDist (--SkipSharedRuntime)."
} else {
    # Nothing is staged into the runtime here, and that is the point. QUILL Lite
    # declares no components, so it contributes no ffmpeg, no ffprobe and no
    # libmpv -- 304 MB, 41% of what this installer used to carry, for tools it
    # can never call. Staging is opt-in (scripts\StageMediaTools.ps1), so there
    # is no per-app exclusion list to keep in step.
    #
    # This also retires an ordering dependency nothing documented: build_runtime
    # used to refuse to run without a vetted ffmpeg AND libmpv directory, so
    # every QUILL Lite build failed unless some other app had already produced the
    # runtime, and the -FfmpegDir the caller reached for was silently swallowed
    # into $args.
    Push-Location (Join-Path $repoRoot "..\runtime")
    try {
        & (Join-Path $repoRoot "..\runtime\build_runtime.ps1") -Python $Python
        if ($LASTEXITCODE -ne 0) { throw "Shared QuillVille Runtime build failed." }
    } finally {
        Pop-Location
    }
}

# -- the runtime must actually contain this app -------------------------------
# Compiling and installing are not evidence that the thing runs. The shared
# runtime carries its OWN frozen copy of the quill package, so a runtime built
# before QUILL Lite existed does not contain quill.apps.lite -- and the installer
# compiles, installs, and then fails on first launch with "No module named
# quill.apps.lite". That shipped once, on 2026-09-08, because -SkipSharedRuntime
# reused a runtime from three weeks earlier. One import is the cheapest check
# that catches it, and it runs whether or not the runtime was rebuilt here.
Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.lite" -ProbeArgs "--check"

# -- portable bundle (self-contained, genuine embeddable runtime) -------------
# NOT a PyInstaller onedir and NOT a stamped pythonw.exe. See build_portable.py
# and docs/design/native-launcher-2026-07-24.md: genuine unmodified
# python.exe/pythonw.exe + the native C launcher (QuillLite.exe) spawning
# `pythonw.exe -m quill.apps.lite`. QUILL Lite is small -- no ffmpeg/mpv/engines.
$appDir = Join-Path $repoRoot "dist\QuillLite"
& $Python (Join-Path $QuillRepo "standalone\studio\scripts\build_portable.py") `
    --product quilllite `
    --out $appDir `
    --source-root $QuillRepo `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillLite.exe"))) {
    throw "Portable build did not produce the native QuillLite.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the shared runtime and the portable app BEFORE they are
# zipped or embedded in the installer. Opt-in via -Sign / QUILL_SIGN; else no-op.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "quilllite payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\QuillLite-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- strip staged media tools from the runtime payload -----------------------
# QUILL Lite declares no media components, but the shared runtime dist is a
# COMMUNAL work area: a media app's build (Radio, Studio, Cast) stages
# ffmpeg/libmpv into its tools\ and leaves them there. Packed wholesale,
# they cost this installer 304 MB for tools QUILL Lite can never call -- the
# 2026-08-18 rebuild shipped exactly that because it ran after Radio's.
# Stripping here makes build order irrelevant; a media app's own build
# re-stages what it declares every time.
foreach ($tool in @("ffmpeg", "mpv")) {
    $staged = Join-Path $sharedRuntimeDist "tools\$tool"
    if (Test-Path $staged) {
        Remove-Item $staged -Recurse -Force
        Write-Host "Stripped staged $tool from the runtime payload (QUILL Lite declares no media tools)."
    }
}

# -- installer (Inno signs Setup.exe + the uninstaller when signing is on) ----
# When QUILL_SIGN=1, pass /DSign plus the /Squilltrusted sign-command mapping so
# the .iss SignTool/SignedUninstaller directives activate ($q -> ", $f -> file).
# Without it, $innoSign is empty and the build compiles unsigned.
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quilllite.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
