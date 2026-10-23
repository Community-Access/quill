# Building the QUILL Windows family

Run these commands in PowerShell from the repository root on Windows. They build unsigned local artifacts; they do not publish a release. Use a clean checkout at the commit you want to ship. Inno Setup 7, Pandoc 3.10, and Python 3.14 are required. The build scripts check the Python environment and the shared runtime before packaging.

QUILL Lite is an editor app in its own right. The **Lite installer edition** and **Companion ZIP edition** of other apps are retired. The Windows release set is a full installer and a portable ZIP for each app.

## The one-command way

`build-quill-apps.ps1` at the repository root runs steps 2 to 5 below for the
apps you name, in this order, with a log per step and plain-text progress
("Step 3 of 6: QUILL Cast") that reads well with a screen reader. It rebuilds
the shared runtime first, runs the joint-release sibling version check once,
passes each app the build number its source declares, and collects every new
installer and portable zip into one upload folder with a zip per app, an
everything zip and `SHA256SUMS.txt`, under `dist/release-builds/<date-time>/`.
Builds are unsigned unless you pass `-Sign`; nothing is published.

**A build for distribution needs `-Release`.** Without it the script makes a
local dev build: every app is passed `-SkipPublishedCheck`, so none of them
checks its version and build number against the releases already published.
With `-Release` each app keeps that gate (it needs the network). The script
builds with the system Python 3.14 (`py -3.14`) unless you pass `-Python`; a
repository `.venv` is never used unasked, because releases build with the
system interpreter.

```powershell
.\build-quill-apps.ps1 all -Release -KeepGoing   # a distribution build of everything
.\build-quill-apps.ps1 lite,cast,radio,transcribe
.\build-quill-apps.ps1 transcribe -DryRun        # print the commands, build nothing
Get-Help .\build-quill-apps.ps1 -Detailed        # every option
```

App names: `quill` (QUILL for All), `lite`, `inkwell`, `weather`, `beacon`,
`social`, `converter`, `studio`, `cast`, `radio`, `transcribe`, or `all`. Step 1
below (installing the build environment) is still yours to do once.

## 1. Prepare the build environment

```powershell
$ErrorActionPreference = 'Stop'
$python = py -3.14 -c 'import sys; print(sys.executable)'
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe'
if (-not (Test-Path -LiteralPath $iscc)) { throw 'Install Inno Setup 7 or set $iscc to its ISCC.exe.' }
& $python -m pip install --find-links vendor/wheels -e '.[runtime,packaging,dev]'
& $python scripts/check_build_env.py --groups runtime,packaging --python $python
& $python scripts/fetch_build_deps.py
```

### Before a distribution build: confirm everything is ready

These checks build nothing, and each takes seconds to a few minutes. Run them on
the commit you mean to ship; every one should pass. They were last run in full
on 2026-10-23, on `main`, and all passed.

```powershell
# Every Python package any app's build installs, in the system interpreter.
& $python scripts/check_build_env.py --python $python `
    --groups runtime,packaging,dev,ui,speech,youtube,windows-media,live-dictation,office-text,ocr,docx,mp3,nemotron
& $python -m pip check                             # "No broken requirements found."
# The pinned binaries (ffmpeg, libmpv, deno, piper), the built-in speech
# models and the updater's bootstrappers, each checksum-verified.
& $python scripts/fetch_build_deps.py
& $python scripts/fetch_dictation_models.py --check
& $python scripts/fetch_bootstrappers.py --verify-only
# Versions: one QUILL version everywhere, siblings not ahead of their releases.
& $python -m quill.tools.check_version_consistency
& $python scripts/check_sibling_versions.py --releasing quilllite --releasing inkwell `
    --releasing weather --releasing beacon --releasing social --releasing converter `
    --releasing studio --releasing cast --releasing radio --releasing transcribe
