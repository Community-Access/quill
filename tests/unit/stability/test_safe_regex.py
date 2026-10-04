"""Unit tests for bounded-time regex helpers and stdlib fallback."""

from __future__ import annotations

import pytest

from quill.stability.safe_regex import (
    RegexTimeoutError,
    safe_finditer,
    safe_subn,
)


def test_safe_finditer_matches() -> None:
    matches = safe_finditer(r"\d+", "abc 123 def 456")
    assert len(matches) == 2
    assert [m.group(0) for m in matches] == ["123", "456"]


def test_safe_subn_replaces() -> None:
    result, count = safe_subn(r"\d+", "NUM", "item 1 and item 2")
    assert result == "item NUM and item NUM"
    assert count == 2


def test_safe_finditer_fallback_without_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.stability.safe_regex._HAVE_REGEX", False)
    matches = safe_finditer(r"[a-z]+", "apple 123 banana")
    assert len(matches) == 2
    assert [m.group(0) for m in matches] == ["apple", "banana"]


def test_safe_subn_fallback_without_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.stability.safe_regex._HAVE_REGEX", False)
    result, count = safe_subn(r"[0-9]+", "X", "foo 42 bar 99")
    assert result == "foo X bar X"
    assert count == 2


def test_safe_finditer_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockPattern:
        def finditer(self, *args: object, **kwargs: object) -> None:
            raise TimeoutError("timeout")

    monkeypatch.setattr(
        "quill.stability.safe_regex._compile_cached", lambda *args, **kwargs: MockPattern()
    )
    with pytest.raises(RegexTimeoutError):
        safe_finditer(r".*", "test")


def test_safe_subn_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockPattern:
        def subn(self, *args: object, **kwargs: object) -> None:
            raise TimeoutError("timeout")

    monkeypatch.setattr(
        "quill.stability.safe_regex._compile_cached", lambda *args, **kwargs: MockPattern()
    )
    with pytest.raises(RegexTimeoutError):
        safe_subn(r".*", "x", "test")
