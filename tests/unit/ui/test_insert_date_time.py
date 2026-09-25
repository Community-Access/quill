"""F5 writes the date in QUILL too (bad.md P1.9).

F5 has put the time and date in at the caret since Notepad on Windows 3.1, and
QUILL Lite has done it since it shipped. QUILL had no F5: its three date/time
inserters are menu rows contributed by the bundled ``insert-tools`` Quillin,
reached through a submenu, and a menu row is not a chord. They also switch off
in Safe Mode with every other Quillin contribution, so in the mode people fall
back to when something is wrong QUILL could not insert a date at all.
"""

from __future__ import annotations

from quill.ui.main_frame_power_tools import PowerToolsActionsMixin


class _Editor:
    def __init__(self) -> None:
        self.text = ""

    def WriteText(self, text: str) -> None:
        self.text += text

    def GetValue(self) -> str:
        return self.text


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


def _frame() -> tuple[PowerToolsActionsMixin, _Editor, list[str]]:
    frame = PowerToolsActionsMixin.__new__(PowerToolsActionsMixin)
    editor = _Editor()
    said: list[str] = []
    frame.editor = editor  # type: ignore[attr-defined]
    frame.document = _Document()  # type: ignore[attr-defined]
    frame._announce_result = said.append  # type: ignore[attr-defined,method-assign]
    return frame, editor, said


def test_f5_writes_a_stamp_at_the_caret() -> None:
    frame, editor, _said = _frame()
    frame.insert_date_time()
    assert editor.text
    # "14:07 16/09/2026" -- Notepad's shape: five colons-and-slashes worth of
    # punctuation and nothing else.
    assert editor.text.count(":") == 1
    assert editor.text.count("/") == 2


def test_it_reads_the_stamp_back() -> None:
    """The whole accessibility of the command. A screen reader says nothing
    when an app writes text on its own behalf -- no focus moved and no control
    was named -- so without this, F5 is a keystroke after which something has
    silently appeared, and finding out what means arrowing back over it."""
    frame, editor, said = _frame()
    frame.insert_date_time()
    assert said == [f"Inserted {editor.text}"]


def test_the_document_model_keeps_up() -> None:
    frame, editor, _said = _frame()
    frame.insert_date_time()
    assert frame.document.text == editor.text


def test_it_is_f5_and_it_is_a_core_command() -> None:
    """Core rather than contributed, which is what makes it survive Safe Mode."""
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["edit.insert_date_time"] == "F5"


def test_both_editors_write_the_same_stamp() -> None:
    """One format in core, so QUILL's F5 and QUILL Lite's cannot drift apart."""
    from quill.apps import lite_window_commands
    from quill.core.datetime_insert import NOTEPAD_DATETIME_FORMAT

    assert lite_window_commands._DATETIME_FORMAT == NOTEPAD_DATETIME_FORMAT
