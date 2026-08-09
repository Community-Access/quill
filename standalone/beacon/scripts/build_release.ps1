# Builds every QuillBeacon release artifact from one onedir build:
#
#   dist\QuillBeacon\                          the staged app folder
#   dist\Quill-Beacon-Portable-<ver>.zip       portable (with its data\ folder)
#   dist\Quill-Beacon-Setup-<ver>.exe          system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-LibmpvDir <dir>]
#                               [-Iscc <path>]
#
# QuillBeacon plays through the shared audio engine (quill.ui.audio), whose
# DEFAULT backend is wx.media / WMP -- so unlike radio there is NO required
# ffmpeg/mpv. libmpv is the OPT-IN backend (gapless, exact seeking,
# output-device routing); if a libmpv-2.dll is found it is staged under
# tools\mpv so the opt-in path works offline, but its absence is only a
# warning, never a build failure.

param(
    [string]$Python = "S:\QUILL\.venv\Scripts\python.exe",
    [string]$LibmpvDir = "",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$QuillRepo = "S:\QUILL",
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "0.1.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- optional libmpv (the opt-in backend; NOT required) -----------------------
if (-not $LibmpvDir) {
    $packDir = Join-Path $env:APPDATA "Quill\engine-packs\mpv"
    if (Test-Path (Join-Path $packDir "libmpv-2.dll")) { $LibmpvDir = $packDir }
}
$stageMpv = $LibmpvDir -and (Test-Path (Join-Path $LibmpvDir "libmpv-2.dll"))
if (-not $stageMpv) {
    Write-Warning "libmpv-2.dll not found -- shipping the wx.media default only (opt-in gapless/output-device playback will require an on-demand mpv download)."
}
if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
}

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quill-beacon.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
$appDir = Join-Path $repoRoot "dist\QuillBeacon"
if (-not (Test-Path (Join-Path $appDir "QuillBeacon.exe"))) {
    throw "Onedir build did not produce QuillBeacon.exe"
}

# -- stage the optional libmpv engine (GPL license texts alongside) -----------
if ($stageMpv) {
    $mpvDir = Join-Path $appDir "tools\mpv"
    New-Item -ItemType Directory -Force $mpvDir | Out-Null
    Copy-Item (Join-Path $LibmpvDir "libmpv-2.dll") $mpvDir -Force
    Get-ChildItem $LibmpvDir -File | Where-Object { $_.Extension -eq ".txt" } | ForEach-Object {
        Copy-Item $_.FullName $mpvDir -Force
    }
}

# -- stage docs (Help > User Guide / PRD; prefers pre-rendered .html) ----------
$docsDir = Join-Path $appDir "docs"
New-Item -ItemType Directory -Force $docsDir | Out-Null
Get-ChildItem (Join-Path $repoRoot "docs") -File | ForEach-Object { Copy-Item $_.FullName $docsDir -Force }
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $appDir "README-QuillBeacon.md") -Force

# -- portable zip (adds the data\ folder = portable-mode evidence) ------------
$dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Set-Content (Join-Path $dataDir "README.txt") @"
This folder makes QuillBeacon portable: your library, captures, and settings
live here, right next to the app, so the whole thing travels on a stick.
Delete this folder and the app uses %APPDATA%\QuillBeacon instead.
"@
# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the app BEFORE it is zipped or embedded in the installer.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $appDir --label "beacon payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\Quill-Beacon-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $appDir -DestinationPath $zipPath
# The installed flavor must NOT carry the data folder (it would flip the
# installed copy into portable mode), so remove it before the installer runs.
Remove-Item $dataDir -Recurse -Force

# -- installer ----------------------------------------------------------------
# When QUILL_SIGN=1, pass /DSign plus the /Squilltrusted sign-command mapping so
# the .iss SignTool/SignedUninstaller directives activate ($q -> ", $f -> file).
# Inno then signs both the compiled Setup.exe and the embedded uninstaller.
$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-beacon.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
