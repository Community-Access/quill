"""Where Am I counts lines in the text, and says the percent (EdSharp's Say Position)."""

from __future__ import annotations


def test_where_am_i_counts_lines_in_the_text_and_says_the_percent() -> None:
    from types import SimpleNamespace

    from quill.core.document_text import DocumentText
    from quill.core.verbosity.controller import VerbosityController
    from quill.ui.main_frame_verbosity import VerbosityCommandsMixin

    text = "first line\n" + "a long paragraph " * 40 + "\nlast"
    caret = text.index("last")
    said: list[str] = []

    def no_xy(_position: int) -> tuple[bool, int, int]:
        raise AssertionError("PositionToXY counts wrapped lines; it must not be asked")

    host = SimpleNamespace(
        editor=SimpleNamespace(GetInsertionPoint=lambda: caret, PositionToXY=no_xy),
        doc_text=DocumentText(lambda: text),
        verbosity=VerbosityController(),
        _announce=said.append,
    )
    for name in ("verbosity_where_am_i", "_text_position", "_caret_position", "_announce_text"):
        setattr(host, name, getattr(VerbosityCommandsMixin, name).__get__(host))
    host.verbosity_where_am_i()
    percent = round(100 * caret / len(text))
    assert said == [f"Line 3 of 3, column 1, {percent} percent"]


def test_pressed_twice_it_opens_everything_in_a_window() -> None:
    from types import SimpleNamespace

    from quill.core.document_text import DocumentText
    from quill.core.verbosity.controller import VerbosityController
    from quill.ui.main_frame_verbosity import VerbosityCommandsMixin

    text = "one\ntwo"
    said: list[str] = []
    shown: list[str] = []
    host = SimpleNamespace(
        editor=SimpleNamespace(GetInsertionPoint=lambda: 0),
        doc_text=DocumentText(lambda: text),
        verbosity=VerbosityController(),
        document=SimpleNamespace(name="notes.md", path=None, modified=True, encoding="utf-8"),
        _announce=said.append,
        _build_cheatsheet_text=lambda query, order: "File menu:\nOpen...: Ctrl+O",
    )
    for name in (
        "verbosity_where_am_i",
        "_text_position",
        "_caret_position",
        "_announce_text",
        "_where_am_i_review_text",
    ):
        setattr(host, name, getattr(VerbosityCommandsMixin, name).__get__(host))
    host._show_where_am_i_review = lambda position: shown.append(
        host._where_am_i_review_text(position)
    )
    host.verbosity_where_am_i()
    host.verbosity_where_am_i()
    assert said == ["Line 1 of 2, column 1, 0 percent"]
    review = shown[0].splitlines()
    assert review[:4] == [
        "Line 1 of 2, column 1, 0 percent",
        "Document: notes.md",
        "Modified",
        "2 words, 7 characters",
    ]
    assert "Open...: Ctrl+O" in review
    host.verbosity_where_am_i()  # a third press starts over: spoken again
    assert len(said) == 2
