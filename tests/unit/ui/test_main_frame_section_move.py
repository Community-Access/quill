"""Tests for the MainFrame section-move wrapper methods (PR1, EdSharp port).

The pure section-move logic is exercised in
``tests/unit/core/test_markdown_sections.py``.  This module verifies the
``MainFrame`` wiring: surface gating, editor text round-trip, and announcement.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.settings import Settings
from quill.ui.main_frame import MainFrame


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self._text = text
        self._caret = caret
        self.set_value_calls: list[str] = []
        self.set_caret_calls: list[int] = []
        self.selection: tuple[int, int] | None = None

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._caret

    def SetValue(self, text: str) -> None:
        self._text = text
        self.set_value_calls.append(text)

    def SetInsertionPoint(self, caret: int) -> None:
        self._caret = caret
        self.set_caret_calls.append(caret)

    def SetFocus(self) -> None:  # pragma: no cover - trivial
        pass

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)


class _Document:
    def __init__(self, path: str | None) -> None:
        # infer_markup_kind needs a real Path, not a str.
        from pathlib import Path as _Path

        self.path = _Path(path) if path is not None else None


def _make_frame(text: str, caret: int, path: str | None) -> tuple[MainFrame, _Editor]:
    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    frame._status_message = ""
    frame._set_status = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame._announce = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    editor = _Editor(text, caret)
    frame.editor = editor  # type: ignore[assignment]
    frame.document = _Document(path)  # type: ignore[assignment]
    return frame, editor


def test_move_section_down_in_markdown_swaps_with_next_sibling() -> None:
    text = "# A\nA body\n## B\nB body\n## C\nC body\n"
    caret = text.index("## B")
    frame, editor = _make_frame(text, caret, "test.md")
    frame.move_section_down()
    # B is now where C was.
    assert editor._text.index("## B") > editor._text.index("## C")
    assert "below" in frame._status_message.lower()
    assert "c" in frame._status_message.lower()


def test_move_section_up_in_markdown_swaps_with_previous_sibling() -> None:
    text = "# A\nA body\n## B\nB body\n## C\nC body\n"
    caret = text.index("## C")
    frame, editor = _make_frame(text, caret, "test.md")
    frame.move_section_up()
    # C is now where B was.
    assert editor._text.index("## C") < editor._text.index("## B")
    assert "above" in frame._status_message.lower()
    assert "b" in frame._status_message.lower()


def test_move_section_announces_top_when_already_first() -> None:
    text = "# A\nA body\n## B\nB body\n"
    caret = text.index("# A")
    frame, editor = _make_frame(text, caret, "test.md")
    frame.move_section_up()
    assert editor._text == text
    assert editor.set_value_calls == []  # no edit
    assert frame._status_message == "Top!"


def test_move_section_announces_bottom_when_already_last() -> None:
    text = "# A\nA body\n## B\nB body\n"
    caret = text.index("## B")
    frame, editor = _make_frame(text, caret, "test.md")
    frame.move_section_down()
    assert editor._text == text
    assert editor.set_value_calls == []
    # "B" is the last (and only) section inside "A", and the announcement
    # names that parent rather than claiming the document ends here.
    assert frame._status_message == "Bottom of A"


def test_a_section_with_no_sibling_moves_past_its_parent_in_quill_too() -> None:
    """QUILL used to re-derive its sentences from the result code alone and
    could only say "No sibling to swap with". It now reaches the same
    move_section QUILL Lite does, so the two cannot answer differently."""
    text = "# Heading 1\n\nbody\n\n## Heading 2\n\nbody\n"
    frame, editor = _make_frame(text, text.index("## Heading 2"), "test.md")
    frame.move_section_up()
    assert editor._text == "## Heading 2\n\nbody\n\n# Heading 1\n\nbody\n"
    assert frame._status_message == "Section moved above Heading 1"


def test_move_section_in_plain_text_announces_unavailable() -> None:
    text = "no headings here, just prose.\n"
    frame, editor = _make_frame(text, 0, "test.txt")
    frame.move_section_down()
    # No edit, no crash.
    assert editor.set_value_calls == []
    assert "markdown" in frame._status_message.lower()


def test_move_section_in_html_swaps_with_next_sibling() -> None:
    text = "<h2>B</h2><p>b</p><h2>C</h2><p>c</p>"
    caret = text.index("<h2>B")
    frame, editor = _make_frame(text, caret, "test.html")
    frame.move_section_down()
    assert editor._text != text
    assert "below" in frame._status_message.lower()


def test_move_section_handles_dead_editor_without_crashing() -> None:
    """#269-style: a closed-tab callback that still routes here should not
    raise a RuntimeError out of the wx main loop.  We guard the editor
    read so any RuntimeError becomes a quiet no-op."""

    class _DeadEditor:
        def GetValue(self) -> str:  # pragma: no cover - always raises
            raise RuntimeError("wrapped C/C++ object has been deleted")

        def GetInsertionPoint(self) -> int:  # pragma: no cover - always raises
            raise RuntimeError("wrapped C/C++ object has been deleted")

    class _DeadDocument:
        from pathlib import Path as _Path

        path = _Path("test.md")

    frame = MainFrame.__new__(MainFrame)
    frame.settings = Settings()
    frame.editor = _DeadEditor()  # type: ignore[assignment]
    frame.document = _DeadDocument()  # type: ignore[assignment]
    frame._status_message = ""
    frame._set_status = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    frame._announce = lambda message: setattr(frame, "_status_message", message)  # type: ignore[method-assign]
    # Must not raise.  The editor.GetValue() call inside _move_section
    # raises RuntimeError; the mixin catches it and returns silently.
    frame.move_section_down()
    # No edit applied, no status set.
    assert frame._status_message == ""


def test_move_section_ignores_fenced_heading() -> None:
    """A `# fake` inside a ``` fence is not a real heading, so moving the
    real heading above the fence must not collide with the fake one."""
    text = "# Real One\nBody\n```\n# fake\n```\n# Real Two\nMore\n"
    caret = text.index("# Real Two")
    frame, editor = _make_frame(text, caret, "test.md")
    frame.move_section_up()
    # Fake heading must still sit inside the ``` fence after the swap.
    new_text = editor._text
    fence_open = new_text.index("```")
    fence_close = new_text.index("```", fence_open + 3)
    assert fence_open < new_text.index("# fake") < fence_close


