"""Tests for windows_ocr.py importability without the winrt OCR packages.

H-3-platform: the winrt-* packages are a Windows-runtime-only optional
dependency.  On CI and non-Windows dev boxes they are not installed.  The module
must be importable regardless and must raise OcrUnavailableError at call time,
not at import time.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# The winrt sub-modules windows_ocr.py imports. Patching these to None in
# sys.modules simulates the packages being absent so the import falls into the
# graceful try/except path.
_WINRT_MODS = [
    "winrt",
    "winrt.windows",
    "winrt.windows.globalization",
    "winrt.windows.graphics",
    "winrt.windows.graphics.imaging",
    "winrt.windows.media",
    "winrt.windows.media.ocr",
    "winrt.windows.storage",
]


def test_module_imports_without_winrt() -> None:
    """H-3-platform: windows_ocr imports cleanly when the winrt packages are absent."""
    # Remove the module from the cache so the import runs fresh.
    mod_name = "quill.platform.windows.windows_ocr"
    cached = sys.modules.pop(mod_name, None)
    with patch.dict(sys.modules, {m: None for m in _WINRT_MODS}):  # type: ignore[arg-type]
        try:
            import importlib

            mod = importlib.import_module(mod_name)
        finally:
            # Restore original state whether the test passes or fails.
            sys.modules.pop(mod_name, None)
            if cached is not None:
                sys.modules[mod_name] = cached
    # If we got here without ImportError the module is importable.
    assert hasattr(mod, "recognize_with_windows_ocr")
    assert mod._WINRT_AVAILABLE is False  # type: ignore[attr-defined]


def test_recognize_raises_ocr_unavailable_when_winrt_missing() -> None:
    """H-3-platform: recognize_with_windows_ocr raises OcrUnavailableError when winrt absent."""
    from quill.io.ocr import OcrUnavailableError

    mod_name = "quill.platform.windows.windows_ocr"
    cached = sys.modules.pop(mod_name, None)
    import pytest

    with patch.dict(sys.modules, {m: None for m in _WINRT_MODS}):  # type: ignore[arg-type]
        try:
            import importlib

            mod = importlib.import_module(mod_name)
            with pytest.raises(OcrUnavailableError, match="winrt"):
                mod.recognize_with_windows_ocr(Path("dummy.png"), None)
        finally:
            sys.modules.pop(mod_name, None)
            if cached is not None:
                sys.modules[mod_name] = cached
