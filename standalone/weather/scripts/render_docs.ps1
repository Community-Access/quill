# Renders every docs\*.md to matching .html and .epub via Pandoc, mirroring
# the exact invocation QUILL's own scripts\release_readiness.py uses
# (gfm -> html5 -s, gfm -> epub3), so this repo's rendered docs are
# reproducible from source instead of hand-maintained alongside the
# markdown. build_release.ps1 calls this before staging the bundled docs\
# folder that the app's own Help menu opens.
#
# Usage: .\scripts\render_docs.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$docsDir = Join-Path $repoRoot "docs"

$pandoc = Get-Command pandoc -ErrorAction SilentlyContinue
if (-not $pandoc) {
    throw "Pandoc is required to render docs. Install with: winget install --id JohnMacFarlane.Pandoc -e"
}

Get-ChildItem $docsDir -Filter "*.md" | ForEach-Object {
    $htmlOut = [System.IO.Path]::ChangeExtension($_.FullName, "html")
    $epubOut = [System.IO.Path]::ChangeExtension($_.FullName, "epub")
    Write-Host "Rendering $($_.Name) -> $(Split-Path -Leaf $htmlOut), $(Split-Path -Leaf $epubOut)"
    & $pandoc.Source $_.FullName -f gfm -t html5 -s -o $htmlOut
    if ($LASTEXITCODE -ne 0) { throw "Pandoc HTML render failed for $($_.Name)" }
    & $pandoc.Source $_.FullName -f gfm -t epub3 -o $epubOut
    if ($LASTEXITCODE -ne 0) { throw "Pandoc EPUB render failed for $($_.Name)" }
}
