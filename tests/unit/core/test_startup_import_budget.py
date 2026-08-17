"""GATE-IMPORT: QUILL's core import path must stay light (polish.md P2.2).

The codebase practices lazy imports rigorously — every speech engine, every
optional feature imports inside the function that needs it — which is why
``import quill`` measures ~83 ms and the core trio under half a second of
subprocess wall time (measured 2026-08-17, Python 3.13.15, importtime top
offenders: quill.build_info 31 ms, quill.branding 19 ms; no third-party module
in the top 15). Nothing *enforced* that. One absent-minded top-level
``import numpy`` in a core module would tax every launch of every QuillVille
app and no test would notice.

This gate pins the discipline the way the codebase pins everything else — as a
ratchet on *facts*, not timings:

- Importing the core boundary (``quill`` + paths/settings/storage, the modules
  every app touches before its window exists) must not pull in any of the
  known-heavy libraries. Timings vary by machine and thermal luck; the set of
  loaded modules does not, so the assertion is deterministic in CI.
- A deliberately *generous* wall-clock ceiling (10x today's measurement)
  backstops catastrophic regressions — a network call or a model load at import
  time — without ever flaking on a slow runner.

Runs the probe in a subprocess so the suite's own imports cannot contaminate
the measurement.
"""

from __future__ import annotations

import subprocess
import sys
import time

#: The import boundary every app crosses before showing UI.
_CORE_IMPORTS = "import quill, quill.core.paths, quill.core.settings, quill.core.storage"

#: Libraries that must never ride along with the core import. Each is either
#: large, slow to initialize, or both — and each has a lazy-import discipline
#: already (add here when a new heavy dependency arrives).
_HEAVY = {
    "wx",
    "numpy",
    "PIL",
    "requests",
    "urllib3",
    "cryptography",
    "paramiko",
    "ctranslate2",
    "vosk",
    "sherpa_onnx",
    "faster_whisper",
    "yt_dlp",
    "feedparser",
    "docx",
    "openpyxl",
    "pypdf",
    "sounddevice",
    "mutagen",
    "rapidfuzz",
    "comtypes",
    "pythoncom",
}

#: 10x the 2026-08-17 measurement (0.46 s): only a structural regression — a
#: model load, a network call, an eager package sweep — can cross this.
_WALL_CEILING_SECONDS = 5.0


def _probe() -> tuple[set[str], float]:
    code = (
        f'{_CORE_IMPORTS}, sys; print(",".join(sorted({{m.split(".")[0] for m in sys.modules}})))'
    )
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    elapsed = time.perf_counter() - started
    return set(result.stdout.strip().split(",")), elapsed


def test_core_import_pulls_no_heavy_library() -> None:
    modules, _elapsed = _probe()
    offenders = sorted(modules & _HEAVY)
    assert offenders == [], (
        "QUILL's core import now loads heavy libraries at startup: "
        f"{offenders}. Something gained a top-level import that must become "
        "lazy (see this file's docstring; every optional engine shows the "
        "pattern)."
    )


def test_core_import_stays_under_the_catastrophe_ceiling() -> None:
    _modules, elapsed = _probe()
    assert elapsed < _WALL_CEILING_SECONDS, (
        f"Core import took {elapsed:.1f}s (ceiling {_WALL_CEILING_SECONDS}s). "
        "This ceiling is 10x the measured norm — crossing it means something "
        "structural (a model load, network, or eager package sweep) moved into "
        "import time."
    )
