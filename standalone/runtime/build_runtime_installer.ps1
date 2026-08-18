# Compile QuillVille-Runtime-Setup.exe -- the standalone shared-runtime
# installer every "-Lite" app installer downloads from the latest GitHub
# release (see installer\quillville-runtime.iss for why it exists and what it
# deliberately leaves out).
#
# Separate from build_runtime.ps1 on purpose: every app's build_release.ps1
# invokes the runtime build, and compiling a ~150 MB installer on each of
# those runs would tax builds that only need the dist. Run this when the
# runtime itself is being released:
#
#   .\standalone\runtime\build_runtime_installer.ps1 [-Iscc <path>] [-Sign]
#
# Output: standalone\runtime\dist\QuillVille-Runtime-Setup.exe
# Publish: gh release upload <latest-release-tag> dist\QuillVille-Runtime-Setup.exe
#          (the Lite installers fetch releases/latest/download/QuillVille-Runtime-Setup.exe)

param(
    [string]$Iscc = "",
    [string]$Python = "",
    [string]$QuillRepo = "",
    [switch]$Sign
)

$ErrorActionPreference = "Stop"
$runtimeRoot = $PSScriptRoot

if (-not $QuillRepo) {
    # standalone\runtime -> standalone -> the QUILL checkout root.
    $QuillRepo = Split-Path -Parent (Split-Path -Parent $runtimeRoot)
}
. (Join-Path $QuillRepo "scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
$Iscc = Resolve-QuillIscc -Preferred $Iscc

if ($Sign) { $env:QUILL_SIGN = "1" }

# A built, gate-passing runtime is the input; this script never builds one,
# so it can never quietly ship a runtime the gates have not seen.
$dist = Join-Path $runtimeRoot "dist\QuillVilleRuntime"
$marker = Join-Path $dist "quillville-runtime.json"
if (-not (Test-Path (Join-Path $dist "QuillVilleRuntime.exe")) -or -not (Test-Path $marker)) {
    throw "No built runtime at $dist. Run build_runtime.ps1 first (and let its gates pass)."
}

# Version stamp: the python minor the runtime is built for plus the build
# date from its own marker, e.g. "3.13.20260818". The install path and the
# Lite installers' presence check key on the 3.13, so that leads.
$markerData = Get-Content $marker -Raw | ConvertFrom-Json
$buildDate = ([datetime]$markerData.build).ToString("yyyyMMdd")
$pythonMinor = ($markerData.python -split "\.")[0..1] -join "."
$version = "$pythonMinor.$buildDate"

# Sign the runtime payload before it is embedded (a no-op unless QUILL_SIGN=1).
$signer = Join-Path $QuillRepo "scripts\code_signing.py"
& $Python $signer sign-build $dist --label "runtime payload"
if ($LASTEXITCODE -ne 0) { throw "Code signing (runtime payload) failed." }

$innoSign = @()
if ($env:QUILL_SIGN -eq "1") {
    $innoSign = @("/DSign", "/Squilltrusted=`$q$Python`$q `$q$signer`$q sign `$f")
}
& $Iscc @innoSign "/dAppVersion=$version" (Join-Path $runtimeRoot "installer\quillville-runtime.iss") "/O$(Join-Path $runtimeRoot 'dist')"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

$setup = Join-Path $runtimeRoot "dist\QuillVille-Runtime-Setup.exe"
Write-Host ""
Write-Host ("Built {0}  ({1:N1} MB, runtime {2})" -f $setup, ((Get-Item $setup).Length / 1MB), $version)
Write-Host "Publish with: gh release upload <latest-release-tag> `"$setup`""
