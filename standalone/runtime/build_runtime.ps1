# Builds the shared QuillVille Runtime onedir that every app reuses.
#
#   dist\QuillVilleRuntime\   the shared runtime (CPython + wxPython + quill +
#                             quill_social) and a quillville-runtime.json
#                             version marker.
#
# An app installer installs this once (installer\shared-runtime.iss skips it when
# a matching version is already present) and launches apps through it with
#   QuillVilleRuntime.exe -m <the app's module>.
#
# It does NOT stage ffmpeg/ffprobe/libmpv. It used to, and that put 304 MB --
# 41% of the runtime -- into every app that installs it, including the four that
# never touch media: Quill Weather's installer was 191 MB to read out a
# forecast. The media tools belong beside the runtime, not inside it (the
# 2026-07-20 runtime/component plan, S2), so the apps that declare them
# (quill.apps.radio: ffmpeg+mpv; podcasts and studio: ffmpeg) stage them into
# the shared runtime dist from their OWN build_release.ps1 -- the same pattern
# the OptiLab adapter already uses. An app that declares no components stages
# nothing and its installer is 304 MB smaller. Radio's offline promise is
# unchanged: its installer still carries the tools, so it plays the instant it
# finishes installing on a machine with no internet.
#
# Usage:
#   .\build_runtime.ps1 [-Python <python.exe>]
#
# -Python defaults to the newest installable system Python (see
# scripts\BuildEnv.ps1). It used to default to a literal
# "S:\QUILL\.venv\Scripts\python.exe", so a direct invocation worked on exactly
# one machine, on one drive letter.

param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$dist = Join-Path $repoRoot "dist\QuillVilleRuntime"

# standalone\runtime -> standalone -> the QUILL checkout root. Derived from this
# script's own location, so no drive letter is ever assumed.
$quillRepo = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "..\.."))
. (Join-Path $quillRepo "scripts\BuildEnv.ps1")
$quillRepo = Resolve-QuillRepo -Preferred $quillRepo
$Python = Resolve-QuillPython -Preferred $Python -QuillRepo $quillRepo

# -- the build environment must match the declared runtime manifest -----------
# quillville-runtime.spec builds with collect_all("quill"), so PyInstaller
# bundles whatever is importable in THIS interpreter's environment. A drifted
# virtualenv therefore changes what ships without changing a line of source, and
# the build still exits 0: one such drift shipped a runtime with no offline
# dictation and wxPython below the pin in [ui], and it was only caught by
# unpacking the installer and diffing it against a known-good one. Check the
# venv against pyproject's [runtime] group first -- it costs a second.
$envCheck = Join-Path $quillRepo "scripts\check_build_env.py"
if (Test-Path $envCheck) {
    # runtime = what the shared runtime ships; packaging = the build tools that
    # produce it. Checking only [runtime] let a missing PyInstaller through: the
    # gate passed, then PyInstaller failed seconds later with a bare import error.
    & $Python $envCheck --groups runtime,packaging --python $Python
    if ($LASTEXITCODE -ne 0) {
        throw "Build environment does not match pyproject [runtime, packaging] -- see above."
    }
} else {
    Write-Warning "Build-environment check not found at $envCheck; skipping."
}

# -- onedir build -------------------------------------------------------------
Push-Location $repoRoot
try {
    & $Python -m PyInstaller quillville-runtime.spec --noconfirm --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}
if (-not (Test-Path (Join-Path $dist "QuillVilleRuntime.exe"))) {
    throw "Runtime build did not produce QuillVilleRuntime.exe"
}

