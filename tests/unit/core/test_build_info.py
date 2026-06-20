"""Tests for quill.build_info safe read-only access.

``quill.build_info`` is the read-side of the generated build-identity
system. The About dialog and crash reporter call into it. These tests
verify both the happy path (the generated module exists) and the
fallback path (it does not exist, e.g. an unpacked dev checkout that has
never run ``tools/generate_build_info.py``).
"""

from __future__ import annotations

import pytest

from quill import __version__, build_info


def test_get_display_version_returns_string() -> None:
    text = build_info.get_display_version()
    assert isinstance(text, str)
    assert text


def test_get_display_version_mentions_quill_for_all() -> None:
    text = build_info.get_display_version()
    assert "QUILL for All" in text


def test_get_short_version_returns_string() -> None:
    short = build_info.get_short_version()
    assert isinstance(short, str)
    assert short


def test_get_support_info_is_multiline() -> None:
    text = build_info.get_support_info()
    assert "Product:" in text
    assert "QUILL for All" in text


def test_is_release_build_default_is_false_for_test_env() -> None:
    # Test runs almost never use the stable channel.
    assert build_info.is_release_build() is False


def test_fallback_when_generated_module_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """If quill._build_info cannot be imported, the fallbacks still work."""
    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    try:
        text = build_info.get_display_version()
        short = build_info.get_short_version()
        support = build_info.get_support_info()
        assert text == f"QUILL for All {__version__} (development build)"
        assert short == __version__
        assert "Product: QUILL for All" in support
        assert "development build" in support
        assert build_info.is_release_build() is False
    finally:
        # Restore by re-running the import side-effect.
        monkeypatch.setattr(build_info, "_BUILD_INFO", build_info._load(), raising=False)


def test_resolve_running_version_prefers_override() -> None:
    assert build_info.resolve_running_version(override="1.2.3") == "1.2.3"


def test_resolve_running_version_falls_back_to_short_then_version() -> None:
    short = build_info.get_short_version()
    resolved = build_info.resolve_running_version()
    assert resolved == short or resolved == __version__
    assert resolved


def test_resolve_running_version_last_resort(monkeypatch: pytest.MonkeyPatch) -> None:
    """When every other source is empty the sentinel 0.0.0 is returned."""
    monkeypatch.setattr(build_info, "_BUILD_INFO", None)
    monkeypatch.setattr(build_info, "get_short_version", lambda: "")
    monkeypatch.setattr(build_info, "__version__", "")
    assert build_info.resolve_running_version() == "0.0.0"
