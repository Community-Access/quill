"""Tab's meaning follows the document kind (bad.md T3, P1.21).

QUILL indented the line in every kind of document and QuillLite typed a tab in
every kind, each with a toggle to get the other behaviour -- so the same key
did two different things in two editors that share a keymap, and each default
was wrong somewhere: a literal tab inside a Markdown list item breaks the list,
and indenting the line in a plain note is not what a Notepad replacement does.

The rule lives beside ``autoformat_allows`` because it is the same shape of
decision: the document kind is something both editors already know.
"""

from __future__ import annotations

import pytest

from quill.core.tab_behaviour import tab_inserts_a_tab


@pytest.mark.parametrize("kind", ["markdown", "html", "HTML", " Markdown "])
def test_markup_indents_because_indentation_is_structure_there(kind: str) -> None:
    assert tab_inserts_a_tab(kind) is False


@pytest.mark.parametrize("kind", ["plain", "text", "rtf", "docx", "python"])
def test_everything_else_types_a_tab(kind: str) -> None:
    assert tab_inserts_a_tab(kind) is True


def test_an_unknown_kind_types_a_tab() -> None:
    """An untitled buffer is a note far more often than a structured document.

    The failure in this direction is one character somebody can see and delete;
    the other direction silently re-indents a line they did not ask to move.
    """
    assert tab_inserts_a_tab(None) is True


def test_both_editors_read_this_one_rule() -> None:
    """The point of the row: one rule, two editors, no second opinion."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    quill_side = (root / "quill" / "ui" / "main_frame_typing_modes.py").read_text(encoding="utf-8")
    lite_side = (root / "quill" / "apps" / "lite_window_typing.py").read_text(encoding="utf-8")
    for source in (quill_side, lite_side):
        assert "from quill.core.tab_behaviour import tab_inserts_a_tab" in source
        assert "_tab_mode_chosen" in source
