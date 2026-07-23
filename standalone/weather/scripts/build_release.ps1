# Builds every Quill Weather release artifact from one onedir build:
#
#   dist\QuillWeather\                        the staged app folder
#   dist\Quill-Weather-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\Quill-Weather-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-TokenFile S:\token.txt]
#                               [-Iscc <path>] [-SkipToken]
#
# Quill Weather is a small app: no ffmpeg, no mpv, no media/AI stacks -- so,
# unlike Quill Radio's build, there is nothing to stage under tools\. It is
# versioned in lockstep with Quill Radio (2.2.0) but built and released on its
# own. Everything is bundled; the installer and zip perform no downloads.

param(
    [string]$Python = "S:\QUILL\.venv\Scripts\python.exe",
    [string]$TokenFile = "S:\token.txt",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$QuillRepo = "S:\QUILL",
    [switch]$SkipToken
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "2.2.0"

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (Report a Bug for users with no GitHub setup) -----
if (-not $SkipToken) {
    if (-not (Test-Path $TokenFile)) {
        throw "Token file not found: $TokenFile -- a release build must embed the issues-only token (or pass -SkipToken for a private build)."
    }
    $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
}

if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
}

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quill-weather.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
$appDir = Join-Path $repoRoot "dist\QuillWeather"
if (-not (Test-Path (Join-Path $appDir "QuillWeather.exe"))) {
    throw "Onedir build did not produce QuillWeather.exe"
}

# -- stage the bundled docs (both artifacts ship this) ------------------------
$docsDir = Join-Path $appDir "docs"
New-Item -ItemType Directory -Force $docsDir | Out-Null
foreach ($stem in @("userguide", "release-notes-2.2", "prd")) {
    Copy-Item (Join-Path $repoRoot "docs\$stem.md") $docsDir -Force
    Copy-Item (Join-Path $repoRoot "docs\$stem.html") $docsDir -Force
}
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $appDir "README-Quill-Weather.md") -Force

# -- portable zip (adds the data\ folder = portable-mode evidence) ------------
$dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Set-Content (Join-Path $dataDir "README.txt") @"
This folder makes Quill Weather portable: your saved locations and settings
live here, right next to the app, so the whole thing travels on a stick.
Delete this folder and the app uses the shared Quill data in your Windows
profile instead (shared with QUILL and Quill Radio on the same machine).
"@
# The storage-mode marker is what actually routes data here.
Set-Content (Join-Path $dataDir "storage-mode.json") '{"mode": "portable"}'
$zipPath = Join-Path $repoRoot "dist\Quill-Weather-Portable-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $appDir -DestinationPath $zipPath
# The installed flavor must NOT carry the data folder (it would flip the
# installed copy into portable mode), so remove it before the installer runs.
Remove-Item $dataDir -Recurse -Force

# -- installer ----------------------------------------------------------------
& $Iscc "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-weather.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
