<#
.SYNOPSIS
Build any QuillVille product from the repo root, with one command.

.DESCRIPTION
A thin dispatcher over the real build scripts, which stay where they live
(standalone\<product>\scripts\build_release.ps1, standalone\runtime\*.ps1,
scripts\build_windows_distribution.py). This file adds no build logic of its
own -- it resolves the right script, runs it from the repo root, and tees the
output to local\build-logs\ so a 500,000-line PyInstaller log never lands in
the terminal.

Everything else resolves itself: Python, ISCC, ffmpeg, libmpv and the bundled
feedback token all come from scripts\BuildEnv.ps1, so no paths need passing on
any machine.

.PARAMETER Product
Which product to build. Run ".\build.ps1 list" to see them all.

.PARAMETER Sign
Authenticode-sign the payload and installers (Azure Trusted Signing). Opt-in;
a signing failure is non-fatal unless QUILL_SIGN_REQUIRED=1 is also set.

.PARAMETER NoLog
Stream the full build output to the terminal instead of teeing it to a file.

.PARAMETER NoCopy
Leave the finished artifacts in the product's own dist folder instead of also
copying them to the \installs collection folder.

.EXAMPLE
.\build.ps1 radio
Build every Quill Radio artifact: the portable zip, the Companion zip, the
shared installer and the Lite installer.

.EXAMPLE
.\build.ps1 radio -SkipSharedRuntime
Rebuild Radio only, reusing the shared runtime already in
standalone\runtime\dist (saves ~10 minutes; see the ordering note below).

.EXAMPLE
.\build.ps1 all
Build the shared runtime, its standalone installer, and every app, in the
order that keeps each artifact honest.

.NOTES
ORDERING -- why "all" runs runtime, then runtime-installer, then the apps.
Each media app stages the tools it declares (ffmpeg, libmpv: 306 MB) into the
shared runtime dist AFTER the runtime is built, and nothing unstages them.
QuillVille-Runtime-Setup.exe is compiled from whatever is sitting in that dist,
and it is meant to carry the BASE runtime only. So the runtime installer is
compiled straight after a fresh runtime build, before any app has staged into
it. If you build the runtime installer by hand, do it on a freshly built
runtime for the same reason.
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet(
        'list', 'all',
        'runtime', 'runtime-installer',
        'quill',
        'radio', 'cast', 'weather', 'studio', 'inkwell', 'beacon', 'social'
    )]
    [string]$Product = 'list',

    [switch]$Sign,
    [switch]$NoLog,
    [switch]$NoCopy,

    # Anything else is handed straight to the underlying build script, so
    # -SkipSharedRuntime, -SkipCatalog, -SkipToken, -Offline, -Iscc <path>,
    # -Python <exe> and friends all keep working unchanged.
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot

# Where finished installers and portable zips are collected, deliberately
# written WITHOUT a drive letter: a leading backslash resolves against the root
# of whatever drive the checkout lives on, so the same path works from S:\QUILL
# and from a clone on D: or C: with nothing to edit.
$InstallsDir = '\installs'

# Each entry: the script that builds it, a one-line description for "list", and
# the folders its shippable artifacts land in (copied to \installs afterwards).
#   app     -> standalone\<Dir>\scripts\build_release.ps1, dist beside it
#   ps1     -> an explicit PowerShell script path
#   python  -> a Python script plus its fixed arguments
$Products = [ordered]@{
    'runtime' = @{
        Kind = 'ps1'
        Path = 'standalone\runtime\build_runtime.ps1'
        # A folder, not a shippable file: runtime-installer packages it.
        Dist = @()
        Desc = 'QuillVille Runtime -- the shared CPython every app reuses'
    }
    'runtime-installer' = @{
        Kind = 'ps1'
        Path = 'standalone\runtime\build_runtime_installer.ps1'
        Dist = @('standalone\runtime\dist')
        Desc = 'QuillVille-Runtime-Setup.exe (build on a fresh runtime)'
    }
    'quill' = @{
        Kind = 'python'
        Path = 'scripts\build_windows_distribution.py'
        Args = @('--bundle-python', '--compile-installer')
        # The portable zip sits in the output dir; Inno drops the .exe in Output\.
        Dist = @(
            'dist\windows',
            'dist\windows\installer\Output',
            'dist\windows-offline',
            'dist\windows-offline\installer\Output'
        )
        Desc = 'QUILL itself -- portable bundle + Windows installer'
    }
    'radio'   = @{ Kind = 'app'; Dir = 'radio';   Desc = 'Quill Radio' }
    'cast'    = @{ Kind = 'app'; Dir = 'cast';    Desc = 'QUILL Cast (podcasts)' }
    'weather' = @{ Kind = 'app'; Dir = 'weather'; Desc = 'Quill Weather' }
    'studio'  = @{ Kind = 'app'; Dir = 'studio';  Desc = 'Quill Audio Studio (add -Offline for the Offline Edition)' }
    'inkwell' = @{ Kind = 'app'; Dir = 'inkwell'; Desc = 'Quill Inkwell' }
    'beacon'  = @{ Kind = 'app'; Dir = 'beacon';  Desc = 'Quill Beacon' }
    'social'  = @{ Kind = 'app'; Dir = 'social';  Desc = 'Quill Social' }
}

