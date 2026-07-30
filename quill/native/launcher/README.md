# QuillVille native launcher (C source)

> **For the design and rationale, read [`docs/design/native-launcher-2026-07-24.md`](../../../docs/design/native-launcher-2026-07-24.md).** This README is a 60-second orientation for someone landing in the directory and wondering what to do.

## What this is

A tiny, genuinely-compiled-from-C Windows / macOS / Linux launcher that
replaces the prior pattern of stamping a copy of `pythonw.exe` with
`rcedit` to make the user-facing exe.

The compiled launcher is **a process-spawn shim** — it does not embed
CPython. It:

1. Computes its own install root from its executable path.
2. Resolves a Python interpreter (shared QuillVille runtime → private
   embedded runtime → legacy `pythonw.exe` fallback).
3. Spawns the resolved interpreter with the right `-m quill.apps.<product>`
   argv and the `QUILL_APP_ROOT` / `QUILL_PORTABLE` env vars.
4. Forwards the exit code.

## Files

| File | Purpose |
| --- | --- |
| `launcher.c` | The launcher body. `wmain` on Windows, `main` on POSIX. |
| `runtime_resolve.c` | Path-walk + version-marker validation. The never-crash contract. |
| `runtime_resolve.h` | `QlRuntime` struct + the two public entry points. |
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
python scripts/build_native_launcher.py --product quill --out windows-distribution\portable
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

## Tests

```powershell
pytest tests/unit/native/test_runtime_resolver.py -v
pytest tests/unit/scripts/test_build_native_launcher.py -v
```

The first is a Python mirror of the C runtime resolver and exercises
the algorithm in isolation. The second is the per-product identity
contract and the cross-product storage-mode allowlist check.

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
