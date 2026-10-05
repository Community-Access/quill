# Builds every Quill Converter release artifact:
#
#   dist\QuillConverter\                           the staged portable folder
#   dist\Quill-Converter-Portable-<ver>.zip        portable (with its data\ folder)
#   dist\Quill-Converter-Setup-Shared-<ver>.exe    the installer (bundles the runtime)
#
# TWO artifacts, the shape QUILL Lite (2026-09-15) and Quill Radio (3.0.0,
# 2026-09-26) settled on after the four-download era: a Companion zip binds to
# whatever shared runtime is already on the machine -- including one frozen
# before the app it launches, which fails at launch and cannot self-heal -- and
# a thin installer trades a smaller download for a first-launch download. With
# two, Check for Updates asks one honest question, portable or not
# (quill.apps.converter_menu passes match_edition=False).
#
# Everything is bundled and neither artifact downloads anything, ever:
#   - FFmpeg + ffprobe (tools\ffmpeg; pinned and SHA-256-verified),
#   - libmpv (tools\mpv), the Chapter Workbench's player,
#   - yt-dlp for Convert from URL and mutagen for cover art (frozen into the
#     runtime; installed into the portable's own site-packages),
#   - the OptiLab Core adapter, when this machine has a C++ toolchain.
# No GitHub token is generated or embedded: feedback goes by email to
# support@community-access.org (Help > Get Help from Support).
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-FfmpegDir <dir>]
#                               [-LibmpvDir <dir>] [-Iscc <path>]
#                               [-SkipSharedRuntime] [-Sign]

