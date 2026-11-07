"""Document Statistics in QUILL: counts at once, the writing report on a second press.

QUILL Lite says the same words on the same key; both go through
``quill.core.metrics.statistics_report``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("wx")

from quill.ui.main_frame import MainFrame  # noqa: E402


class _Editor:
    def __init__(self, text: str, selected: str = "") -> None:
        self.text = text
        self.selected = selected

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self.text

    def GetStringSelection(self) -> str:  # noqa: N802 - wx spelling
        return self.selected


def _frame(text: str, selected: str = "", *, announce_counts: bool = True):
    spoken: list[str] = []
    quiet: list[str] = []
    frame = SimpleNamespace(
        editor=_Editor(text, selected),
        settings=SimpleNamespace(announce_counts=announce_counts, multi_press_window_ms=60_000),
        _set_status=spoken.append,
        _set_status_quiet=quiet.append,
    )
    return frame, spoken, quiet


def test_first_press_says_the_counts_and_second_press_the_writing_report() -> None:
    frame, spoken, _quiet = _frame("The cat sat.\n\nThe dog ran far away. It was fast.\n")
    MainFrame.show_word_count(frame)
    assert spoken[-1] == "11 words, 4 lines, 49 characters"
    MainFrame.show_word_count(frame)
    report = spoken[-1]
    assert report.startswith("11 words, 4 lines, 49 characters, 2 paragraphs, 3 sentences")
    assert "0 long sentences over 30 words" in report
    assert "under a minute to read" in report
    assert "reading grade" in report


def test_counts_the_selection_when_there_is_one() -> None:
    frame, spoken, _quiet = _frame("one two three four five", "one two")
    MainFrame.show_word_count(frame)
    assert spoken[-1] == "Selection: 2 words, 1 line, 7 characters"


def test_the_writing_report_is_spoken_even_with_counts_kept_quiet() -> None:
    frame, spoken, quiet = _frame("A short one.", announce_counts=False)
    MainFrame.show_word_count(frame)
    assert quiet and not spoken
    MainFrame.show_word_count(frame)
    assert spoken and "1 sentence" in spoken[-1]
