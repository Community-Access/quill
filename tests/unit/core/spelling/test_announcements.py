"""Tests for quill.core.spelling.announcements.AccessibilityAnnouncer."""

from __future__ import annotations

from quill.core.spelling.announcements import AccessibilityAnnouncer


def _announcer(spoken: list[str]) -> AccessibilityAnnouncer:
    # No timer_factory -> the delayed spell-aloud is skipped, keeping tests
    # deterministic.
    return AccessibilityAnnouncer(spoken.append, spell_word=False)


def test_announce_context_sentence_speaks_the_full_context() -> None:
    spoken: list[str] = []
    _announcer(spoken).announce_context_sentence(
        "The quick brown fox. It jumpd over the lazy dog. Then it slept."
    )
    assert spoken == ["The quick brown fox. It jumpd over the lazy dog. Then it slept."]


def test_announce_context_sentence_collapses_whitespace_and_newlines() -> None:
    spoken: list[str] = []
    _announcer(spoken).announce_context_sentence("A line\n\nwith  odd\tspacing.")
    assert spoken == ["A line with odd spacing."]


def test_announce_context_sentence_is_silent_on_empty_context() -> None:
    spoken: list[str] = []
    _announcer(spoken).announce_context_sentence("   \n  ")
    assert spoken == []