# Every gate, then the whole plan without building anything.
& $python -m quill.tools.platform_report
.\build-quill-apps.ps1 all -Release -DryRun
```

The published-version gate, which `-Release` keeps, refuses a build number the
app's source does not declare. Each app's source says which build it is
(`_BUILD`, or `APP_BUILD`), and the script passes that number, so a version
shipping for the first time ships as the build its source names, not build 1.

Pandoc 3.10 or later renders the documents. A newer Pandoc than the one that
rendered the tree changes only the stylesheet in each page's head; re-render a
document when its text changes, not to update that line.

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

If the runtime inventory gate reports drift, inspect each named package against `pyproject.toml`. Rebaseline with `scripts/check_runtime_inventory.py standalone/runtime/dist/QuillVilleRuntime --write` only for an intentional package change, then rerun `build_runtime.ps1` so every remaining gate completes. On the first runtime build after 2026-10-17, expect the gate to report `lxml` with an explanation, because the runtime now ships Word support. Follow *Rebaselining after the Word support change* in section 5.

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
& .\standalone\transcribe\scripts\build_release.ps1 -Python $python -Iscc $iscc -SkipSharedRuntime
```

Each sibling places its installer and portable ZIP in `standalone/<app>/dist/`. Use `-Sign` only for an approved signed release with signing credentials configured. The build scripts derive the app version and Windows build number; do not rename an artifact to imply a different version. For local unpublished Dev builds, Radio, Cast, QUILL Lite, Converter, Weather and Transcribe accept `-SkipPublishedCheck`. Production releases must retain the published-version gate.

## 5. Verify the artifacts

