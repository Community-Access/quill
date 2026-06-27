<#
.SYNOPSIS
    Reset a machine to a "QUILL never installed" state for fresh-install testing.

.DESCRIPTION
    Stops any running QUILL process, then removes the per-user install
    directory and all user data so the next installer run behaves exactly
    like a first-time install. Verifies the machine is clean afterward.

    Locations removed:
      - %LOCALAPPDATA%\Programs\QUILL for All   (install dir, 0.7.0+)
      - %LOCALAPPDATA%\Programs\Quill           (install dir, 0.5.0/0.6.0 branding)
      - %ProgramFiles%\QUILL for All            (admin-elevated install, 0.7.0+)
      - %ProgramFiles%\Quill                    (admin-elevated install, 0.5.0/0.6.0)
      - %APPDATA%\Quill                          (settings, keymap, recovery, AI)
      - %LOCALAPPDATA%\Quill                     (caches, if present)

    The 0.5.0/0.6.0 installer used AppName "Quill" (dir "Quill"); 0.7.0+ uses
    "QUILL for All". Because all releases share the same Inno AppId, an upgrade
    reuses the original folder - so a clean reset for upgrade-path testing must
    cover BOTH names. The installer is per-user by default but allows elevating
    to an admin (Program Files) install via the privileges dialog, so those
    locations are cleaned too.

    WARNING: %APPDATA%\Quill holds your real settings and any per-user data.
    Deleting it is what makes the test a true fresh install. Use -Backup to
    copy it to your Desktop first, or back it up yourself before running.

.PARAMETER Force
    Skip the confirmation prompt and delete immediately.

.PARAMETER Backup
    Copy %APPDATA%\Quill to the Desktop (timestamped) before deleting.

.EXAMPLE
    .\clean-quill-install.ps1
    Prompts for confirmation, then cleans.

.EXAMPLE
    .\clean-quill-install.ps1 -Backup -Force
    Backs up settings to the Desktop and cleans without prompting.
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Backup
)

$ErrorActionPreference = 'Stop'

# Per-user install dirs (default). Both AppName variants across versions.
$installDirNew = Join-Path $env:LOCALAPPDATA 'Programs\QUILL for All'
$installDirOld = Join-Path $env:LOCALAPPDATA 'Programs\Quill'
# Admin-elevated install dirs (only if the user chose elevation in the dialog).
$pf = if ($env:ProgramFiles) { $env:ProgramFiles } else { 'C:\Program Files' }
$installPfNew = Join-Path $pf 'QUILL for All'
$installPfOld = Join-Path $pf 'Quill'
$installDirs = @($installDirNew, $installDirOld, $installPfNew, $installPfOld)

$dataRoaming = Join-Path $env:APPDATA 'Quill'
$dataLocal  = Join-Path $env:LOCALAPPDATA 'Quill'
$targets = @($installDirs + @($dataRoaming, $dataLocal))

function Write-State {
    param([string]$Label)
    Write-Host ""
    Write-Host "QUILL install state ($Label):"
    foreach ($t in $targets) {
        $exists = Test-Path -LiteralPath $t
        $mark = if ($exists) { 'PRESENT' } else { 'absent ' }
        Write-Host ("  [{0}] {1}" -f $mark, $t)
    }
}

Write-State -Label 'before'

# 1. Stop any running QUILL process (matched by install dir, either branding).
$procNames = @('quill', 'pythonw', 'python')
$installDirsLower = $installDirs | ForEach-Object { $_.ToLower() }
$running = Get-Process -Name $procNames -ErrorAction SilentlyContinue |
    Where-Object {
        try {
            $p = $_.Path
            $p -and ($installDirsLower | Where-Object { $p.ToLower().StartsWith($_) })
        } catch { $false }
    }
if ($running) {
    Write-Host ""
    Write-Host "Stopping running QUILL processes:"
    $running | ForEach-Object { Write-Host ("  PID {0}  {1}" -f $_.Id, $_.Path) }
    if (-not $Force) {
        $ans = Read-Host "Stop these processes? [y/N]"
        if ($ans -notmatch '^(y|yes)$') { Write-Host "Aborted."; exit 1 }
    }
    $running | Stop-Process -Force
    Start-Sleep -Milliseconds 500
}

# 2. Confirm before destructive removal.
$toRemove = $targets | Where-Object { Test-Path -LiteralPath $_ }
if (-not $toRemove) {
    Write-Host ""
    Write-Host "Nothing to remove - machine is already clean."
    Write-State -Label 'after'
    exit 0
}

if (-not $Force) {
    Write-Host ""
    Write-Host "About to permanently delete the folders marked PRESENT above."
    $ans = Read-Host "Type DELETE to proceed"
    if ($ans -ne 'DELETE') { Write-Host "Aborted. Nothing was deleted."; exit 1 }
}

# 2b. Run the Inno Setup uninstaller first if present, so the Add/Remove
#     Programs entry, registry keys, and Start Menu shortcuts are cleared
#     too (manual folder deletion alone leaves those orphaned).
foreach ($dir in $installDirs) {
    if (Test-Path -LiteralPath $dir) {
        $uninst = Get-ChildItem -LiteralPath $dir -Filter 'unins*.exe' -ErrorAction SilentlyContinue |
            Sort-Object Name | Select-Object -First 1
        if ($uninst) {
            Write-Host "Running uninstaller: $($uninst.FullName)"
            Start-Process -FilePath $uninst.FullName -ArgumentList '/VERYSILENT', '/NORESTART', '/SUPPRESSMSGBOXES' -Wait
            Start-Sleep -Milliseconds 500
        }
    }
}

# 3. Optional backup of user data.
if ($Backup -and (Test-Path -LiteralPath $dataRoaming)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dest = Join-Path ([Environment]::GetFolderPath('Desktop')) "Quill-data-backup-$stamp"
    Write-Host "Backing up $dataRoaming -> $dest"
    Copy-Item -LiteralPath $dataRoaming -Destination $dest -Recurse -Force
}

# 4. Remove.
foreach ($t in $toRemove) {
    Write-Host "Removing $t"
    Remove-Item -LiteralPath $t -Recurse -Force
}

# 5. Verify.
Write-State -Label 'after'

$stillThere = $targets | Where-Object { Test-Path -LiteralPath $_ }
if ($stillThere) {
    Write-Host ""
    Write-Host "WARNING: some paths could not be removed (open handle? permissions?):"
    $stillThere | ForEach-Object { Write-Host "  $_" }
    exit 2
}

Write-Host ""
Write-Host "Clean. The next installer run will behave as a first-time install."
exit 0
