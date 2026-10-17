"""QUILL Lite's Read-Only Guard: QUILL's command, QUILL's key, QUILL's memory.

Tools > Read-Only Guard, Ctrl+Alt+Backspace (2026-10-16). Before this QUILL Lite
had no way to lock a document against edits at all, so a person reading a long
reference file in it could type into it by accident and save the damage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.lite.parity import COMMAND_EQUIVALENTS
from quill.core.lite.read_only import TEXT_CHANGING_HANDLERS
from quill.core.read_only_guards import GUARD_FILENAME, READ_ONLY_REFUSAL

DOC = "# Chapter 1\n\nThe first line.\nThe second line.\n"


@pytest.fixture
def lite_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    folder = tmp_path / "lite-data"
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(folder))
    return folder


def _saved_book(tmp_path: Path) -> Path:
    path = tmp_path / "Reference Book.md"
    path.write_text(DOC, encoding="utf-8")
    return path


def test_toggle_locks_typing_and_is_remembered(lite_window, lite_data, tmp_path) -> None:
    win = lite_window(DOC)
    win.path = _saved_book(tmp_path)

    win.cmd_toggle_read_only()

    assert win.read_only_active()
    assert win.control.IsEditable() is False
    assert win.announcements[-1] == "Document is read-only"
    assert (lite_data / GUARD_FILENAME).exists()

    win.cmd_toggle_read_only()
    assert win.control.IsEditable() is True
    assert win.announcements[-1] == "Document is editable"


def test_a_guarded_file_opens_guarded_however_its_path_is_spelt(
    lite_window, lite_data, tmp_path
) -> None:
    book = _saved_book(tmp_path)
    first = lite_window(DOC)
    first.path = book
    first.cmd_toggle_read_only()

    # A restart and an open from File Explorer: a new window, a new app object,
    # and the path in the shell's spelling.
    second = lite_window(DOC)
    second.apply_read_only_guard(Path(str(book).upper()))
    assert second.read_only_active()
    assert second.control.IsEditable() is False


def test_a_file_that_cannot_be_written_opens_guarded(lite_window, lite_data, tmp_path) -> None:
    book = _saved_book(tmp_path)
    book.chmod(0o444)
    try:
        win = lite_window(DOC)
        win.apply_read_only_guard(book)
        assert win.read_only_active()
    finally:
        book.chmod(0o666)


def test_commands_that_change_text_are_refused_and_reading_ones_are_not(
    lite_window, lite_data, tmp_path
) -> None:
    win = lite_window(DOC)
    win.path = _saved_book(tmp_path)
    win.cmd_toggle_read_only()

    assert win.refuse_while_read_only("cmd_paste") is True
    assert win.announcements[-1] == READ_ONLY_REFUSAL
    for reading in (
        "cmd_copy",
        "cmd_find",
        "cmd_goto_line",
        "cmd_set_bookmark",
        "cmd_next_bookmark",
        "cmd_add_inline_note",
        "cmd_toggle_read_only",
    ):
        assert win.refuse_while_read_only(reading) is False, reading


def test_nothing_is_refused_while_the_guard_is_off(lite_window, lite_data) -> None:
    win = lite_window(DOC)
    assert not any(win.refuse_while_read_only(handler) for handler in TEXT_CHANGING_HANDLERS)


def test_bookmarks_keep_working_while_text_is_locked(lite_window, lite_data, tmp_path) -> None:
    win = lite_window(DOC)
    win.path = _saved_book(tmp_path)
    win.cmd_toggle_read_only()

    win.control.SetInsertionPoint(DOC.index("The second"))
    win.cmd_set_bookmark()
    win.control.SetInsertionPoint(0)
    win.cmd_next_bookmark()

    assert win.control.GetInsertionPoint() == DOC.index("The second")
    assert win.control.GetValue() == DOC


def test_a_note_added_while_locked_is_kept_beside_the_file(
    lite_window, lite_data, tmp_path, monkeypatch
) -> None:
    offered: list[bool] = []

    def fake(_wx, _parent, _show, **kwargs):
        offered.append(kwargs["in_file_available"])
        return ("save", "Check this chapter.", True)

    monkeypatch.setattr("quill.ui.inline_note_dialog.show_inline_note_dialog", fake)
    win = lite_window(DOC)
    win.path = _saved_book(tmp_path)
    win._language_override = "markdown"
    win.cmd_toggle_read_only()
    win.control.SetInsertionPoint(DOC.index("The first"))

    win.cmd_add_inline_note()

    assert offered == [False], "writing into the file is not offered while locked"
    assert win.control.GetValue() == DOC
    assert [note.text for note in win._inline_notes] == ["Check this chapter."]


def test_an_untitled_window_says_it_cannot_remember(lite_window, lite_data) -> None:
    win = lite_window("scratch")
    win.cmd_toggle_read_only()
    assert "it has no file name yet" in win.announcements[-1]


def test_the_word_tools_refuse_to_replace_while_locked(lite_window, lite_data, tmp_path) -> None:
    from quill.core.word_lookup import WordSpan

    win = lite_window(DOC)
    win.path = _saved_book(tmp_path)
    win.cmd_toggle_read_only()
    span = WordSpan("first", DOC.index("first"), DOC.index("first") + len("first"))

    assert win._replace_word(span, "opening") is False
    assert win.control.GetValue() == DOC
    assert win.announcements[-1] == READ_ONLY_REFUSAL


def test_the_command_is_quills_command() -> None:
    assert COMMAND_EQUIVALENTS["cmd_toggle_read_only"] == "power.toggle_read_only_guard"


def test_every_refused_handler_is_a_real_command() -> None:
    from quill.core.lite.commands import COMMANDS

    handlers = {row[3] for row in COMMANDS if len(row) > 3 and row[3]}
    assert TEXT_CHANGING_HANDLERS <= handlers, sorted(TEXT_CHANGING_HANDLERS - handlers)


def test_the_command_palette_goes_through_the_guard(lite_window, lite_data, tmp_path) -> None:
    from quill.apps.lite_services import _run_guarded

    win = lite_window(DOC)
    win.path = _saved_book(tmp_path)
    win.cmd_toggle_read_only()
    _run_guarded(win, "cmd_upper_case")
    assert win.control.GetValue() == DOC
    assert win.announcements[-1] == READ_ONLY_REFUSAL
