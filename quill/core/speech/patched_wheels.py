"""Wheels QUILL patches because PyPI has no installable build for its Python.

Today that is kokoro-onnx 0.6.1 with its ``Requires-Python <3.14`` cap lifted
and nothing else changed (upstream PR thewh1teagle/kokoro-onnx#195). Builds
stage it under ``{app}/wheels/patched`` (``_stage_patched_wheels`` in
``scripts/build_windows_distribution.py``); a source run uses the repo's
``vendor/wheels``. Unlike an Offline Edition wheelhouse this is not a full
dependency tree, so callers pass it as an extra ``--find-links`` beside PyPI,
never with ``--no-index``. Drop it when upstream ships a 3.14-capable release.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Where the repo keeps its vendored wheels (source runs only).
SOURCE_VENDOR_WHEELS = Path(__file__).resolve().parents[3] / "vendor" / "wheels"


def patched_wheels_dir(pattern: str = "kokoro_onnx-*.whl") -> Path | None:
    """The first folder holding a wheel matching *pattern*, or None."""
    candidates: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        candidates.append(Path(app_root) / "wheels" / "patched")
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / "wheels" / "patched")
    candidates.append(SOURCE_VENDOR_WHEELS)
    for candidate in candidates:
        try:
            if candidate.is_dir() and any(candidate.glob(pattern)):
                return candidate
        except OSError:
            continue
    return None


def kokoro_find_links(wheelhouse: Path | None, *, use_patched: bool) -> tuple[str, ...]:
    """The pip arguments that point a Kokoro install at local wheels.

    An Offline Edition *wheelhouse* is the whole tree, so it resolves with
    ``--no-index``. Otherwise, when *use_patched*, the patched kokoro-onnx goes
    beside PyPI, which still supplies onnxruntime and the rest.
    """
    if wheelhouse is not None:
        return ("--no-index", "--find-links", str(wheelhouse))
    patched = patched_wheels_dir() if use_patched else None
    return ("--find-links", str(patched)) if patched is not None else ()
