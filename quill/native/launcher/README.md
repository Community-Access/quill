# QuillVille native launcher (C source)

> **For the design and rationale, read [`docs/design/native-launcher-2026-07-24.md`](../../../docs/design/native-launcher-2026-07-24.md).** This README is a 60-second orientation for someone landing in the directory and wondering what to do.

## What this is

A tiny, genuinely-compiled-from-C Windows / macOS / Linux launcher that
replaces the prior pattern of stamping a copy of `pythonw.exe` with
`rcedit` to make the user-facing exe.

The compiled launcher is **a process-spawn shim** — it does not embed
CPython. It:

1. Computes its own install root from its executable path.
2. Resolves a Python interpreter (private embedded runtime beside the
   launcher, including the legacy `pythonw.exe` fallback → shared QuillVille
   runtime). Private first since 2026-09-15: a bundle that ships its own
   interpreter is self-contained, and preferring the machine-wide runtime made
   every portable zip stop being portable — and crash outright when that
   runtime predated the app. See the "WHY PRIVATE FIRST" note in
   `runtime_resolve.c`.
3. Spawns the resolved interpreter with the right `-m quill.apps.<product>`
   argv and the `QUILL_APP_ROOT` / `QUILL_PORTABLE` env vars.
4. Forwards the exit code.

## Files

| File | Purpose |
| --- | --- |
| `launcher.c` | The launcher body. `wmain` on Windows, `main` on POSIX. |
| `runtime_resolve.c` | Path-walk + version-marker validation. The never-crash contract. |
| `runtime_resolve.h` | `QlRuntime` struct + the two public entry points. |
| `launch_report.c` / `.h` | The "it did not start" report: the launch log the child's stderr goes to, the words for a non-zero exit, and the archive-preview check. See "When the app does not start" below. |
| `product.h.in` | Per-product identity template. CMake substitutes the values at configure time. |
| `CMakeLists.txt` | Build script. One executable target per product, configured by `-DPRODUCT_NAME=…` etc. |

The same source compiles on Windows (MSVC), macOS (`clang`), and Linux
(`gcc`) — the only `#ifdef _WIN32` branches are
`GetModuleFileNameA` vs `readlink("/proc/self/exe")` and
`CreateProcessW` vs `fork/execv`.

## How to build

The launchers are not built by hand. The build wrapper is
[`scripts/build_native_launcher.py`](../../../scripts/build_native_launcher.py)
and it is invoked by the per-product build scripts:

```powershell
# Per-product (run from the per-product repo, e.g. standalone/radio):
python scripts/build_native_launcher.py --product radio --out dist\QuillRadio
python scripts/build_native_launcher.py --product weather --out dist\QuillWeather
python scripts/build_native_launcher.py --product studio --out dist\QuillAudioStudio

# Main QUILL (run from the quill repo root):
python scripts/build_native_launcher.py --product quill --out dist\windows\portable
```

The wrapper detects MSVC 2022 (the `BuildTools` edition first, then
Community / Professional / Enterprise), configures CMake with the
per-product identity, builds, and copies the resulting `<product>.exe`
to the requested `--out` directory.

**The build is best-effort by design.** If MSVC or cmake is missing
on the build machine, the wrapper prints a clear message and exits 0
with no exe produced. The caller falls back to the legacy
stamped-pythonw launcher so the release still ships. Once every
supported build machine has MSVC + cmake, the fallback is removed.

## Manual build (when you need to iterate on the C source)

```powershell
cd quill\native\launcher
mkdir build
cd build
cmake -G "Visual Studio 17 2022" -A x64 `
  -DPRODUCT_NAME=QuillRadio `
  -DPRODUCT_DISPLAY_NAME="Quill Radio" `
  -DPRODUCT_VERSION=2.2.0 `
  -DPRODUCT_PYTHON_MODULE=quill.apps.radio `
  -DPRODUCT_REPO=Community-Access/quill `
  -DPRODUCT_APP_ID=CommunityAccess.QuillRadio `
  -DPRODUCT_ICON=../../../standalone/radio/assets/quill-radio.ico `
  ..
cmake --build . --config Release
# Result: build/Release/QuillRadio.exe
```

## When the app does not start

Until 2026-09-28 the launcher waited for `pythonw.exe` and threw its exit
code away. `pythonw.exe` has no console, so a traceback at import time
went nowhere, and a DLL Windows refused to load ended the child before
Python ran, with no text at all. A portable Quill Radio that "just doesn't
return anything" was the first report. `launch_report.c` closes that gap:

- **Launch log.** Before the spawn, the launcher opens (truncating) a log
  and hands its inheritable handle to the child as stdout and stderr. The
  first line is the launcher's own header (product, version, interpreter,
  module). Portable copies (`<dir>\data` exists) log to
  `data\logs\launch.log`; installed ones to
  `%APPDATA%\Quill\logs\<PRODUCT_NAME>-launch.log`, beside `quill.log`;
  `%TEMP%` is the last resort. Opened with `FILE_SHARE_READ` only, so a
  second launcher (the single-instance hand-off) cannot truncate a running
  instance's log; it launches unlogged instead.
- **The dialog.** On a non-zero exit the launcher reads the log's last
  non-blank line and shows one `MessageBox`: "<App> did not start." (or
  "stopped unexpectedly." after `QL_STARTED_AFTER_MS`), the reason, the
  log's path, and the support address. NTSTATUS exits that leave no text
  (`0xC0000135` DLL not found, `0xC0000142`, `0xC000007B`, `0xC0000022`, the
  memory faults) are translated to words; a Python line is quoted with a
  hint for "No module named", "DLL load failed" and "Permission denied".
  Exit 0 stays silent: an ordinary close and the hand-off both exit 0.
- **Archive preview.** If the launcher's own path runs through an archive
  tool's scratch folder (`Temp<n>_<name>.zip`, `7zO<hex>`, `Rar$...`), the
  user pressed Enter on the exe *inside* the zip and only that file exists
  on disk. `fail_no_runtime` says so and walks through Extract All, instead
  of "this portable copy is incomplete".

**Rollout (2026-09-28).** The change is in the shared source, so every
product picks it up at its next launcher build; nothing per product is
needed in C. What each product still owes when it ships: a changelog entry
and a user-guide "If <App> does not start" section naming its own log file.
Done: Quill Radio (3.0.4), Quill Converter (1.0.0, unreleased at the time),
QUILL Lite (1.1.0 docs, ahead of its next build). Owed: QUILL, Cast, Weather, Audio Studio,
Player, Inkwell, Beacon.

## Tests

```powershell
pytest tests/unit/native/test_runtime_resolver.py -v
pytest tests/unit/native/test_launch_failure.py -v
pytest tests/unit/scripts/test_build_native_launcher.py -v
```

The first is a Python mirror of the C runtime resolver and exercises
the algorithm in isolation. The second mirrors `launch_report.c` the same
way and pins every constant and phrase to the C source. The third is the
per-product identity contract and the cross-product storage-mode allowlist
check.

## What this is NOT

- **Not a Python C-API host.** The launcher does not link `python313.dll`
  on Windows. It `exec`s a separate process that does.
- **Not a PyInstaller bootloader.** The PyInstaller bootloaders were the
  same repackaging pattern this launcher was designed to remove.
- **Not a code-signing tool.** Signtool is invoked by a follow-up `--sign`
  flag (a separate PR).
- **Not the source of truth for the marker file format.** The
  `quillville-runtime.json` shape is owned by
  [`quill/core/runtime_marker.py`](../../core/runtime_marker.py). The C
  side reads the marker; the Python side writes it. Update both.
