"""The "Spelling review context display mode" setting changes what the Context field shows.

Until 2026-10 nothing read ``spell_review_context_mode``. The session decides
the context, and both editors' F7 (QUILL's editor path and the shared
``review_textctrl`` QUILL Lite and the compose boxes use) now pass the setting.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.spelling.paragraph_context import normalize_context_mode, paragraph_context
from quill.core.spelling.session import ReviewSession

_TEXT = (
    "First one here. Second one here. Third one here. Fourth has a mispeled word. "
    "Fifth one here. Sixth one here. Seventh one here.\n"
    "Another paragraph entirely."
)
_DICTIONARY = set(_TEXT.lower().replace(".", " ").split()) - {"mispeled"}


def _context(mode: str) -> str:
    session = ReviewSession(text=_TEXT, dictionary=_DICTIONARY, context_mode=mode)
    issue = session.current()
    assert issue is not None and issue.word == "mispeled"
    assert issue.context_text[issue.context_word_start : issue.context_word_end] == "mispeled"
    return issue.context_text


def test_sentence_mode_shows_the_sentence_and_its_neighbours() -> None:
    context = _context("sentence")
    assert context == "Third one here. Fourth has a mispeled word. Fifth one here."


def test_paragraph_mode_shows_the_whole_paragraph_and_no_more() -> None:
    context = _context("paragraph")
    assert context.startswith("First one here.")
    assert context.endswith("Seventh one here.")
    assert "Another paragraph" not in context


def test_unknown_mode_falls_back_to_sentence() -> None:
    assert normalize_context_mode("nonsense") == "sentence"
    assert _context("nonsense") == _context("sentence")


def test_crlf_paragraph_keeps_the_word_offsets() -> None:
    text = "One line.\r\nA wrd here.\r\nLast."
    start = text.index("wrd")
    context, ws, we = paragraph_context(text, start, start + 3)
    assert context == "A wrd here."
    assert context[ws:we] == "wrd"


@pytest.mark.parametrize("mode", ["sentence", "paragraph"])
def test_shared_review_passes_the_setting(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui import spell_review, spelling_review_dialog

    seen: list[Any] = []

    class _Dialog:
        def __init__(self, *, session: Any, **_kw: Any) -> None:
            seen.append(session.current().context_text)

        def show(self, _show_modal: Any) -> None:
            pass

    monkeypatch.setattr(spelling_review_dialog, "SpellingReviewDialog", _Dialog)
    ctrl = SimpleNamespace(GetValue=lambda: _TEXT, GetInsertionPoint=lambda: 0)
    spell_review.review_textctrl(
        None,
        None,
        ctrl,
        dictionary=_DICTIONARY,
        announce_fn=lambda _t: None,
        settings=SimpleNamespace(spell_review_context_mode=mode),
        show_modal=None,
    )
    assert seen == [_context(mode)]


@pytest.mark.parametrize("mode", ["sentence", "paragraph"])
def test_quill_lite_settings_reach_the_shared_review(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QUILL Lite stores the same field, so its F7 honours the same choice."""
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.ui import spell_review, spelling_review_dialog

    seen: list[Any] = []

    class _Dialog:
        def __init__(self, *, session: Any, **_kw: Any) -> None:
            seen.append(session.current().context_text)

        def show(self, _show_modal: Any) -> None:
            pass

    monkeypatch.setattr(spelling_review_dialog, "SpellingReviewDialog", _Dialog)
    ctrl = SimpleNamespace(GetValue=lambda: _TEXT, GetInsertionPoint=lambda: 0)
    spell_review.review_textctrl(
        None,
        None,
        ctrl,
        dictionary=_DICTIONARY,
        announce_fn=lambda _t: None,
        settings=LiteSettings(spell_review_context_mode=mode).normalized(),
        show_modal=None,
    )
    assert seen == [_context(mode)]


def test_quill_lite_unknown_context_mode_normalizes_to_sentence() -> None:
    from quill.core.lite.settings import Settings as LiteSettings

    assert LiteSettings(
        spell_review_context_mode="bogus"
    ).normalized().spell_review_context_mode == ("sentence")
