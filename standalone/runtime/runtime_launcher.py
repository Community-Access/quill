"""Entry point for the shared QuillVille Runtime bundle.

The shared runtime is ONE PyInstaller onedir (CPython + wxPython + the shared
``quill`` and ``quill_social`` packages) reused by every QuillVille app. Each
app is a thin launcher that runs this bundle's ``QuillVilleRuntime.exe`` with
the app's own entry module, exactly like ``python -m <module>``:

    QuillVilleRuntime.exe -m quill.apps.radio
    QuillVilleRuntime.exe -m quill.apps.podcasts
    QuillVilleRuntime.exe -m quill_social

So one Python install serves them all; installing a second app reuses this
runtime instead of shipping another copy (see the installer program spec).
"""

from __future__ import annotations

import runpy
import sys


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "-m":
        module = argv[1]
        # Re-shape argv so the target module sees itself as __main__ with its
        # own arguments, just as `python -m module ...` would.
        sys.argv = [module, *argv[2:]]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return 0
    sys.stderr.write("usage: QuillVilleRuntime.exe -m <module> [args...]\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
