# Builds every Quill Weather release artifact from one onedir build:
#
#   dist\QuillWeather\                        the staged app folder
#   dist\Quill-Weather-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\Quill-Weather-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-TokenFile <path>]
#                               [-Iscc <path>] [-SkipToken] [-SkipSharedRuntime]
#                               [-FfmpegDir <dir>] [-LibmpvDir <dir>]
#
# Quill Weather is a small app: no ffmpeg, no mpv, no media/AI stacks -- so,
# unlike Quill Radio's build, there is nothing to stage under its own tools\.
# The *shared* runtime it builds does bundle both, though, which is why
# -FfmpegDir/-LibmpvDir exist here; omit them and the pinned, SHA-256-verified
# packs are staged automatically. Pass -SkipSharedRuntime to reuse a runtime
# another app already built. It is
# versioned in lockstep with Quill Radio (2.2.0) but built and released on its
# own. Everything is bundled; the installer and zip perform no downloads.

# Every path below defaults to "" and is resolved from the checkout itself, so a
# clone builds on any machine. Hardcoded D:\ defaults used to make this script
# runnable on exactly one computer.
param(
    [string]$Python = "",
    # Weather's own payload bundles neither ffmpeg nor mpv, and the shared
    # QuillVille Runtime no longer bundles them either -- the apps that declare
    # them (Radio, Cast, Studio) stage them in themselves. Both switches are
    # still accepted so an existing build command keeps working; they are simply
    # unused here, which is exactly the 304 MB Weather stops installing.
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
$version = "2.2.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\weather -> standalone -> the QUILL checkout root.
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
# per-app installer (quill-weather.iss) installs into
# %LOCALAPPDATA%\QuillVille\Runtime\3.13\ on first use. It no longer carries
# ffmpeg or libmpv, so this is a plain runtime build with nothing to stage.
$sharedRuntimeDist = Join-Path $repoRoot "..\runtime\dist\QuillVilleRuntime"
if ($SkipSharedRuntime -and (Test-Path (Join-Path $sharedRuntimeDist "QuillVilleRuntime.exe"))) {
    Write-Host "Reusing existing shared runtime at $sharedRuntimeDist (--SkipSharedRuntime)."
} else {
    # Nothing is staged into the runtime here, and that is the point. Weather
    # declares no components, so it contributes no ffmpeg, no ffprobe and no
    # libmpv -- 304 MB, 41% of what this installer used to carry, for tools it
    # can never call. Staging is opt-in (scripts\StageMediaTools.ps1), so there
    # is no per-app exclusion list to keep in step.
    #
    # This also retires an ordering dependency nothing documented: build_runtime
    # used to refuse to run without a vetted ffmpeg AND libmpv directory, so
    # every Weather build failed unless some other app had already produced the
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

# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the shared runtime and the portable app BEFORE they are
# zipped or embedded in the installer. Opt-in via -Sign / QUILL_SIGN; else no-op.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "weather payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\Quill-Weather-Portable-$version.zip"
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
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-weather.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
