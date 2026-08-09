# Builds every QUILL Social release artifact from one onedir build:
#
#   dist\QuillSocial\                        the staged app folder
#   dist\QUILL-Social-Portable-<ver>.zip     portable (with its data\ folder)
#   dist\QUILL-Social-Setup-<ver>.exe        system installer
#
# Usage:
#   .\scripts\build_release.ps1 [-Python <python.exe>] [-TokenFile S:\token.txt]
#                               [-Iscc <path>] [-QuillRepo S:\QUILL]
#
# Mirrors quill-radio's build_release.ps1, minus the ffmpeg/mpv staging (Social
# is text-and-network; media playback is an optional runtime extra, not bundled).
# Everything else is bundled; the installer and zip perform no downloads.

param(
    [string]$Python = "S:\QUILL\.venv\Scripts\python.exe",
    [string]$TokenFile = "S:\token.txt",
    [string]$Iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [string]$QuillRepo = "S:\QUILL",
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$version = "0.3.0"

# Authenticode code signing is opt-in (docs/code-signing.md). -Sign turns it on
# for this run via QUILL_SIGN, read by QUILL\scripts\code_signing.py. Without it
# the sign-build steps below are no-ops, so a plain build is unchanged.
if ($Sign) { $env:QUILL_SIGN = "1" }

# -- render docs (html + epub from the markdown source) -----------------------
& (Join-Path $PSScriptRoot "render_docs.ps1")

# -- bundled feedback token (Report a Bug for users with no GitHub setup) -----
# Best-effort for Social: embed the issues-only token when it is available so
# the shared bug reporter works, but do not fail the build without it (unlike a
# QUILL/Radio release, where it is a hard requirement).
if (Test-Path $TokenFile) {
    $env:QUILL_FEEDBACK_TOKEN_FILE = $TokenFile
    & $Python (Join-Path $QuillRepo "tools\generate_feedback_token.py") --require-token
    if ($LASTEXITCODE -ne 0) { throw "Bundled feedback token generation failed." }
} else {
    Write-Warning "Token file not found: $TokenFile -- building without the bundled bug-report token."
}

if (-not (Test-Path $Iscc)) {
    $fallback = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $fallback) { $Iscc = $fallback } else { throw "ISCC.exe not found: $Iscc" }
}

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quill-social.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
$appDir = Join-Path $repoRoot "dist\QuillSocial"
if (-not (Test-Path (Join-Path $appDir "QuillSocial.exe"))) {
    throw "Onedir build did not produce QuillSocial.exe"
}

# -- stage docs (both artifacts ship these) -----------------------------------
$stagedDocs = Join-Path $appDir "docs"
New-Item -ItemType Directory -Force $stagedDocs | Out-Null
Get-ChildItem (Join-Path $repoRoot "docs") -File |
    Where-Object { $_.Extension -in ".md", ".html" } |
    ForEach-Object { Copy-Item $_.FullName $stagedDocs -Force }
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $appDir "README-QUILL-Social.md") -Force

# -- portable zip (adds the data\ folder = portable-mode switch) --------------
# launcher.py exports QUILLSOCIAL_DATA when a data\ folder sits next to the exe,
# so the whole local store travels on a stick. The installed flavor ships no
# data\ folder and keeps using the platform app-data store.
$dataDir = Join-Path $appDir "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Set-Content (Join-Path $dataDir "README.txt") @"
This folder makes QUILL Social portable: your accounts, drafts, schedules,
and settings live here, right next to the app, so the whole thing travels on
a stick. Delete this folder and the app uses the shared Quill data in your
Windows profile instead.
"@
# -- code signing (payload) ---------------------------------------------------
# Sign every exe/dll in the app BEFORE it is zipped or embedded in the installer.
# Opt-in via -Sign / QUILL_SIGN; a no-op otherwise.
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $appDir --label "social payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (payload) failed." }

$zipPath = Join-Path $repoRoot "dist\QUILL-Social-Portable-$version.zip"
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
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $repoRoot "installer\quill-social.iss") "/O$(Join-Path $repoRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

Write-Host ""
Write-Host "Release artifacts in $(Join-Path $repoRoot 'dist'):"
Get-ChildItem (Join-Path $repoRoot "dist") -File | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MB" -f $_.Name, ($_.Length / 1MB))
}
