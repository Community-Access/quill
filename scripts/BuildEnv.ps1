# Shared build-environment resolution for every standalone app's
# scripts\build_release.ps1 and for standalone\runtime\build_runtime.ps1.
#
# WHY THIS EXISTS
# Each build script used to hardcode its own absolute defaults -- "S:\QUILL",
# "S:\QUILL\.venv\Scripts\python.exe", "S:\token.txt" (and Studio had the same
# three on D:\). That made every script runnable on exactly one machine, on
# exactly one drive letter: a clone anywhere else failed either instantly ("Python
# at 'S:\QUILL\...' is not runnable") or, worse, several minutes in with a
# misleading error. Radio and Weather had already grown a private copy of the
# correct resolution logic; this file is that logic extracted once so the other
# five scripts stop drifting from it.
#
# HISTORICAL NOTE (2026-08-17): "S:" and "D:" in old logs are the SAME machine.
# The primary checkout's drive was re-lettered S: -> D:, which is why stale
# .pyc tracebacks can print S:\QUILL paths and why S:\installs deletions sit in
# D:'s recycle bin. The checkout's broken .venv (Python 3.13.11; PyInstaller
# crashed on malformed metadata; the "stale venv silently changed what
# shipped" hazard Resolve-QuillPython exists to avoid) was deleted the same
# day. Release builds use the newest system CPython -- never a checkout venv.
#
# Dot-source it from a build script:
#   . (Join-Path $quillRepo "scripts\BuildEnv.ps1")
# following the same pattern render_docs.ps1 uses for scripts\DocRender.ps1.
#
# Nothing here resolves a path from a drive letter. Everything is derived from
# this file's own location on disk, so the checkout builds from D:\, S:\, a UNC
# share, or a temp clone with no arguments at all.

Set-StrictMode -Version Latest

# The QUILL checkout root, derived from THIS file (scripts\BuildEnv.ps1 -> repo
# root). $PSScriptRoot inside a dot-sourced file is the *sourcing* script's
# directory, so use $PSCommandPath, which always names this file.
$script:QuillBuildEnvRoot = [System.IO.Path]::GetFullPath(
    (Join-Path (Split-Path -Parent $PSCommandPath) ".."))

function Resolve-QuillRepo {
    <#
    .SYNOPSIS
    Resolve the QUILL checkout root, drive-letter independent.
    .PARAMETER Preferred
    An explicit -QuillRepo value from the caller; wins when it is a real checkout.
    #>
    param([string]$Preferred = "")

    # An explicit value wins, but only if it really is a checkout -- a stale
    # hardcoded default that happens to exist as a directory must not silently
    # become the source tree we ship.
    if ($Preferred -and (Test-Path (Join-Path $Preferred "quill\__init__.py"))) {
        return [System.IO.Path]::GetFullPath($Preferred)
    }
    if ($Preferred) {
        Write-Host "Ignoring -QuillRepo '$Preferred' (not a QUILL checkout); resolving from this script's location."
    }
    if (Test-Path (Join-Path $script:QuillBuildEnvRoot "quill\__init__.py")) {
        return $script:QuillBuildEnvRoot
    }
    throw "QUILL checkout not found at '$script:QuillBuildEnvRoot' -- pass -QuillRepo <path>."
}

function Test-QuillPythonExe {
    <#
    .SYNOPSIS
    True only if this python.exe actually runs.
    .DESCRIPTION
    Existing on disk is not the same as runnable: a virtualenv whose base
    interpreter was moved or uninstalled still has a python.exe, and it dies with
    "did not find executable at ...". Preferring it blindly wedged builds several
    steps later with a misleading "Bundled feedback token generation failed", so
    prove the interpreter runs before committing to it.
    #>
    param([string]$Exe)

    if (-not $Exe -or -not (Test-Path $Exe)) { return $false }
    try {
        & $Exe -c "import sys" 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-QuillPythonVersion {
    <#
    .SYNOPSIS
    The [version] of an interpreter, or $null if it will not report one.
    #>
    param([string]$Exe)

    try {
        $raw = & $Exe -c "import sys;print('.'.join(map(str,sys.version_info[:3])))" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $raw) { return $null }
        return [version]($raw.Trim())
    } catch {
        return $null
    }
}

function Test-QuillPythonInstallable {
    <#
    .SYNOPSIS
    False for a PEP 668 "externally managed" interpreter.
    .DESCRIPTION
    A uv- or distro-managed CPython ships an EXTERNALLY-MANAGED marker in its
    stdlib and refuses `pip install` without --break-system-packages. These builds
    must be able to install the pyproject [runtime] closure into the interpreter
    they build with, so such an install is not a usable build target -- and it must
    not merely be *preferred and then fail*, which is what happened when this
    machine's newest system Python (a uv-managed 3.14.2 with no wxPython and no
    PyInstaller) sorted to the top of the candidate list.
    #>
    param([string]$Exe)

    try {
        $out = & $Exe -c "import os,sysconfig;print(os.path.exists(os.path.join(sysconfig.get_paths()['stdlib'],'EXTERNALLY-MANAGED')))" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $true }
        return ($out.Trim() -ne "True")
    } catch {
        return $true
    }
}

