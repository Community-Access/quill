"""Tests for the screen-capture unsupported-off-Windows messages (#5).

The capture helpers are Windows-only, but the off-Windows path must raise a
:class:`ScreenCaptureError` whose message explains *why* macOS is unsupported
(the separate Screen Recording permission) and points at a workaround, rather
than the bare "only available on Windows" string.
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from quill.platform.windows import screen_capture as sc


def _non_windows(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    # Replace the module's ``os`` reference with a stand-in whose ``name`` is
    # "posix" so the Windows-only guard fires without mutating the real ``os``
    # module (which would break pytest's own path handling).
    fake_os = types.SimpleNamespace(name="posix")
    monkeypatch.setattr(sc, "os", fake_os)
    return fake_os


def test_clipboard_capture_off_windows_explains_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    _non_windows(monkeypatch)
    with pytest.raises(sc.ScreenCaptureError) as info:
        sc.capture_clipboard_image(Path("C:/nonexistent/ocr-tmp"))
    msg = str(info.value)
    assert "Clipboard image capture" in msg
    assert "Screen Recording" in msg
    assert "Cmd+Shift" in msg


def test_screen_capture_off_windows_explains_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    _non_windows(monkeypatch)
    with pytest.raises(sc.ScreenCaptureError) as info:
        sc.capture_screen(Path("C:/nonexistent/ocr-tmp"))
    msg = str(info.value)
    assert "Screen capture" in msg
    assert "Screen Recording" in msg
    assert "Cmd+Shift" in msg


def test_active_window_capture_off_windows_explains_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    _non_windows(monkeypatch)
    with pytest.raises(sc.ScreenCaptureError) as info:
        sc.capture_screen(Path("C:/nonexistent/ocr-tmp"), target="active_window")
    assert "Screen Recording" in str(info.value)


def test_unsupported_message_names_the_action() -> None:
    msg = sc._unsupported_message("Screen capture")
    assert msg.startswith("Screen capture is only available on Windows.")
    assert "Privacy & Security" in msg
