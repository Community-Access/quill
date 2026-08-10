# Shared doc-rendering helpers, dot-sourced by every standalone app's
# scripts\render_docs.ps1: Pandoc resolution and reproducible EPUB metadata.
# The Python equivalents live in scripts\release_readiness.py; keep them in
# step.
#
# Why this exists: the render scripts used to take whatever `Get-Command pandoc`
# handed back, which is the first match on PATH -- and PATH order is not a
# version order. A machine with an old per-machine install under
# "C:\Program Files\Pandoc" and a newer per-user one under
# "%LOCALAPPDATA%\Pandoc" silently renders with the old one, because Windows
# composes PATH as machine entries first and user entries after. Uninstalling
# the old copy needs admin rights that a developer may not have, so the scripts
# resolve the interpreter themselves instead of relying on PATH ordering.

# Deliberately no Set-StrictMode here: this file is dot-sourced, so any mode it
# sets would leak into the calling script's scope and change how unrelated code
# behaves.

# The repo bundles Pandoc 3.10 (see MIRRORED_PANDOC_URL in
# scripts\build_windows_distribution.py) and every committed .html/.epub was
# rendered with it. Older releases stamp a different generator string and
# differ in typography, so rendering with one produces artifact churn that the
# docs parity gate then reports as a spurious diff. Fail fast instead.
$script:QuillMinimumPandoc = [version]"3.10"

function Get-PandocVersion {
    <#
    .SYNOPSIS
        The version an executable reports, or $null if it is not usable Pandoc.
    #>
    param([Parameter(Mandatory)][string]$Path)

    try {
        $first = & $Path --version 2>$null | Select-Object -First 1
    } catch {
        return $null
    }
    if (-not $first) { return $null }
    # "pandoc 3.10.1" / "pandoc.exe 3.9.0.2"
    if ($first -notmatch '(\d+(?:\.\d+)+)') { return $null }
    try { return [version]$Matches[1] } catch { return $null }
}

function Resolve-Pandoc {
    <#
    .SYNOPSIS
        The path to the newest usable Pandoc, independent of PATH ordering.
    .DESCRIPTION
        Honours $env:QUILL_PANDOC as an explicit override. Otherwise it
        collects every candidate on PATH plus the standard per-user and
        per-machine install locations, and returns the highest version that
        meets the minimum. Throws with an actionable message if none does.
    #>
    [CmdletBinding()]
    param([version]$Minimum = $script:QuillMinimumPandoc)

    if ($env:QUILL_PANDOC) {
        $override = $env:QUILL_PANDOC
        if (-not (Test-Path -LiteralPath $override -PathType Leaf)) {
            throw "QUILL_PANDOC points at '$override', which is not a file."
        }
        $overrideVersion = Get-PandocVersion -Path $override
        if (-not $overrideVersion) {
            throw "QUILL_PANDOC points at '$override', which did not report a Pandoc version."
        }
        if ($overrideVersion -lt $Minimum) {
            throw "QUILL_PANDOC points at Pandoc $overrideVersion, but $Minimum or newer is required."
        }
        Write-Host "Using Pandoc $overrideVersion from QUILL_PANDOC ($override)"
        return $override
    }

    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($command in @(Get-Command pandoc -All -ErrorAction SilentlyContinue)) {
        if ($command.Source) { $candidates.Add($command.Source) }
    }
    foreach ($root in @($env:LOCALAPPDATA, ${env:ProgramFiles}, ${env:ProgramFiles(x86)})) {
        if ($root) { $candidates.Add((Join-Path $root "Pandoc\pandoc.exe")) }
    }

    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $found = @()
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $full = (Resolve-Path -LiteralPath $candidate).Path
        if (-not $seen.Add($full)) { continue }
        $version = Get-PandocVersion -Path $full
        if ($version) { $found += [pscustomobject]@{ Path = $full; Version = $version } }
    }

    if (-not $found) {
        throw "Pandoc is required to render docs. Install with: winget install --id JohnMacFarlane.Pandoc -e"
    }

    $best = $found | Sort-Object Version -Descending | Select-Object -First 1
    if ($best.Version -lt $Minimum) {
        $detail = ($found | ForEach-Object { "  $($_.Version)  $($_.Path)" }) -join [Environment]::NewLine
        throw @"
Pandoc $Minimum or newer is required to render docs; the newest found is $($best.Version).
Every committed .html/.epub was rendered with $Minimum, so an older release would
rewrite all of them with a different generator stamp and typography.

Found:
$detail

Upgrade with: winget install --id JohnMacFarlane.Pandoc -e
Or point QUILL_PANDOC at a suitable pandoc.exe.
"@
    }

    if ($found.Count -gt 1) {
        # PATH order is not version order, so say which one won -- this is
        # exactly the case that used to render silently with the wrong copy.
        Write-Host "Using Pandoc $($best.Version) ($($best.Path)); $($found.Count - 1) older copy/copies ignored"
    } else {
        Write-Host "Using Pandoc $($best.Version) ($($best.Path))"
    }
    return $best.Path
}

# --- Reproducible EPUB metadata -------------------------------------------
#
# Pandoc stamps a fresh random UUID into dc:identifier and the current wall
# clock into dcterms:modified on every EPUB build, so re-rendering an
# unchanged document still produces different bytes. That made all 165
# committed .epub files show as modified on every run, and left the docs
# parity gate unable to distinguish a real content change from a no-op
# rebuild. Pinning both makes the output a pure function of the source.

# A fixed build epoch (2024-01-01T00:00:00Z), honoured by Pandoc via
# SOURCE_DATE_EPOCH. This is deliberately a constant rather than a real
# modification time: any per-run or per-checkout value reintroduces the churn.
$script:QuillSourceDateEpoch = "1704067200"

function Get-QuillEpubIdentifier {
    <#
    .SYNOPSIS
        A stable, URN-safe dc:identifier derived from a document's path.
    .DESCRIPTION
        Must be unique per document and identical across machines and runs, so
        it is derived from the repo-relative path rather than generated. Paths
        can contain spaces and mixed case (e.g. "docs/user guide/userguide.md"),
        so everything outside [a-z0-9] collapses to a single hyphen.
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRelativePath
    )

    $stem = $RepoRelativePath -replace '\.[^.\/]+$', ''
    $slug = ($stem -replace '[^A-Za-z0-9]+', '-').Trim('-').ToLowerInvariant()
    return "urn:quill:$slug"
}

function Invoke-WithSourceDateEpoch {
    <#
    .SYNOPSIS
        Runs a script block with SOURCE_DATE_EPOCH pinned, then restores it.
    .DESCRIPTION
        Scoped rather than set globally: render_docs.ps1 is called from
        build_release.ps1, and other tools in that build also honour
        SOURCE_DATE_EPOCH. Leaking it would silently change their output too.
    #>
    param(
        [Parameter(Mandatory)][scriptblock]$Body
    )

    $previous = $env:SOURCE_DATE_EPOCH
    $env:SOURCE_DATE_EPOCH = $script:QuillSourceDateEpoch
    try { & $Body } finally { $env:SOURCE_DATE_EPOCH = $previous }
}
