"""Tests for the platform dispatch helpers (#7).

The per-surface helpers delegate to the module-level-gated root modules
(``quill.platform.high_contrast`` / ``quill.platform.sr_detect``) instead of
re-implementing the platform-routing branch, so a routing change applied in
the root module is picked up automatically.
"""

from __future__ import annotations

from quill.platform import dispatch


def test_current_platform_returns_a_known_label():
    assert dispatch.current_platform() in {"macos", "windows", "other"}


def test_is_high_contrast_enabled_returns_bool():
    # On any host this must return a bool without raising -- the dispatcher no
    # longer carries its own platform branch to get wrong (#7).
    assert isinstance(dispatch.is_high_contrast_enabled(), bool)


def test_detect_screen_reader_returns_detection_dataclass():
    result = dispatch.detect_screen_reader()
    assert isinstance(result, dispatch.ScreenReaderDetection)
    assert hasattr(result, "detected")
    assert hasattr(result, "name")
    assert hasattr(result, "source")


def test_is_high_contrast_enabled_delegates_to_root_module(monkeypatch):
    import quill.platform.high_contrast as hc

    calls = {"n": 0}

    def _spy():
        calls["n"] += 1
        return False

    monkeypatch.setattr(hc, "is_high_contrast_enabled", _spy)
    dispatch.is_high_contrast_enabled()
    assert calls["n"] == 1


def test_detect_screen_reader_delegates_to_root_module(monkeypatch):
    import quill.platform.sr_detect as sr

    calls = {"n": 0}

    def _spy():
        calls["n"] += 1
        return sr.ScreenReaderDetection(detected=False, name="none", source="")

    monkeypatch.setattr(sr, "detect_screen_reader", _spy)
    result = dispatch.detect_screen_reader()
    assert calls["n"] == 1
    assert result.detected is False
