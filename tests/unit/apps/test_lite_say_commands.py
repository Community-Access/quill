"""QUILL Lite's Say commands: the clipboard, the time, the open documents, the log.

The handlers are QUILL's (``quill/ui/say_commands.py``), reached here through
QUILL Lite's window exactly as the menu and the keys reach them. The system
clipboard is replaced at the four functions that touch it, and the clock at the
one the press counting reads, so nothing here races the machine's own clipboard
or depends on how fast the suite runs.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import wx

from quill.core.say_commands import ClipboardContents
from quill.ui import say_commands


class _Clipboard:
    def __init__(self) -> None:
        self.contents = ClipboardContents()
        self.file_put: Path | None = None
        self.reachable = True

    def read(self) -> ClipboardContents:
        return self.contents

    def set_text(self, text: str) -> bool:
        if self.reachable:
            self.contents = ClipboardContents(text=text)
        return self.reachable

    def clear(self) -> bool:
        if self.reachable:
            self.contents = ClipboardContents()
        return self.reachable

    def put_file(self, path: Path) -> bool:
        self.file_put = path
        return self.reachable


@pytest.fixture
def clipboard(monkeypatch) -> _Clipboard:
    fake = _Clipboard()
    monkeypatch.setattr(say_commands, "read_clipboard", fake.read)
    monkeypatch.setattr(say_commands, "set_clipboard_text", fake.set_text)
    monkeypatch.setattr(say_commands, "clear_clipboard", fake.clear)
    monkeypatch.setattr(say_commands, "put_file_on_clipboard", fake.put_file)
    return fake


@pytest.fixture
def clock(monkeypatch):
    """A monotonic clock the test moves by hand."""
    now = [1000.0]
    monkeypatch.setattr(say_commands, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return now


# -- Say Clipboard --------------------------------------------------------- #


def test_one_press_says_the_clipboard_text(lite_window, clipboard, clock) -> None:
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="meet at noon")
    win.cmd_say_clipboard()
    assert win.announcements == ["meet at noon"]


def test_a_quick_second_press_spells_it(lite_window, clipboard, clock) -> None:
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="Ab")
    win.cmd_say_clipboard()
    clock[0] += 0.2
    win.cmd_say_clipboard()
    assert win.announcements == ["Ab", "cap A. B"]


def test_a_slow_second_press_says_it_again_rather_than_spelling(
    lite_window, clipboard, clock
) -> None:
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="Ab")
    win.cmd_say_clipboard()
    clock[0] += 2.0
    win.cmd_say_clipboard()
    assert win.announcements == ["Ab", "Ab"]


def test_a_third_quick_press_shows_the_clipboard_to_read(
    lite_window, clipboard, clock, monkeypatch
) -> None:
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.apps.lite_window_say.show_text_window",
        lambda _parent, title, body, **_k: shown.append((title, body)),
    )
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="line one\nline two")
    for _ in range(3):
        win.cmd_say_clipboard()
        clock[0] += 0.2
    assert shown == [("Clipboard", "line one\nline two")]
    assert len(win.announcements) == 2  # said, spelled, then the window speaks for itself


def test_files_on_the_clipboard_are_counted_and_named(lite_window, clipboard, clock) -> None:
    win = lite_window("")
    clipboard.contents = ClipboardContents(
        text=r"C:\a\report.docx", files=(r"C:\a\report.docx", r"C:\a\notes.txt")
    )
    win.cmd_say_clipboard()
    assert win.announcements == ["2 files on the clipboard: report.docx, notes.txt"]


def test_an_empty_clipboard_says_so(lite_window, clipboard, clock) -> None:
    win = lite_window("")
    win.cmd_say_clipboard()
    assert win.announcements == ["The clipboard is empty"]


# -- Append, Clear, Save --------------------------------------------------- #


def test_append_adds_the_selection_on_a_new_line(lite_window, clipboard) -> None:
    win = lite_window("alpha bravo")
    win.control.SetSelection(6, 11)
    clipboard.contents = ClipboardContents(text="first")
    win.cmd_append_to_clipboard()
    assert clipboard.contents.text == "first\nbravo"
    assert win.announcements == [
        "Appended 5 characters to the clipboard, which now holds 11 characters"
    ]


def test_append_with_nothing_selected_says_what_to_do(lite_window, clipboard) -> None:
    win = lite_window("alpha", cursor=2)
    clipboard.contents = ClipboardContents(text="first")
    win.cmd_append_to_clipboard()
    assert clipboard.contents.text == "first"
    assert win.announcements == ["Select text first to append it to the clipboard"]


def test_clear_empties_the_clipboard(lite_window, clipboard) -> None:
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="a password")
    win.cmd_clear_clipboard()
    assert clipboard.contents.empty
    assert win.announcements == ["Cleared the clipboard"]


def test_clear_when_the_clipboard_cannot_be_reached_says_so(lite_window, clipboard) -> None:
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="a password")
    clipboard.reachable = False
    win.cmd_clear_clipboard()
    assert clipboard.contents.text == "a password"
    assert win.announcements == ["Could not reach the clipboard. Try again in a moment"]


def test_save_writes_the_clipboard_to_the_file_chosen(
    lite_window, clipboard, fake_wx_dialog, tmp_path
) -> None:
    target = tmp_path / "saved.txt"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(target))
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="kept for later")
    win.cmd_save_clipboard()
    assert target.read_text(encoding="utf-8") == "kept for later"
    assert win.announcements == ["Saved 14 characters to saved.txt"]


def test_save_cancelled_writes_nothing_and_says_nothing(
    lite_window, clipboard, fake_wx_dialog, tmp_path
) -> None:
    fake_wx_dialog("FileDialog", wx.ID_CANCEL, GetPath=str(tmp_path / "never.txt"))
    win = lite_window("")
    clipboard.contents = ClipboardContents(text="kept for later")
    win.cmd_save_clipboard()
    assert not (tmp_path / "never.txt").exists()
    assert win.announcements == []


# -- Time, windows, log ---------------------------------------------------- #


def test_say_time_then_the_date_on_a_quick_second_press(lite_window, clock, monkeypatch) -> None:
    win = lite_window("")
    monkeypatch.setattr(win, "_say_now", lambda: datetime(2026, 11, 6, 14, 5))
    win.cmd_say_time()
    clock[0] += 0.2
    win.cmd_say_time()
    assert win.announcements == ["2:05 PM", "Friday, November 6, 2026"]


def test_say_windows_open_counts_then_names(lite_window, clock) -> None:
    win = lite_window("")
    other = lite_window("")
    other.path = Path("notes.txt")
    win.app.frames.append(other)
    win.cmd_say_windows_open()
    clock[0] += 0.2
    win.cmd_say_windows_open()
    assert win.announcements == [
        "2 documents open",
        "2 documents: Untitled 1 (current), notes.txt",
    ]


def test_copy_log_puts_the_log_on_the_clipboard(lite_window, clipboard) -> None:
    win = lite_window("")
    log = Path(win.app.data_dir) / "logs" / "quill.log"
    log.parent.mkdir(parents=True)
    log.write_text("started\n", encoding="utf-8")
    win.cmd_copy_log()
    assert clipboard.file_put == log
    assert win.announcements[0].startswith("Copied the log, quill.log, to the clipboard")


def test_copy_log_with_no_log_yet_says_so(lite_window, clipboard) -> None:
    win = lite_window("")
    win.cmd_copy_log()
    assert clipboard.file_put is None
    assert win.announcements == ["No log has been written yet"]
