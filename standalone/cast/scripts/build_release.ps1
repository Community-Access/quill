# Builds every QUILL Cast release artifact from one onedir build:
#
#   dist\QUILLCast\                       the staged app folder
#   dist\QUILL-Cast-Portable-<ver>.zip    portable (with its data\ folder)
#   dist\QUILL-Cast-Setup-<ver>.exe       system installer
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

param(
    [string]$Python = "S:\QUILL\.venv\Scripts\python.exe",
    [string]$FfmpegDir = "",
    [string]$TokenFile = "S:\token.txt",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$QuillRepo = "S:\QUILL"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "1.0.5"

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (hard requirement for a release build) -----------
if (-not (Test-Path $TokenFile)) {
    throw "Token file not found: $TokenFile -- a release build must embed the issues-only token."
}
$env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
& $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }

# -- ffmpeg to bundle ---------------------------------------------------------
if (-not $FfmpegDir) {
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpeg) { $FfmpegDir = Split-Path -Parent $ffmpeg.Source }
}
if (-not $FfmpegDir -or -not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    throw "ffmpeg.exe not found. Pass -FfmpegDir; audio trim/normalize must ship bundled."
}
if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
}

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quill-cast.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
$appDir = Join-Path $repoRoot "dist\QUILLCast"
if (-not (Test-Path (Join-Path $appDir "QUILLCast.exe"))) {
    throw "Onedir build did not produce QUILLCast.exe"
}

# -- stage the shared payload (both artifacts ship this) ----------------------
$toolsDir = Join-Path $appDir "tools\ffmpeg"
New-Item -ItemType Directory -Force $toolsDir | Out-Null
Copy-Item (Join-Path $FfmpegDir "ffmpeg.exe") $toolsDir -Force
if (Test-Path (Join-Path $FfmpegDir "ffprobe.exe")) {
    Copy-Item (Join-Path $FfmpegDir "ffprobe.exe") $toolsDir -Force
}
$ffLicense = Join-Path (Split-Path -Parent $FfmpegDir) "LICENSE"
if (Test-Path $ffLicense) { Copy-Item $ffLicense (Join-Path $toolsDir "FFMPEG-LICENSE.txt") -Force }
$docsDir = Join-Path $appDir "docs"
New-Item -ItemType Directory -Force $docsDir | Out-Null
# .md + .html for every doc (Help > User Guide / Release Notes / Product
# Requirements... prefers the pre-rendered .html; .md is the fallback source
# if a build ever ships without render_docs.ps1 having run).
Copy-Item (Join-Path $repoRoot "docs\userguide.md") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\userguide.html") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\release-notes-1.0.md") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\release-notes-1.0.html") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\prd.md") $docsDir -Force
Copy-Item (Join-Path $repoRoot "docs\prd.html") $docsDir -Force
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $appDir "README-QUILL-Cast.md") -Force

# -- portable zip (adds the data\ folder = portable-mode evidence) ------------
$dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Set-Content (Join-Path $dataDir "README.txt") @"
This folder makes QUILL Cast portable: your subscriptions, downloads,
queue, notes, and settings live here, right next to the app, so the
whole thing travels on a stick. Delete this folder and the app uses
the shared Quill data in your Windows profile instead.
"@
# The storage-mode marker is what actually routes data here (the folder
# alone is only the portable-bundle evidence); QUILL portable ships the
# same marker.
Set-Content (Join-Path $dataDir "storage-mode.json") '{"mode": "portable"}'
$zipPath = Join-Path $repoRoot "dist\QUILL-Cast-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $appDir -DestinationPath $zipPath
# The installed flavor must NOT carry the data folder (it would flip the
# installed copy into portable mode), so remove it before the installer runs.
Remove-Item $dataDir -Recurse -Force

# -- installer ----------------------------------------------------------------
& $Iscc (Join-Path $repoRoot "installer\quill-cast.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