param(
    [string]$Python = "",
    [string]$FfmpegDir = "",
    [string]$LibmpvDir = "",
    [string]$Iscc = "",
    [string]$QuillRepo = "",
    [switch]$SkipSharedRuntime,
    [int]$Build = 0,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "1.0.0"

# Authenticode signing is opt-in (docs/code-signing.md); a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- resolve the toolchain ----------------------------------------------------
# standalone\converter -> standalone -> the QUILL checkout root.
if (-not $QuillRepo) {
    $QuillRepo = Split-Path -Parent (Split-Path -Parent $repoRoot)
}
. (Join-Path $QuillRepo "scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
$Iscc = Resolve-QuillIscc -Preferred $Iscc

# The build number: -Build, else the next one after the newest tag published
# for $version. It must equal the app's build constant in source, which the
# runtime carries; the installer records it and Windows shows X.Y.Z.B.
$build, $fileVersion = Resolve-QuillReleaseBuild -QuillRepo $QuillRepo -Python $Python -App "converter" -Version $version -Build $Build

# -- the version is one number ---------------------------------------------
# The app's _VERSION, this script's $version and the .iss fallback must agree,
# or Check for Updates compares against the wrong number.
$appSource = Get-Content -Raw (Join-Path $QuillRepo "quill/apps/converter.py")
if ($appSource -notmatch '(?m)^_VERSION\s*=\s*"([^"]+)"') {
    throw "Could not read _VERSION from quill/apps/converter.py."
}
if ($Matches[1] -ne $version) {
    throw "quill/apps/converter.py says $($Matches[1]) but this script builds $version -- bump them together."
}

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- refresh the published site's copies of these docs ------------------------
& $Python (Join-Path $QuillRepo "scripts\sync_site_docs.py") --app converter
if ($LASTEXITCODE -ne 0) { throw "Site docs sync failed (see above)." }

# -- the Explorer verb block, regenerated from the format catalogue -----------
& $Python (Join-Path $QuillRepo "scripts\build_converter_verb_iss.py")
if ($LASTEXITCODE -ne 0) { throw "Could not generate installer\explorer-verb.isi." }

# -- ffmpeg to bundle ---------------------------------------------------------
# SECURITY: copied verbatim into the release, so never resolved from the
# builder's PATH. Absent an explicit vetted directory, stage QUILL's pinned,
# SHA-256-verified build (scripts/fetch_build_deps.py).
if (-not $FfmpegDir) {
    Write-Host "Staging ffmpeg from QUILL's pinned release assets..."
    & $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only ffmpeg
    if ($LASTEXITCODE -ne 0) { throw "Could not stage ffmpeg (see scripts/fetch_build_deps.py)." }
    $FfmpegDir = Join-Path $QuillRepo "build\deps\ffmpeg"
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found in -FfmpegDir '$FfmpegDir'."
}
if (-not (Test-Path (Join-Path $FfmpegDir "ffprobe.exe"))) {
    # File Properties, Split by Chapters and Join all read files with ffprobe.
    throw "ffprobe.exe not found in -FfmpegDir '$FfmpegDir'."
}

# -- shared QuillVille Runtime ------------------------------------------------
$sharedRuntimeDist = Join-Path $repoRoot "..\runtime\dist\QuillVilleRuntime"
if ($SkipSharedRuntime -and (Test-Path (Join-Path $sharedRuntimeDist "QuillVilleRuntime.exe"))) {
    Write-Host "Reusing existing shared runtime at $sharedRuntimeDist (-SkipSharedRuntime)."
} else {
    Push-Location (Join-Path $repoRoot "..\runtime")
    try {
        & (Join-Path $repoRoot "..\runtime\build_runtime.ps1") -Python $Python
        if ($LASTEXITCODE -ne 0) { throw "Shared QuillVille Runtime build failed." }
    } finally {
        Pop-Location
    }
}
# -- libmpv to bundle ----------------------------------------------------------
# The Chapter Workbench's player (1.0.0): exact seeking in every format is what
# makes "set this chapter's start to the playhead" land where you heard it.
# SECURITY: never the user-writable %APPDATA%\Quill\engine-packs\mpv copy;
# absent an explicit vetted directory, the pinned, SHA-256-verified pack.
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
# yt-dlp needs a JavaScript runtime to solve YouTube's challenges, for Convert
# from URL (one video, a playlist or a channel). Pinned and SHA-256-verified by
# fetch_build_deps.py, as Quill Radio's is -- never from PATH, never downloaded
# at run time.
Write-Host "Staging deno from its pinned release..."
& $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") --only deno
if ($LASTEXITCODE -ne 0) { throw "Could not stage deno (see scripts/fetch_build_deps.py)." }
$DenoDir = Join-Path $QuillRepo "build\deps\deno"
# Converter declares ffmpeg and mpv (REQUIRED_COMPONENTS), and deno for yt-dlp.
. (Join-Path $QuillRepo "scripts\StageMediaTools.ps1")
Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir -LibmpvDir $LibmpvDir -DenoDir $DenoDir

# -- the runtime must actually contain this app, and what it needs -----------
Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.converter"
Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.converter_actions"

# -- portable bundle (self-contained, genuine embeddable runtime) -------------
$appDir = Join-Path $repoRoot "dist\QuillConverter"
& $Python (Join-Path $QuillRepo "standalone\studio\scripts\build_portable.py") `
    --product converter `
    --out $appDir `
    --source-root $QuillRepo `
    --ffmpeg-dir $FfmpegDir `
    --mpv-dir $LibmpvDir `
    --deno-dir $DenoDir `
    --version $version
if ($LASTEXITCODE -ne 0) { throw "Portable bundle build failed." }
foreach ($required in @("QuillConverter.exe", "pythonw.exe", "tools\ffmpeg\ffmpeg.exe", "tools\ffmpeg\ffprobe.exe", "tools\mpv\libmpv-2.dll")) {
    if (-not (Test-Path (Join-Path $appDir $required))) {
        throw "Portable build is missing $required."
    }
}
# Nothing may download on first use: prove the bundled Python has both.
& (Join-Path $appDir "python.exe") -c "import yt_dlp, mutagen; print('bundled: yt-dlp', yt_dlp.version.__version__, 'mutagen', mutagen.version_string)"
if ($LASTEXITCODE -ne 0) { throw "The portable bundle lacks yt-dlp or mutagen." }

# -- OptiLab Core adapter (optional; best effort, as in Radio's build) --------
& $Python (Join-Path $QuillRepo "scripts\build_native_optilab.py") --out $appDir
$optilabExe = Join-Path $appDir "quill-optilab.exe"
if (Test-Path $optilabExe) {
    $upstream = Join-Path $QuillRepo "quill\native\optilab\upstream"
    foreach ($dest in @($appDir, $sharedRuntimeDist)) {
        $optilabTarget = Join-Path $dest "quill-optilab.exe"
        if ([IO.Path]::GetFullPath($optilabTarget) -ne [IO.Path]::GetFullPath($optilabExe)) {
            Copy-Item $optilabExe $optilabTarget -Force
        }
        Copy-Item (Join-Path $upstream "LICENSE") (Join-Path $dest "OptiLabCore-LICENSE.txt") -Force
        Copy-Item (Join-Path $upstream "NOTICE")  (Join-Path $dest "OptiLabCore-NOTICE.txt")  -Force
    }
    Write-Host "Staged the OptiLab Core adapter and its licence files."
} else {
    Write-Host "No OptiLab adapter in this build; exact OptiLab processing will be unavailable."
}

# -- code signing (payload) ---------------------------------------------------
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $sharedRuntimeDist $appDir --label "converter payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\Quill-Converter-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Write-Host "Compressing portable bundle -> $zipPath ..."
Compress-Archive -Path $appDir -DestinationPath $zipPath

# -- installer (Inno Setup 7; signs Setup.exe + uninstaller when signing is on)
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" "/dAppBuild=$build" "/dAppFileVersion=$fileVersion" (Join-Path $repoRoot "installer\quill-converter.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File -Filter "*-$version.*" | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
