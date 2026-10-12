# Builds every QUILL Transcribe release artifact:
#
#   dist\QuillTranscribe\                           the staged app folder
#   dist\QUILL-Transcribe-Portable-<ver>.zip        portable (with its data\ folder)
#   dist\QUILL-Transcribe-Setup-Shared-<ver>.exe    the installer (bundles the runtime)
#
# Two editions, as QUILL Lite and every app since: the installer and the
# portable zip. No thin installer, no launcher-only companion zip.
#
# QUILL Transcribe is dictation into other programs and nothing else: no
# ffmpeg, no libmpv, no media stack. What it does carry is dictation's own
# engine and models -- the same ones QUILL Lite ships -- beside its launcher,
# never inside the shared runtime every QuillVille app installs. Everything is
# bundled; the installer and the zip perform no downloads.
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-Iscc <path>]
#                               [-SkipSharedRuntime] [-Sign]

param(
    [string]$Python = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    [switch]$SkipSharedRuntime,
    [switch]$SkipPublishedCheck,
    # A Dev build's version. Release builds never pass it; the literal below
    # stays the app's real version.
    [string]$DevVersion = "",
    [int]$Build = 0,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "1.0.0"
if ($DevVersion) { $version = $DevVersion }

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\transcribe -> standalone -> the QUILL checkout root.
if (-not $QuillRepo) {
    $QuillRepo = Split-Path -Parent (Split-Path -Parent $repoRoot)
}
. (Join-Path $QuillRepo "scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
$Iscc = Resolve-QuillIscc -Preferred $Iscc

# The build number: -Build, else the next one after the newest tag published
# for $version. It must equal _BUILD in quill\apps\transcribe.py.
$build, $fileVersion = Resolve-QuillReleaseBuild -QuillRepo $QuillRepo -Python $Python -App "transcribe" -Version $version -Build $Build -Dev:([bool]$DevVersion) -OfflineOk:$SkipPublishedCheck

# Beta and Dev builds are never code-signed (scripts\code_signing.py build-decision).
$null = Resolve-QuillSigning -QuillRepo $QuillRepo -Python $Python -Version $version -Dev:([bool]$DevVersion)

# GATE-SIBVER: no sibling in the runtime this ships may be ahead of its release.
Assert-QuillSiblingVersions -QuillRepo $QuillRepo -Python $Python -Releasing @("transcribe") -Skip:$SkipPublishedCheck

# The app's own version constant must be the version being built.
if (-not $DevVersion) {
    $source = Get-Content -Raw (Join-Path $QuillRepo "quill\apps\transcribe.py")
    $match = [regex]::Match($source, '(?m)^_VERSION\s*=\s*"([^"]+)"')
    if (-not $match.Success -or $match.Groups[1].Value -ne $version) {
        throw "quill\apps\transcribe.py _VERSION does not match $version."
    }
}

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")
& $Python (Join-Path $QuillRepo "scripts\sync_site_docs.py") --app transcribe
if ($LASTEXITCODE -ne 0) { throw "Site docs sync failed." }

# -- shared QuillVille Runtime --------------------------------------------------
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

# -- the runtime must actually contain this app -------------------------------
Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.transcribe"

# -- dictation models -----------------------------------------------------------
# Fetched from sherpa-onnx's releases and checked against the SHA-256 digests
# pinned in quill\core\windows_dictation\engines.py; a mismatch fails the build.
$modelsDir = Join-Path $QuillRepo "build\dictation-models"
$dictationPython = Join-Path $QuillRepo "build\dictation-python"
& $Python (Join-Path $QuillRepo "scripts\fetch_dictation_models.py") --out $modelsDir --package-out $dictationPython
if ($LASTEXITCODE -ne 0) { throw "Dictation models are missing or failed verification." }

# -- portable bundle (self-contained, genuine embeddable runtime) -------------
$appDir = Join-Path $repoRoot "dist\QuillTranscribe"
& $Python (Join-Path $QuillRepo "standalone\studio\scripts\build_portable.py") `
    --product transcribe `
    --out $appDir `
    --source-root $QuillRepo `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
if (-not (Test-Path (Join-Path $appDir "QuillTranscribe.exe"))) {
    throw "Portable build did not produce the native QuillTranscribe.exe launcher."
}
# The installer ships its own launcher (with the runtime self-heal URL); the
# portable's has none, so a damaged portable never offers a download.
$installerLauncherDir = Join-Path $repoRoot "dist\QuillTranscribe-installer"
if (-not (Test-Path (Join-Path $installerLauncherDir "QuillTranscribe.exe"))) {
    throw "Portable build did not produce the installer's QuillTranscribe.exe launcher."
}
if (-not (Test-Path (Join-Path $appDir "pythonw.exe"))) {
    throw "Portable build did not stage the genuine pythonw.exe interpreter."
}
# Beside QuillTranscribe.exe, where quill.core.windows_dictation.engines looks first.
$portableModels = Join-Path $appDir "dictation-models"
if (Test-Path $portableModels) { Remove-Item $portableModels -Recurse -Force }
Copy-Item $modelsDir $portableModels -Recurse

# -- code signing (payload) ---------------------------------------------------
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir $installerLauncherDir --label "transcribe payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

# A portable copy names its own version, as the installer's quill-app-version.ini does.
Set-Content -LiteralPath (Join-Path $appDir "quill-app-version.ini") -Value "[app]`r`nversion=$version`r`nversion_build=$version+$build" -Encoding ascii
$zipPath = Join-Path $repoRoot "dist\QUILL-Transcribe-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- strip staged media tools from the runtime payload -----------------------
# The shared runtime dist is a communal work area: a media app's build leaves
# ffmpeg/libmpv in its tools\. QUILL Transcribe declares none, so none ship.
foreach ($tool in @("ffmpeg", "mpv")) {
    $staged = Join-Path $sharedRuntimeDist "tools\$tool"
    if (Test-Path $staged) {
        Remove-Item $staged -Recurse -Force
        Write-Host "Stripped staged $tool from the runtime payload (QUILL Transcribe declares no media tools)."
    }
}

# -- installer (Inno signs Setup.exe + the uninstaller when signing is on) ----
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" "/dAppBuild=$build" "/dAppFileVersion=$fileVersion" (Join-Path $repoRoot "installer\quill-transcribe.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
