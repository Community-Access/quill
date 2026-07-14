"""Tests for the MainFrame section-move wrapper methods (PR1, EdSharp port).

The pure section-move logic is exercised in
``tests/unit/core/test_markdown_sections.py``.  This module verifies the
``MainFrame`` wiring: surface gating, editor text round-trip, and announcement.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.settings import Settings
from quill.ui.main_frame import MainFrame


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self._text = text
        self._caret = caret
        self.set_value_calls: list[str] = []
        self.set_caret_calls: list[int] = []

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
    assert frame._status_message == "Bottom!"


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
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_menu.py"
    ).read_text(encoding="utf-8")
    for attr in ("_id_move_section_up", "_id_move_section_down"):
        assert f"self.{attr},\n" in source, f"{attr} is never Append-ed to a real menu"
        assert f"id=self.{attr}" in source, f"{attr} is never bound to a handler"