function Get-QuillSystemPythons {
    <#
    .SYNOPSIS
    Every usable system (non-virtualenv) CPython this machine can offer, newest first.
    .DESCRIPTION
    Sources, in order of trust: the `py` launcher's registered installs (PEP 514),
    then PATH. A virtualenv is never returned -- a venv has pyvenv.cfg beside the
    interpreter, and system Python is what these builds want. PEP 668
    externally-managed installs are also skipped; see Test-QuillPythonInstallable.
    #>
    $found = @()

    # The py launcher enumerates every properly registered install, including the
    # per-user Store/pythoncore layouts that are not on PATH.
    try {
        $listing = & py --list-paths 2>$null
        if ($LASTEXITCODE -eq 0 -and $listing) {
            foreach ($line in $listing) {
                # Lines look like: " -V:3.13 *        C:\...\python.exe"
                $m = [regex]::Match($line, '(?<path>[A-Za-z]:\\[^\s].*?python\.exe)\s*$')
                if ($m.Success) { $found += $m.Groups['path'].Value }
            }
        }
    } catch { }

    try {
        foreach ($cmd in @(Get-Command python -All -ErrorAction SilentlyContinue)) {
            if ($cmd.Source) { $found += $cmd.Source }
        }
    } catch { }

    $seen = @{}
    $result = @()
    foreach ($exe in $found) {
        $full = try { [System.IO.Path]::GetFullPath($exe) } catch { continue }
        if ($seen.ContainsKey($full.ToLowerInvariant())) { continue }
        $seen[$full.ToLowerInvariant()] = $true

        # Skip virtualenvs: "just use system python".
        if (Test-Path (Join-Path (Split-Path -Parent $full) "pyvenv.cfg")) { continue }
        if (-not (Test-QuillPythonExe $full)) { continue }
        if (-not (Test-QuillPythonInstallable $full)) { continue }
        $ver = Get-QuillPythonVersion $full
        if (-not $ver) { continue }
        $result += [pscustomobject]@{ Path = $full; Version = $ver }
    }
    return $result | Sort-Object -Property Version -Descending
}

function Resolve-QuillPython {
    <#
    .SYNOPSIS
    Pick the interpreter to build with. Never returns an unrunnable path.
    .DESCRIPTION
    Precedence:
      1. an explicit -Python from the caller (hard error if unrunnable -- an
         explicit request that cannot be honoured must not be silently replaced)
      2. $env:QUILL_BUILD_PYTHON
      3. the newest system CPython (py launcher, then PATH), at or above -Minimum
      4. the checkout's .venv, only as a last resort
    Step 3 before step 4 is deliberate: these release builds target system Python,
    and a stale .venv silently changed what shipped.
    .PARAMETER Minimum
    Lowest acceptable version; system interpreters below it are passed over.
    #>
    param(
        [string]$Preferred = "",
        [string]$QuillRepo = "",
        [version]$Minimum = [version]"3.12"
    )

    if ($Preferred) {
        if (-not (Test-QuillPythonExe $Preferred)) {
            throw "Python at '$Preferred' is not runnable -- pass a working -Python <python.exe>."
        }
        return [System.IO.Path]::GetFullPath($Preferred)
    }

    if ($env:QUILL_BUILD_PYTHON) {
        if (Test-QuillPythonExe $env:QUILL_BUILD_PYTHON) {
            Write-Host "Using QUILL_BUILD_PYTHON: $env:QUILL_BUILD_PYTHON"
            return [System.IO.Path]::GetFullPath($env:QUILL_BUILD_PYTHON)
        }
        Write-Host "Ignoring QUILL_BUILD_PYTHON='$env:QUILL_BUILD_PYTHON' (not runnable)."
    }

    $candidates = @(Get-QuillSystemPythons)
    $usable = @($candidates | Where-Object { $_.Version -ge $Minimum })
    if ($usable.Count -gt 0) {
        $pick = $usable[0]
        $others = ($candidates | Where-Object { $_.Path -ne $pick.Path }).Count
        $suffix = if ($others -gt 0) { "; $others other system copy/copies ignored" } else { "" }
        Write-Host "Using system Python $($pick.Version) ($($pick.Path))$suffix"
        return $pick.Path
    }

    if ($QuillRepo) {
        $venv = Join-Path $QuillRepo ".venv\Scripts\python.exe"
        if (Test-QuillPythonExe $venv) {
            Write-Warning "No system Python >= $Minimum found; falling back to the checkout venv $venv."
            return [System.IO.Path]::GetFullPath($venv)
        }
    }
    throw "No usable Python >= $Minimum found -- pass -Python <python.exe> or set QUILL_BUILD_PYTHON."
}

