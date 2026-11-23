# Stages the tools every shared runtime carries into dist\QuillVilleRuntime\tools:
# the Copilot SDK runtime, the Codex app-server, Node.js, the language servers,
# ripgrep and the Practice Site's WordPress Playground (wp-playground-cli).
#
# build_runtime.ps1 runs this after PyInstaller, with -SkipInventoryCheck
# because it checks the inventory itself once the dist is complete. Run on its
# own, it brings an existing runtime up to date without a full rebuild. That
# matters whenever this tool list grows: a runtime built before the Practice
# Site was bundled (2026-11-15, #1837) has no tools\wp-playground-cli, and the
# runtime-inventory gate fails on it until the tools are restaged or the
# runtime is rebuilt.
#
# Every tool comes from the pinned, verified build\deps cache
# (scripts\fetch_build_deps.py), never from PATH. A component already complete
# in the cache is not fetched again.
#
# Usage:
#   .\stage_runtime_tools.ps1 [-Python <python.exe>] [-QuillRepo <checkout>] [-RuntimeDist <dist>]

param(
    [string]$Python = "",
    [string]$QuillRepo = "",
    [string]$RuntimeDist = "",
    [switch]$SkipInventoryCheck
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\..\scripts\BuildEnv.ps1")
$QuillRepo = Resolve-QuillRepo -Preferred $QuillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $QuillRepo
if (-not $RuntimeDist) {
    $RuntimeDist = Join-Path $QuillRepo "standalone\runtime\dist\QuillVilleRuntime"
}

# The tools, in the order they stage. Each is a fetch_build_deps.py component
# and a folder under the runtime's tools\ directory; runtime-inventory.json
# declares the same names under "tools".
$tools = @("copilot", "codex", "nodejs", "language-servers", "ripgrep", "wp-playground-cli")
$fetchArgs = @()
foreach ($tool in $tools) { $fetchArgs += @("--only", $tool) }
& $Python (Join-Path $QuillRepo "scripts\fetch_build_deps.py") @fetchArgs
if ($LASTEXITCODE -ne 0) { throw "Could not stage the runtime tools (see scripts/fetch_build_deps.py)." }

$deps = Join-Path $QuillRepo "build\deps"
. (Join-Path $QuillRepo "scripts\StageMediaTools.ps1")
Stage-QuillMediaTools -RuntimeDist $RuntimeDist `
    -CopilotDir (Join-Path $deps "copilot") `
    -CodexDir (Join-Path $deps "codex") `
    -NodeDir (Join-Path $deps "nodejs") `
    -LanguageServersDir (Join-Path $deps "language-servers") `
    -RipgrepDir (Join-Path $deps "ripgrep") `
    -WpPlaygroundDir (Join-Path $deps "wp-playground-cli")

if ($SkipInventoryCheck) { return }
& $Python (Join-Path $QuillRepo "scripts\check_runtime_inventory.py") $RuntimeDist
if ($LASTEXITCODE -ne 0) { throw "Runtime inventory drift -- see above." }
Write-Host "Runtime tools staged: $RuntimeDist"