def test_move_section_menu_ids_are_appended_and_bound() -> None:
    """Regression for #278: ``_id_move_section_up``/``_id_move_section_down``
    were declared and fed into the accelerator table, but never ``Append``-ed
    to a real menu nor ``Bind``-ed to a handler, leaving the documented
    Alt+Shift+Up/Down accelerator silently inert outside the context menu."""
    _ui = Path(__file__).resolve().parents[3] / "quill" / "ui"
    source = (_ui / "main_frame_menu.py").read_text(encoding="utf-8") + (
        _ui / "main_frame_menu_bindings.py"
    ).read_text(encoding="utf-8")
    for attr in ("_id_move_section_up", "_id_move_section_down", "_id_move_section_to"):
        assert f"self.{attr},\n" in source, f"{attr} is never Append-ed to a real menu"
        assert f"id=self.{attr}" in source, f"{attr} is never bound to a handler"


def test_quill_moves_subsections_with_their_parent_too() -> None:
    """QUILL reaches the same move_section QUILL Lite does, so the fix for
    "the ### stayed behind" is one fix. Pinned on this side as well, because
    "both editors call the same function" is a claim that stops being true the
    moment somebody writes a second one."""
    text = "# Top\n\n## A1\n\nbody a1\n\n### A1a\n\nbody a1a\n\n## A2\n\nbody a2\n"
    frame, editor = _make_frame(text, text.index("## A1"), "notes.md")

    frame.move_section_down()

    assert editor._text == "# Top\n\n## A2\n\nbody a2\n\n## A1\n\nbody a1\n\n### A1a\n\nbody a1a\n"
    assert "below" in frame._status_message.lower()


def test_quill_selects_a_section_with_its_subsections() -> None:
    """Same command, same core helper and the same sentence as QUILL Lite's, so
    the two products cannot describe one capability two ways."""
    text = "# Top\n\ntop\n\n## Bread\n\nbread\n\n### Sourdough\n\nsour\n\n## Soup\n\nsoup\n"
    frame, editor = _make_frame(text, text.index("## Bread"), "notes.md")

    frame.select_section()

    assert editor.selection is not None
    start, end = editor.selection
    assert text[start:end] == "## Bread\n\nbread\n\n### Sourdough\n\nsour"
    assert frame._status_message == "Selected Bread and 1 section under it, 7 lines"


