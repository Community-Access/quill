"""Unit tests for the bounded-time regex helpers (from PR #1618 by @salorajan)."""

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