# -- prune dead weight PyInstaller can't drop via `excludes` -------------------
# pywin32 ships an IDE (Pythonwin\) and a compiled help file (PyWin32.chm) that
# collect_all bundles as data. Nothing in any QuillVille app opens either at
# runtime, so strip them (~17 MB) after the build. Also drop *.pdb debug symbols
# if any slipped in. Best-effort: absence is a no-op.
$internal = Join-Path $dist "_internal"
foreach ($dead in @("Pythonwin")) {
    $p = Join-Path $internal $dead
    if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "pruned $dead" }
}
Get-ChildItem $internal -Recurse -Include *.chm, *.pdb -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue }
# libx265 is the H.265 VIDEO encoder that ffmpeg's shared build links; these are
# audio/text apps, so ~22 MB of video encoder is dead weight. (Kept as a
# standalone DLL, so PyInstaller `excludes` can't drop it.)
Get-ChildItem $internal -Filter "libx265*.dll" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Force $_.FullName; Write-Host "pruned $($_.Name)" }

# pyenchant ships a slice of an MSYS2 bin\ as package DATA -- Tcl/Tk, a second
# CPython, GNU readline, the GCC support libraries, gettext's toolchain, and
# 34 MB of ICU -- so PyInstaller `excludes` cannot see it and every installer
# carried ~64 MB that nothing can call. The pruner computes libenchant's real
# PE import closure and keeps exactly that, so a future pyenchant wheel linked
# against different libraries still prunes correctly with no list to maintain.
# Dictionaries are untouched. Verified end-to-end: same check()/suggest()
# results before and after, en_GB/en_ZA still resolve.
& $Python (Join-Path $quillRepo "scripts\prune_enchant_payload.py") $dist
if ($LASTEXITCODE -ne 0) { throw "enchant payload prune failed (see above)." }


# -- stamp the version marker (installer's skip-if-present check reads this) ---
$pyver = (& $Python -c "import platform; print(platform.python_version())").Trim()
# A sortable UTC stamp, not a bare date: the installer's skip-if-present check
# compares this string, and two runtimes built on the SAME DAY are different
# payloads (they carry the whole quill package). With date-only ids the second
# build of a day looked identical to the first, so an update installed over it
# was skipped and the app kept running yesterday's code.
$build = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
& $Python -c "from pathlib import Path; from quill.core import runtime_marker as m; m.write_marker(Path(r'$dist'), python_version='$pyver', build_id='$build'); print('marker', m.read_marker(Path(r'$dist')))"

# -- the swept contents must match the declared inventory ---------------------
# check_build_env above guards the floor (everything [runtime] needs is
# importable); this guards the ceiling. Analysis follows every optional import,
# so an extra package on the build machine ships silently: the 2026-08-15
# installers carried 81.8 MB of undeclared payload (pymupdf, a second OpenBLAS,
# pydantic, curl_cffi...) and the only symptom was 31 MB of installer size.
# Runs once the dist is complete (pruned, marker stamped), so the inventory
# describes exactly what the runtime contributes to an installer. ffmpeg and
# mpv are declared "optional" rather than expected: the runtime never stages
# them now, and the media apps add them afterwards (scripts\StageMediaTools.ps1),
# so their presence and their absence are both correct here.
& $Python (Join-Path $quillRepo "scripts\check_runtime_inventory.py") $dist
if ($LASTEXITCODE -ne 0) {
    throw "Runtime inventory drift -- see above. Rebaseline (--write) only for intentional changes."
}

# -- the frozen modules must actually import ----------------------------------
# The inventory gate above compares NAMES. It cannot see a package that is
# present, resolves through find_spec, and raises the moment anything imports
# it -- which is how this runtime shipped three dead speech engines at once:
# vosk (its 26 MB libvosk.dll loads via cffi, which PyInstaller never saw, so
# only vosk's mingw support DLLs shipped), faster_whisper (needs `av`, an
# exclude) and kokoro_onnx (needs onnxruntime, an exclude). Each also SHADOWED
# the working on-demand engine pack, because FrozenImporter precedes PathFinder
# on sys.meta_path -- and is_vosk_available() asks find_spec, so QUILL reported
# all three as installed and never offered the pack. Every one of those builds
# exited 0. This runs the real bundle and asks it directly.
& $Python (Join-Path $quillRepo "scripts\check_runtime_imports.py") $dist
if ($LASTEXITCODE -ne 0) {
    throw "Runtime import gate failed -- see above."
}

Write-Host "Shared runtime ready: $dist (Python $pyver)"
