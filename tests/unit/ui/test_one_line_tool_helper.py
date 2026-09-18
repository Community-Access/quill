"""QUILL runs its line tools through one helper (bad.md N1-N3, P1.16).

There were three, with three scopes. The one that hurt: with nothing selected,
`_apply_text_block_operation` acted on the **current line**, so Sort Lines with
no selection sorted one line and announced "Sorted lines ascending" -- true of
the line, and read by a listener as true of the document.

The helper also stopped writing through `_replace_document_text`, which rewrote
the whole buffer for a change to three lines and took every other list, note
and formatting run with it.
"""

from __future__ import annotations

from quill.ui.main_frame_power_tools import PowerToolsActionsMixin

NL = chr(10)


class _Editor:
    def __init__(self, text: str, selection: tuple[int, int]) -> None:
        self.text = text
        self.selection = selection

    def GetValue(self) -> str:
        return self.text

    def GetSelection(self) -> tuple[int, int]:
        return self.selection

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)

    def WriteText(self, text: str) -> None:
        start, end = self.selection
        self.text = self.text[:start] + text + self.text[end:]
        self.selection = (start + len(text), start + len(text))


class _Host(PowerToolsActionsMixin):
    def __init__(self, text: str, selection: tuple[int, int] = (0, 0), *, mode: str = "markup"):
        self.editor = _Editor(text, selection)
        self.document = type("Doc", (), {"set_text": lambda self, text: None})()
        self.status: list[str] = []
        self._mode = mode
        self.asked = 0
        self.answer = True

    def _document_is_read_only(self) -> bool:
        return False

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _current_editor_mode(self) -> str:
        return self._mode

    def _confirm_whole_document_rewrite(self) -> bool:
        if self._mode not in {"rich", "rich_converted"}:
            return True
        self.asked += 1
        return self.answer

    def _atomic_replace(self, start: int, end: int, updated: str) -> None:
        self.editor.SetSelection(start, end)
        self.editor.WriteText(updated)


def _sort(text: str) -> str:
    return NL.join(sorted(text.split(NL)))


def test_with_no_selection_it_takes_the_whole_document() -> None:
    host = _Host("c" + NL + "a" + NL + "b")
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.editor.text == "a" + NL + "b" + NL + "c"


def test_the_announcement_carries_the_count() -> None:
    host = _Host("c" + NL + "a" + NL + "b")
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.status[-1] == "Sorted lines ascending, 3 lines"


def test_a_tool_that_changes_nothing_says_so() -> None:
    """Remove Duplicate Lines on a file with none used to sound like success."""
    host = _Host("a" + NL + "b" + NL + "c")
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.status[-1] == "No lines to change"


def test_an_empty_scope_says_so_rather_than_counting_zero() -> None:
    host = _Host("")
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.status[-1] == "Nothing to change"


def test_a_selection_is_the_scope_when_there_is_one() -> None:
    text = "keep" + NL + "c" + NL + "a"
    host = _Host(text, selection=(5, len(text)))
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.editor.text.startswith("keep" + NL)
    assert host.editor.text.endswith("a" + NL + "c")


def test_rich_asks_before_rewriting_the_whole_document() -> None:
    host = _Host("c" + NL + "a", mode="rich")
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.asked == 1
    assert host.editor.text == "a" + NL + "c"


def test_declining_that_leaves_the_document_alone() -> None:
    host = _Host("c" + NL + "a", mode="rich")
    host.answer = False
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.editor.text == "c" + NL + "a"
    assert host.status[-1] == "Left unchanged"


def test_a_selection_in_rich_is_not_asked_about() -> None:
    """The warning is about a whole-document rewrite, not about editing."""
    text = "keep" + NL + "c" + NL + "a"
    host = _Host(text, selection=(5, len(text)), mode="rich")
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.asked == 0


def test_read_only_refuses_before_anything_else() -> None:
    host = _Host("c" + NL + "a")
    host._document_is_read_only = lambda: True  # type: ignore[method-assign]
    host.apply_line_tool(_sort, "Sorted lines ascending")
    assert host.status == ["Document is read-only"]
    assert host.editor.text == "c" + NL + "a"


def test_the_old_entry_points_still_exist_and_delegate() -> None:
    """Twenty-two call sites use one name and ten use the other."""
    import inspect

    from quill.ui.main_frame import MainFrame

    assert "self.apply_line_tool(transform, status)" in inspect.getsource(
        PowerToolsActionsMixin._power_tools_transform_selection_or_document
    )
    assert "self.apply_line_tool(transform, status)" in inspect.getsource(
        MainFrame._apply_text_block_operation
    )


def test_the_helper_does_not_rewrite_the_whole_buffer() -> None:
    import inspect

    source = inspect.getsource(PowerToolsActionsMixin.apply_line_tool)
    assert "_atomic_replace(" in source
    assert "_replace_document_text(" not in source