# See the ordering note in the header.
$AllOrder = @(
    'runtime', 'runtime-installer',
    'radio', 'cast', 'studio', 'weather', 'inkwell', 'beacon', 'social',
    'quill'
)

function Show-ProductList {
    Write-Host ''
    Write-Host 'Usage: .\build.ps1 <product> [-Sign] [-NoLog] [-NoCopy] [extra args passed through]'
    Write-Host '   or: build-<product>.cmd [same options]'
    Write-Host ''
    Write-Host 'Products:'
    foreach ($name in $Products.Keys) {
        Write-Host ('  {0,-18} {1}' -f $name, $Products[$name].Desc)
    }
    Write-Host ('  {0,-18} {1}' -f 'all', 'every product above, in build order')
    Write-Host ''
    Write-Host 'No build shell yet: converter, player, radio-mac.'
    Write-Host 'Logs:      local\build-logs\<product>-<timestamp>.log (-NoLog streams instead).'
    Write-Host "Artifacts: the product's dist folder, copied to $InstallsDir (-NoCopy skips)."
    Write-Host ''
}

function Resolve-BuildScript {
    param([string]$Name)

    $entry = $Products[$Name]
    if ($entry.Kind -eq 'app') {
        $path = Join-Path $RepoRoot "standalone\$($entry.Dir)\scripts\build_release.ps1"
    } else {
        $path = Join-Path $RepoRoot $entry.Path
    }
    if (-not (Test-Path $path)) {
        throw "No build script for '$Name' at $path."
    }
    return @{ Entry = $entry; Path = $path }
}

function Get-DistFolders {
    param([hashtable]$Entry)

    # Every app keeps its artifacts in standalone\<dir>\dist; the two products
    # that do not follow that shape name their folders explicitly above.
    if ($Entry.ContainsKey('Dist')) { return $Entry.Dist }
    return @("standalone\$($Entry.Dir)\dist")
}

function ConvertTo-ParameterSplat {
    <#
    .SYNOPSIS
    Turn pass-through tokens into a hashtable to splat at a PowerShell script.

    .DESCRIPTION
    Array splatting (& $script @tokens) passes every element as a POSITIONAL
    argument, so "-SkipSharedRuntime" arrived at build_release.ps1 as the value
    of its first positional parameter and the build died with "Python at
    '-SkipSharedRuntime' is not runnable". Hashtable splatting is what actually
    binds by name. A token followed by a non-option token is a parameter with a
    value (-Iscc <path>); a token followed by another option, or by nothing, is
    a switch.
    #>
    param([string[]]$Tokens)

    $splat = @{}
    if (-not $Tokens) { return $splat }

    for ($i = 0; $i -lt $Tokens.Count; $i++) {
        $token = $Tokens[$i]
        if ($token -notmatch '^-{1,2}\w') {
            throw "Unexpected argument '$token'. Options must be named, e.g. -SkipSharedRuntime."
        }
        $name = $token -replace '^-{1,2}', ''
        $next = if ($i + 1 -lt $Tokens.Count) { $Tokens[$i + 1] } else { $null }
        if ($null -ne $next -and $next -notmatch '^-{1,2}\w') {
            $splat[$name] = $next
            $i++
        } else {
            $splat[$name] = $true
        }
    }
    return $splat
}