def test_quill_refuses_to_select_a_section_in_a_plain_document() -> None:
    frame, editor = _make_frame("just prose\n", 0, "notes.txt")

    frame.select_section()

    assert editor.selection is None
    assert "markdown" in frame._status_message.lower()


# --------------------------------------------------------------------------- #
# Move Section To
# --------------------------------------------------------------------------- #

_OUTLINE = "# Top\n\ntop\n\n## Bread\n\nbread\n\n### Sourdough\n\nsour\n\n## Soup\n\nsoup\n"


def _picking(frame: MainFrame, *answers: str | None) -> list[list[str]]:
    """Stand in for QUILL's searchable picker, answering *answers* in order.

    Returns the list of rows it was offered each time, because what the rows say
    is half of what this command is: a row that does not name a position is a
    row two identically titled headings both match.
    """
    offered: list[list[str]] = []
    pending = list(answers)

    def choose(**kwargs: object) -> str | None:
        rows = list(kwargs["initial_choices"])  # type: ignore[arg-type]
        offered.append(rows)
        wanted = pending.pop(0)
        if wanted is None:
            return None
        return next(row for row in rows if wanted in row)

    frame._choose_searchable_option = choose  # type: ignore[method-assign]
    return offered


def test_quill_moves_a_section_to_a_chosen_destination() -> None:
    frame, editor = _make_frame(_OUTLINE, _OUTLINE.index("## Soup"), "notes.md")
    _picking(frame, "Bread", "Before it")

    frame.move_section_to()

    assert editor._text.index("## Soup") < editor._text.index("## Bread")
    assert frame._status_message == "Moved Soup before Bread. Now 1 of 2 at this level"


def test_quill_offers_every_heading_with_its_position() -> None:
    frame, _editor = _make_frame(_OUTLINE, _OUTLINE.index("## Soup"), "notes.md")
    offered = _picking(frame, "Bread", "After it")

    frame.move_section_to()

    assert offered[0] == [
        "1 of 4, level 1 - Top",
        "2 of 4, level 2 - Bread",
        "3 of 4, level 3 - Sourdough",
        "4 of 4, level 2 - Soup (the section you are moving)",
    ]
    assert [row.split(" -")[0] for row in offered[1]] == [
        "Before it",
        "After it",
        "Inside it",
    ]


def test_quill_inside_renumbers_and_says_the_new_level() -> None:
    frame, editor = _make_frame(_OUTLINE, _OUTLINE.index("## Soup"), "notes.md")
    _picking(frame, "Bread", "Inside it")

    frame.move_section_to()

    assert "### Soup" in editor._text
    assert "now Heading 3" in frame._status_message


def test_quill_says_nothing_and_changes_nothing_when_the_picker_is_cancelled() -> None:
    frame, editor = _make_frame(_OUTLINE, _OUTLINE.index("## Soup"), "notes.md")
    _picking(frame, None)

    frame.move_section_to()

    assert editor.set_value_calls == []
    assert frame._status_message == ""


def test_quill_says_nothing_when_the_placement_question_is_cancelled() -> None:
    frame, editor = _make_frame(_OUTLINE, _OUTLINE.index("## Soup"), "notes.md")
    _picking(frame, "Bread", None)

    frame.move_section_to()

    assert editor.set_value_calls == []
    assert frame._status_message == ""


def test_quill_explains_a_destination_inside_the_moving_section() -> None:
    frame, editor = _make_frame(_OUTLINE, _OUTLINE.index("## Bread"), "notes.md")
    _picking(frame, "Sourdough", "Inside it")

    frame.move_section_to()

    assert editor.set_value_calls == []
    assert "Sourdough is inside Bread" in frame._status_message
    assert "Promote Sourdough" in frame._status_message


def test_quill_refuses_move_section_to_in_a_plain_document() -> None:
    frame, editor = _make_frame("just prose\n", 0, "notes.txt")
    frame._choose_searchable_option = lambda **_kwargs: pytest.fail("must not ask")  # type: ignore[method-assign]

    frame.move_section_to()

    assert editor.set_value_calls == []
    assert "markdown" in frame._status_message.lower()


def test_quill_move_section_to_needs_more_than_one_section() -> None:
    frame, editor = _make_frame("# Only\n\nbody\n", 0, "notes.md")
    frame._choose_searchable_option = lambda **_kwargs: pytest.fail("must not ask")  # type: ignore[method-assign]

    frame.move_section_to()

    assert editor.set_value_calls == []
    assert "only one section" in frame._status_message