function Resolve-QuillIscc {
    <#
    .SYNOPSIS
    Locate the Inno Setup compiler without hardcoding a drive.
    .DESCRIPTION
    Inno Setup 7 first, 6 as the fallback (2026-08-17): the 64-bit v7 compiler
    is what allows LZMADictionarySize above 64 MB, which the shared installers
    rely on to deduplicate ffmpeg/ffprobe (-27 MB on Quill Radio alone), and
    both editions compile the v6-era scripts unchanged. The two can coexist;
    pass -Iscc explicitly to build with a specific one.
    #>
    param([string]$Preferred = "")

    $tried = @()
    if ($Preferred) { $tried += $Preferred }
    $tried += @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($candidate in $tried) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    $onPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    throw "ISCC.exe not found (looked in $($tried -join '; ')) -- pass -Iscc <path>."
}

function Assert-QuillBuildEnv {
    <#
    .SYNOPSIS
    Fail early if the interpreter is missing declared build tools.
    .DESCRIPTION
    For the app builds that call PyInstaller directly (Cast, Social, Beacon,
    Studio) rather than going through build_runtime.ps1. Without this they fail
    on a bare "No module named PyInstaller" from deep inside the build, minutes
    after the docs have already been rendered.
    .PARAMETER Groups
    Comma-separated pyproject optional-dependency groups. Defaults to the build
    tools only -- an app build does not need the whole shipped [runtime] closure.
    #>
    param(
        [string]$Python,
        [string]$QuillRepo,
        [string]$Groups = "packaging"
    )

    $envCheck = Join-Path $QuillRepo "scripts\check_build_env.py"
    if (-not (Test-Path $envCheck)) {
        Write-Warning "Build-environment check not found at $envCheck; skipping."
        return
    }
    & $Python $envCheck --groups $Groups --python $Python
    if ($LASTEXITCODE -ne 0) {
        throw "Build environment does not match pyproject [$Groups] -- see above."
    }
}

function Resolve-QuillTokenFile {
    <#
    .SYNOPSIS
    Find the bundled-feedback-token file, if the builder has one.
    .DESCRIPTION
    Returns "" when nothing is found, which is correct: tools\generate_feedback_token.py
    resolves a token from four sources (env var, this file, Windows Credential
    Manager, or the token already bundled by the last build), so a missing file is
    not a missing token. The old hardcoded "S:\token.txt" default made Cast throw
    "a release build must embed the issues-only token" on every other machine even
    when a perfectly good token was already bundled.
    #>
    param([string]$Preferred = "")

    if ($Preferred) {
        if (-not (Test-Path $Preferred)) { throw "Token file not found: $Preferred." }
        return [System.IO.Path]::GetFullPath($Preferred)
    }
    if ($env:QUILL_FEEDBACK_TOKEN_FILE -and (Test-Path $env:QUILL_FEEDBACK_TOKEN_FILE)) {
        return [System.IO.Path]::GetFullPath($env:QUILL_FEEDBACK_TOKEN_FILE)
    }
    # A token.txt kept beside the checkout, or inside it, is the drive-agnostic
    # form of the old "S:\token.txt" habit -- a convenience, never a requirement.
    # Split-Path -Parent returns "" when the checkout IS a drive root (X:\), so
    # guard it rather than letting Join-Path throw on an empty Path.
    $parent = Split-Path -Parent $script:QuillBuildEnvRoot
    foreach ($dir in @($parent, $script:QuillBuildEnvRoot)) {
        if (-not $dir) { continue }
        $beside = Join-Path $dir "token.txt"
        if (Test-Path $beside) { return [System.IO.Path]::GetFullPath($beside) }
    }
    return ""
}