function Copy-ToInstalls {
    param(
        [hashtable]$Entry,
        [string]$Name,
        [datetime]$Since
    )

    $folders = Get-DistFolders -Entry $Entry
    if (-not $folders -or $folders.Count -eq 0) { return }

    # Only what THIS run produced. A dist folder keeps older versions around
    # (Radio's still holds the 2.2.0 set), and copying those would quietly
    # refill \installs with builds nobody asked for.
    $fresh = @()
    foreach ($folder in $folders) {
        $full = Join-Path $RepoRoot $folder
        if (-not (Test-Path $full)) { continue }
        $fresh += Get-ChildItem -Path $full -File |
            Where-Object { $_.Extension -in '.exe', '.zip' -and $_.LastWriteTime -ge $Since }
    }
    if ($fresh.Count -eq 0) {
        Write-Host "    copy:   nothing new to copy from $($folders -join ', ')"
        return
    }

    if (-not (Test-Path $InstallsDir)) {
        New-Item -ItemType Directory -Path $InstallsDir -Force | Out-Null
    }
    foreach ($file in $fresh) {
        Copy-Item -Path $file.FullName -Destination $InstallsDir -Force
        Write-Host ('    copy:   {0} ({1:N1} MB) -> {2}' -f $file.Name, ($file.Length / 1MB), $InstallsDir)
    }
}

function Invoke-Product {
    param([string]$Name)

    $resolved = Resolve-BuildScript -Name $Name
    $entry = $resolved.Entry
    $path = $resolved.Path

    $stamp = Get-Date -Format 'yyyy-MM-dd-HHmmss'
    $logDir = Join-Path $RepoRoot 'local\build-logs'
    if (-not $NoLog -and -not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $log = Join-Path $logDir "$Name-$stamp.log"

    $passthrough = @()
    if ($Rest) { $passthrough += $Rest }

    Write-Host ''
    Write-Host "=== $Name -- $($entry.Desc)"
    Write-Host "    script: $path"
    if (-not $NoLog) { Write-Host "    log:    $log" }
    $started = Get-Date

    Push-Location $RepoRoot
    try {
        if ($entry.Kind -eq 'python') {
            # The Python build has no -Sign switch; code_signing.py reads the
            # same intent from QUILL_SIGN, which is how every other build sets it.
            if ($Sign) { $env:QUILL_SIGN = '1' }
            . (Join-Path $RepoRoot 'scripts\BuildEnv.ps1')
            $python = Resolve-QuillPython -QuillRepo $RepoRoot
            $argv = @($path) + $entry.Args + $passthrough
            if ($NoLog) {
                & $python @argv
            } else {
                & $python @argv 2>&1 | Tee-Object -FilePath $log
            }
            if ($LASTEXITCODE -ne 0) { throw "$Name build failed (exit $LASTEXITCODE)." }
        } else {
            # Hashtable splat, not an array: see ConvertTo-ParameterSplat.
            $splat = ConvertTo-ParameterSplat -Tokens $passthrough
            if ($Sign) { $splat['Sign'] = $true }
            # The build scripts all use $ErrorActionPreference = 'Stop' and
            # throw on failure, so a failure surfaces as a terminating error.
            if ($NoLog) {
                & $path @splat
            } else {
                & $path @splat 2>&1 | Tee-Object -FilePath $log
            }
        }
        if (-not $NoCopy) {
            # Inside the Push-Location, so the drive-letter-free \installs
            # resolves against the drive the checkout is on.
            Copy-ToInstalls -Entry $entry -Name $Name -Since $started
        }
    } finally {
        Pop-Location
    }

    $elapsed = (Get-Date) - $started
    Write-Host ('=== {0} OK in {1:hh\:mm\:ss}' -f $Name, $elapsed)
}

if ($Product -eq 'list') {
    Show-ProductList
    return
}

$targets = if ($Product -eq 'all') { $AllOrder } else { @($Product) }

$failed = @()
foreach ($name in $targets) {
    try {
        Invoke-Product -Name $name
    } catch {
        # In "all" mode one bad product must not hide the other nine: collect
        # the failures, report them together, and exit non-zero.
        Write-Host "=== $name FAILED: $($_.Exception.Message)"
        $failed += $name
    }
}

Write-Host ''
if ($failed.Count -gt 0) {
    Write-Host "Failed: $($failed -join ', ')"
    Write-Host "Built:  $(($targets | Where-Object { $failed -notcontains $_ }) -join ', ')"
    exit 1
}
Write-Host "Built: $($targets -join ', ')"
