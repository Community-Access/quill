# Building the QUILL Windows family

Run these commands in PowerShell from the repository root on Windows. They build unsigned local artifacts; they do not publish a release. Use a clean checkout at the commit you want to ship. Inno Setup 7, Pandoc 3.10, and Python 3.13 are required. The build scripts check the Python environment and the shared runtime before packaging.

QUILL Lite is an editor app in its own right. The **Lite installer edition** and **Companion ZIP edition** of other apps are retired. The Windows release set is a full installer and a portable ZIP for each app.

## 1. Prepare the build environment

```powershell
$ErrorActionPreference = 'Stop'
$python = py -3.13 -c 'import sys; print(sys.executable)'
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe'
if (-not (Test-Path -LiteralPath $iscc)) { throw 'Install Inno Setup 7 or set $iscc to its ISCC.exe.' }
& $python -m pip install --find-links vendor/wheels -e '.[runtime,packaging,dev]'
& $python scripts/check_build_env.py --groups runtime,packaging --python $python
& $python scripts/fetch_build_deps.py
```

The shared runtime requires a Podcast Index key and secret. Set `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET`, set their `_FILE` counterparts to files containing the values, or retain an existing ignored `quill/_podcast_index_key.py` from a prior build. The key file must never be committed. The build stops if neither source supplies a pair.

GitHub's `dev-builds` workflow also requires repository secrets named `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET`. The workflow passes them only to the sibling build step. Without them, the shared runtime correctly refuses to package a broken podcast directory integration.

## 2. Check the source, then build the shared runtime

```powershell
& $python -m pytest -q
& $python -m ruff check .
& $python -m ruff format --check .
& .\standalone\runtime\build_runtime.ps1 -Python $python
```

The runtime must be built **before** the sibling installers. It carries the shared `quill` package and all sibling app modules. Its output is `standalone/runtime/dist/QuillVilleRuntime/`.

If the runtime inventory gate reports drift, inspect each named package against `pyproject.toml`. Rebaseline with `scripts/check_runtime_inventory.py standalone/runtime/dist/QuillVilleRuntime --write` only for an intentional package change, then rerun `build_runtime.ps1` so every remaining gate completes.

## 3. Build QUILL for All

```powershell
& $python scripts/build_windows_distribution.py --bundle-python --compile-installer --iscc-path $iscc --output-dir dist/windows
```

The full installer is in `dist/windows/installer/Output/`; the portable folder is `dist/windows/portable/`. QUILL uses its own distribution builder rather than a `standalone/*/scripts/build_release.ps1` script.

## 4. Build the Windows sibling apps, in order

Builds are sequential because their installer scripts share `standalone/runtime/dist/QuillVilleRuntime/` as a staging area. Media apps add or remove ffmpeg and mpv there according to what each installer needs. Do not run sibling release scripts in parallel in the same checkout. Pass the same `$python` to every script so the release environment check sees the packages installed in step 1.

```powershell
& .\standalone\quilllite\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
& .\standalone\inkwell\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
& .\standalone\weather\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
& .\standalone\beacon\scripts\build_release.ps1 -Python $python -Iscc $iscc
& .\standalone\social\scripts\build_release.ps1 -Python $python -Iscc $iscc
& .\standalone\converter\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
& .\standalone\studio\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
& .\standalone\cast\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
& .\standalone\radio\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
```

Each sibling places its installer and portable ZIP in `standalone/<app>/dist/`. Use `-Sign` only for an approved signed release with signing credentials configured. The build scripts derive the app version and Windows build number; do not rename an artifact to imply a different version. For local unpublished Dev builds, Radio, Cast, QUILL Lite, and Converter accept `-SkipPublishedCheck`. Production releases must retain the published-version gate.

## 5. Verify the artifacts

```powershell
$apps = 'quilllite','inkwell','weather','beacon','social','converter','studio','cast','radio'
foreach ($app in $apps) {
    $files = Get-ChildItem -LiteralPath "standalone/$app/dist" -File |
        Where-Object { $_.Extension -in '.exe','.zip' -and $_.Name -notmatch '(?i)(-Lite-Setup-|Companion)' }
    if (($files | Where-Object Extension -eq '.exe').Count -lt 1 -or
        ($files | Where-Object Extension -eq '.zip').Count -lt 1) {
        throw "Missing full installer or portable ZIP for $app"
    }
    $files | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash
}
if (-not (Get-ChildItem 'dist/windows/installer/Output/Quill-for-All-Setup-*.exe' -File)) {
    throw 'Missing QUILL for All installer'
}
```

The app directories `standalone/player/`, `standalone/radio-mac/`, and `standalone/weather-ios/` have no Windows `build_release.ps1` target. Build and test the macOS and iOS projects on their respective platform toolchains.