```powershell
$apps = 'quilllite','inkwell','weather','beacon','social','converter','studio','cast','radio','transcribe'
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

### QUILL Lite portable: the PDF reader and OCR (first build after 2026-10-17)

The QUILL Lite portable ZIP now installs two more dependency groups, `office-text` (pdfplumber, which brings pdfminer.six and pypdfium2, plus pypdf and openpyxl) and `ocr` (the `winrt` Windows.Media.Ocr projection), so a portable copy opens PDFs and reads scanned pages the way the installed copy always has. Two things happen on the first build after this change, and both are expected:

1. **The inventory gate stops the build.** `build_portable.py` step 8 compares the bundle with `standalone/quilllite/portable-inventory.json` and reports `unexpected in site-packages:` for the new packages (`pdfplumber`, `pdfminer`, `pypdf`, `pypdfium2`, `pypdfium2_raw`, `openpyxl`, `et_xmlfile`, `winrt` and their `*.dist-info` names). Check the list holds only those and nothing swept from the build machine, then rebaseline from the real bundle and run the release script again:

   ```powershell
   & $python scripts\check_runtime_inventory.py standalone\quilllite\dist\QuillLite --layout portable --manifest standalone\quilllite\portable-inventory.json --write
   ```

   Never hand-edit `portable-inventory.json`; it is only correct when written from a build.
2. **The import check is stricter.** Step 8 now imports `pdfplumber`, `pypdf`, `pypdfium2`, `winrt.windows.media.ocr`, `winrt.windows.graphics.imaging`, `quill.io.pdf` and `quill.io.docconvert` inside the bundle and fails the build if any of them cannot load, so a build that installed the groups but cannot use them does not ship.

After the build, verify by hand on a computer without QUILL installed: unzip the portable ZIP, start `QuillLite.exe`, open a text PDF with Ctrl+O (it opens with its pages, not "This copy of QUILL Lite has no PDF reader"), open a scanned PDF and answer Yes (Windows OCR reads it), and use File > Import / Convert Document on a picture of printed text. Note the ZIP's new size beside the old one (299,961,055 bytes for 1.1.2); expect roughly 25 MB more unpacked. The checks are also in `docs/qa/screen-reader-checks-2026-10.md`.

### Rebaselining after the Word support change (first runtime build after 2026-10-17)

Jeff's decision on 2026-10-17 was to make Word documents fully usable in QUILL and QUILL Lite, whatever the size. Until then the shared runtime spec (`standalone/runtime/quillville-runtime.spec`) listed `lxml` in its `excludes`. python-docx is pure Python, so it still froze into the runtime, but it raised the moment it imported lxml. As a result, every *installed* copy of QUILL and QUILL Lite opened a `.docx` as plain text and could not save a real Word document. The GLOW Word, PDF and PowerPoint audits failed too, because every GLOW auditor imports python-docx. Portable copies were fine, because pip installs lxml with python-docx.

The spec no longer excludes lxml. It also names the Word stack (`lxml`, `docx`, `pptx`, `openpyxl` and every `acb_large_print` module) as hidden imports, so the Word path no longer depends on which optional imports the tracer happens to follow. Expect three things on the first runtime build after this change.

1. **The runtime inventory gate stops the build, and says why.** `check_runtime_inventory.py` reports:

   ```text
     unexpected in _internal: lxml
         expected: lxml was removed from the runtime spec's excludes on 2026-10-17 so python-docx can import ...
   ```

   That reason comes from `KNOWN_ADDITIONS` in the gate. The only new top-level entry should be `lxml`, the folder holding lxml's compiled `.pyd` files. If the gate names anything else as unexpected, treat it as ordinary drift and investigate it before you continue: do not rebaseline it away.
2. **Prove Word works before you rebaseline.** Run the import gate by hand against the dist the build just made:

   ```powershell
   & $python scripts\check_runtime_imports.py standalone\runtime\dist\QuillVilleRuntime
   ```

   It must end with `Runtime import gate: N modules checked, all correct.` Since this change it imports `lxml.etree`, `docx`, `pptx`, `openpyxl`, QUILL's Word reader and writer, `quill.core.docx_open`, `quill_glow_core` and the four GLOW auditors. It then runs `quill.io.word_selfcheck` inside the frozen runtime: that writes a real `.docx` (a heading, a bold word and a table), opens it the way both editors do, saves it back to Word and reads the result. Any failure prints "Word support is broken in this runtime" along with the fix.
3. **Rebaseline, then rebuild so every remaining gate runs.**

   ```powershell
   & $python scripts\check_runtime_inventory.py standalone\runtime\dist\QuillVilleRuntime --write
   git diff standalone\runtime\runtime-inventory.json   # should add "lxml" to _internal and nothing else
   & .\standalone\runtime\build_runtime.ps1 -Python $python
   ```

   Commit the regenerated `runtime-inventory.json`. In the same commit, delete the `"lxml"` entry from `KNOWN_ADDITIONS` in `scripts/check_runtime_inventory.py`, because once the inventory lists lxml the explanation is no longer needed. Never hand-edit `runtime-inventory.json`: it is only correct when it is written from a build.

The portable builds need no rebaseline for this change. Every portable already carries python-docx and lxml as base dependencies, and the QUILL Lite, Radio and Converter portable inventories already list `lxml`. The QUILL Lite product in `build_portable.py` now names the `docx` group as well, which adds no package, and its step-8 check (`check_word=True`) runs the same Word round trip. If that check fails, the portable build stops with "Bundled runtime failed the import check ... the Word open-and-save round trip". The `quill` product gains the `docx` and `office-text` groups; it has no committed inventory, so it only prints how to adopt one. QUILL for All's own builder (`scripts/build_windows_distribution.py`) runs the same check after it prunes the embedded runtime (`_check_word_support`) and stops with "Word support check failed in the embedded runtime" if Word would fall back to text.

**Check by hand after the build.** On a computer where QUILL and QUILL Lite are *installed* from the new installers (not portable), do the following:

1. Open a `.docx` in QUILL Lite with Ctrl+O. You should hear "Opened as Rich Text. Headings and bold are shown formatted.", not a text version of the file.
2. Type a line, then press Ctrl+S. You should hear "Saved", and the file should open in Word with its headings intact.
3. Do the same in QUILL.
4. Run a GLOW audit on a Word file and on a PDF in QUILL.

Then repeat steps 1 to 3 from both portable ZIPs. These checks are also listed in `docs/qa/screen-reader-checks-2026-10.md`. The runtime grows by a few megabytes, the size of lxml's compiled parser.

The app directories `standalone/player/`, `standalone/radio-mac/`, and `standalone/weather-ios/` have no Windows `build_release.ps1` target. Build and test the macOS and iOS projects on their respective platform toolchains.
