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

# Resolve Pandoc by version rather than by PATH order -- see the header of
# scripts\Resolve-Pandoc.ps1 for why the first match on PATH is the wrong one
# on any machine that has more than one Pandoc installed.
$resolverPath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "..\..\scripts\Resolve-Pandoc.ps1"))
if (-not (Test-Path $resolverPath)) { throw "Pandoc resolver not found at $resolverPath." }
. $resolverPath
$pandocExe = Resolve-Pandoc

# Shared accessible HTML template (adds <html lang="en">, a descriptive
# <title>, a skip link, and a <main> landmark) lives in the top-level repo at
# docs/pandoc. It is required, not optional: Pandoc's default template drops
# the page language, the skip link, and the <main> landmark, and a warning here
# is too easy to miss in a build log, so a missing template fails the render.
$templatePath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "..\..\docs\pandoc\quill-accessible.html5"))
if (-not (Test-Path $templatePath)) {
    throw "Accessible pandoc template not found at $templatePath. Rendering without it drops <html lang>, the skip link, and the <main> landmark."
}
$htmlTemplateArgs = @("--template", $templatePath)

Get-ChildItem $docsDir -Filter "*.md" | ForEach-Object {
    $htmlOut = [System.IO.Path]::ChangeExtension($_.FullName, "html")
    $epubOut = [System.IO.Path]::ChangeExtension($_.FullName, "epub")
    Write-Host "Rendering $($_.Name) -> $(Split-Path -Leaf $htmlOut), $(Split-Path -Leaf $epubOut)"
    # A descriptive <title>/<h1> comes from the document's first Markdown H1
    # (falls back to the file name), so pages are never titled by bare filename.
    $h1 = Select-String -Path $_.FullName -Pattern '^#\s+(.+?)\s*$' | Select-Object -First 1
    $pageTitle = if ($h1) { $h1.Matches[0].Groups[1].Value } else { $_.BaseName }
    # +smart turns ASCII "--", "..." and straight quotes into real typography.
    # Without it Pandoc slugifies a literal "--" straight into the heading id
    # (quill-weather----product-requirements), changing every anchor on the page
    # and breaking existing deep links into these docs.
    & $pandocExe $_.FullName -f gfm+smart -t html5 -s @htmlTemplateArgs --metadata "pagetitle=$pageTitle" -o $htmlOut
    if ($LASTEXITCODE -ne 0) { throw "Pandoc HTML render failed for $($_.Name)" }
    & $pandocExe $_.FullName -f gfm+smart -t epub3 -o $epubOut
    if ($LASTEXITCODE -ne 0) { throw "Pandoc EPUB render failed for $($_.Name)" }
}
