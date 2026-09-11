"""The File menu: New, Open, Save, Save As, Close, Exit, Page Setup, Print.

Every one of these is *one state change behind a modal dialog*, which is why
they sat shape-only until 2026-09-11 -- and why they are worth reaching. The
interesting half is never the dialog; it is what the command does with the
answer, and above all what it does with **cancel**. A command that acts on a
cancelled Save As overwrites a file the user chose not to name.

So the shape of nearly every test here is a pair: answer OK and assert the
thing happened, answer cancel and assert **nothing** did. See
``DialogRecorder`` and ``fake_wx_dialog`` in ``conftest.py`` for the seam.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.ui.richedit_editing import PLAIN, RICH

# --------------------------------------------------------------------------- #
# New
# --------------------------------------------------------------------------- #


def test_new_asks_the_app_for_the_default_mode(lite_window):
    win = lite_window("hello")
    win.app.settings.default_mode = "rich"
    win.cmd_new()
    assert win.app.opened == [((RICH,), {})]


def test_new_follows_the_setting_rather_than_the_current_document(lite_window):
    """Ctrl+N makes what Preferences says, not a copy of what is in front of you.

    The explicit New Plain Text and New Rich Text commands exist precisely so
    the plain one can be a preference.
    """
    win = lite_window("hello", mode="rich")
    win.app.settings.default_mode = "plain"
    win.cmd_new()
    assert win.app.opened == [((PLAIN,), {})]


def test_new_rich_and_new_plain_ignore_the_setting(lite_window):
    win = lite_window("hello")
    win.app.settings.default_mode = "plain"
    win.cmd_new_rich()
    win.cmd_new_plain()
    assert win.app.opened == [((RICH,), {}), ((PLAIN,), {})]


# --------------------------------------------------------------------------- #
# Open
# --------------------------------------------------------------------------- #


def test_open_does_nothing_when_the_dialog_is_cancelled(lite_window, fake_wx_dialog):
    fake_wx_dialog("FileDialog", wx.ID_CANCEL, GetPaths=[])
    win = lite_window("")
    win.cmd_open()
    assert win.app.opened == []


def test_open_reuses_a_blank_window_for_the_first_file(lite_window, fake_wx_dialog, tmp_path):
    """A blank untouched window is a window nobody would miss.

    Opening into it rather than beside it is what stops every launch leaving an
    empty Untitled behind the file you asked for.
    """
    target = tmp_path / "a.txt"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPaths=[str(target)])
    win = lite_window("")
    win.cmd_open()
    (args, kwargs) = win.app.opened[0]
    assert args == (Path(target),)
    assert kwargs == {"reuse": win}


def test_open_does_not_reuse_a_window_with_work_in_it(lite_window, fake_wx_dialog, tmp_path):
    target = tmp_path / "a.txt"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPaths=[str(target)])
    win = lite_window("something I typed")
    win.cmd_open()
    assert win.app.opened[0][1] == {"reuse": None}


def test_open_does_not_reuse_a_modified_window_even_when_empty(
    lite_window, fake_wx_dialog, tmp_path
):
    """Empty and *modified* is somebody who has just deleted everything.

    Reusing it would throw away an undo history they can still reach.
    """
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPaths=[str(tmp_path / "a.txt")])
    win = lite_window("")
    win.modified = True
    win.cmd_open()
    assert win.app.opened[0][1] == {"reuse": None}


def test_opening_four_files_claims_the_window_only_once(lite_window, fake_wx_dialog, tmp_path):
    """The bug the ``index == 0`` guard exists for.

    Reusing the window for every file in the list would leave three of the four
    documents opened and immediately discarded -- and only the last one visible,
    which reads as "Open lost my files".
    """
    names = [str(tmp_path / f"{n}.txt") for n in range(4)]
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPaths=names)
    win = lite_window("")
    win.cmd_open()
    reuse = [kwargs["reuse"] for _args, kwargs in win.app.opened]
    assert reuse == [win, None, None, None]
    assert len(win.app.opened) == 4


# --------------------------------------------------------------------------- #
# Save and Save As
# --------------------------------------------------------------------------- #


def test_save_writes_the_open_path(lite_window, tmp_path):
    target = tmp_path / "note.txt"
    win = lite_window("hello")
    win.path = target
    win.cmd_save()
    assert target.read_text(encoding="utf-8") == "hello"
    assert win.modified is False


def test_save_as_cancelled_writes_nothing(lite_window, fake_wx_dialog, tmp_path):
    fake_wx_dialog("FileDialog", wx.ID_CANCEL, GetPath="")
    win = lite_window("hello")
    assert win.cmd_save_as() is False
    assert list(tmp_path.glob("*.txt")) == []


def test_save_as_writes_the_chosen_path(lite_window, fake_wx_dialog, tmp_path):
    target = tmp_path / "chosen.txt"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(target))
    win = lite_window("hello")
    assert win.cmd_save_as() is True
    assert target.read_text(encoding="utf-8") == "hello"
    assert win.path == target


def test_save_as_to_an_rtf_name_switches_the_document_to_rich(
    lite_window, fake_wx_dialog, tmp_path
):
    """The extension is the instruction. Saving a plain document as .rtf and
    getting a plain-text file with an .rtf name would be obeying the letter."""
    target = tmp_path / "chosen.rtf"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(target))
    win = lite_window("hello", mode="plain")
    win.cmd_save_as()
    assert win.editor.mode == RICH


def test_save_as_to_a_txt_name_from_rich_asks_before_flattening(
    lite_window, fake_wx_dialog, tmp_path, monkeypatch
):
    """Losing formatting is not a thing to do quietly.

    And the prompt defaults to No: a listener pressing Enter reflexively must
    not be the one who throws the formatting away.
    """
    import quill.apps.lite_window_commands as commands

    asked: list[int] = []

    def _refuse(_message, _caption, style, _parent):
        asked.append(style)
        return wx.NO

    monkeypatch.setattr(commands, "show_message_box", _refuse)
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(tmp_path / "flat.txt"))
    win = lite_window("hello", mode="rich")

    assert win.cmd_save_as() is False
    assert (tmp_path / "flat.txt").exists() is False
    assert asked and asked[0] & wx.NO_DEFAULT


def test_agreeing_to_flatten_saves_as_plain_text(
    lite_window, fake_wx_dialog, tmp_path, monkeypatch
):
    import quill.apps.lite_window_commands as commands

    monkeypatch.setattr(commands, "show_message_box", lambda *_a, **_k: wx.YES)
    target = tmp_path / "flat.txt"
    fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(target))
    win = lite_window("hello", mode="rich")

    assert win.cmd_save_as() is True
    assert win.editor.mode == PLAIN
    assert target.read_text(encoding="utf-8") == "hello"


# --------------------------------------------------------------------------- #
# Close and Exit
# --------------------------------------------------------------------------- #


def test_close_closes_this_window_only(lite_window):
    win = lite_window("hello")
    win.cmd_close()
    assert win.closed == 1
    assert win.app.exited == 0


def test_exit_asks_the_app_to_close_everything(lite_window):
    """Not the same key and not the same act: Ctrl+W is one document, Alt+F4 is
    the session. A window that exited the app would lose the other documents."""
    win = lite_window("hello")
    win.cmd_exit()
    assert win.app.exited == 1
    assert win.closed == 0


# --------------------------------------------------------------------------- #
# File format (encoding and line endings)
# --------------------------------------------------------------------------- #


def test_file_format_cancelled_changes_nothing(lite_window, lite_dialogs):
    win = lite_window("hello")
    before = (win.encoding, win.newline, win.modified)
    win.cmd_file_format()
    assert lite_dialogs.names() == ["edit_file_format"]
    assert (win.encoding, win.newline, win.modified) == before


def test_file_format_is_offered_what_the_document_currently_uses(lite_window, lite_dialogs):
    win = lite_window("hello")
    win.encoding, win.newline = "cp1252", "\n"
    win.cmd_file_format()
    assert lite_dialogs.kwargs_for("edit_file_format") == {
        "encoding": "cp1252",
        "newline": "\n",
    }


def test_choosing_a_new_format_records_it_and_says_so(lite_window, lite_dialogs):
    win = lite_window("hello")
    lite_dialogs.answer("edit_file_format", ("utf-8", "\n"))
    win.cmd_file_format()
    assert (win.encoding, win.newline) == ("utf-8", "\n")
    assert win.modified is True
    assert "Unix" in win.announcements[-1] or "\\n" not in win.announcements[-1]
    assert win.announcements[-1].startswith("Saving as ")


def test_choosing_the_same_format_is_not_a_modification(lite_window, lite_dialogs):
    """Re-picking what you already had must not dirty the document.

    Otherwise opening the window to *look* leaves an unsaved-changes prompt
    behind, which teaches people not to look.
    """
    win = lite_window("hello")
    lite_dialogs.answer("edit_file_format", (win.encoding, win.newline))
    win.cmd_file_format()
    assert win.modified is False
    assert win.announcements == []


# --------------------------------------------------------------------------- #
# Page Setup and Print
# --------------------------------------------------------------------------- #


@pytest.fixture
def stub_print_data(monkeypatch):
    """``wx.PrintData`` / ``PageSetupDialogData`` / ``PrintDialogData`` as pass-throughs.

    All three are opaque C++ value objects that only accept each other, so the
    real ones reject the placeholder in ``FakePrintSettings`` before the command
    under test has done anything. Identity is all these tests need: the
    question is whether an OK *replaces* the stored settings and a cancel
    *leaves them alone*.
    """
    for name in ("PrintData", "PageSetupDialogData", "PrintDialogData"):
        monkeypatch.setattr(wx, name, lambda value=None: value)


def test_page_setup_cancelled_keeps_the_existing_settings(
    lite_window, fake_wx_dialog, stub_print_data
):
    fake_wx_dialog("PageSetupDialog", wx.ID_CANCEL, GetPageSetupData=object())
    win = lite_window("hello")
    before = (win.app.print_settings.page_setup, win.app.print_settings.print_data)
    win.cmd_page_setup()
    assert (win.app.print_settings.page_setup, win.app.print_settings.print_data) == before
    assert win.announcements == []


def test_page_setup_saves_what_the_dialog_returned(lite_window, fake_wx_dialog, stub_print_data):
    from conftest import FakePageData

    chosen = FakePageData("chosen")
    fake_wx_dialog("PageSetupDialog", wx.ID_OK, GetPageSetupData=chosen)
    win = lite_window("hello")
    win.cmd_page_setup()
    assert win.app.print_settings.page_setup is chosen
    assert win.announcements[-1] == "Page setup saved"


def test_page_setup_is_not_used_as_a_context_manager(
    lite_window, fake_wx_dialog, monkeypatch, stub_print_data
):
    """The bug in the shipped comment, pinned.

    ``wx.PageSetupDialog`` is one of the few Phoenix dialogs that is *not* a
    context manager, so a ``with`` block raised TypeError before the dialog was
    ever shown -- Page Setup did nothing at all and nothing said why. A fake
    whose ``__enter__`` explodes catches a regression to that form.
    """

    class _NotAContextManager:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            raise AssertionError("PageSetupDialog is not a context manager")

        def ShowModal(self):  # noqa: N802 - wx API shape
            return wx.ID_CANCEL

        def Destroy(self):  # noqa: N802 - wx API shape
            return None

    monkeypatch.setattr(wx, "PageSetupDialog", _NotAContextManager)
    win = lite_window("hello")
    win.cmd_page_setup()  # must not raise


def test_print_reports_a_real_failure_and_stays_quiet_on_cancel(
    lite_window, monkeypatch, stub_print_data, wx_app
):
    """Cancelling is not a failure and must say nothing.

    A "print failed" after somebody chose Cancel is the app arguing with them.
    A genuine error, though, is the one thing nothing else in the app mentions.
    """

    class _Printer:
        last_error = wx.PRINTER_CANCELLED

        def __init__(self, *_a, **_k):
            pass

        def Print(self, *_a, **_k):  # noqa: N802 - wx API shape
            return False

        def GetLastError(self):  # noqa: N802 - wx API shape
            return type(self).last_error

    monkeypatch.setattr(wx, "Printer", _Printer)
    win = lite_window("hello")

    win.cmd_print()
    assert win.failures == []
    assert win.announcements == []

    _Printer.last_error = wx.PRINTER_ERROR
    win.cmd_print()
    assert win.failures and win.failures[0][0] == "Print failed"


def test_a_successful_print_announces_the_document_and_cues_twice(
    lite_window, monkeypatch, stub_print_data, wx_app
):
    """Started and complete are two different moments and two different tones.

    Printing is the one action in the editor with a real gap between asking and
    finishing, so a single cue at either end would leave the other unmarked.
    """

    class _Printer:
        def __init__(self, *_a, **_k):
            pass

        def Print(self, *_a, **_k):  # noqa: N802 - wx API shape
            return True

        def GetPrintDialogData(self):  # noqa: N802 - wx API shape
            return type("Data", (), {"GetPrintData": staticmethod(lambda: object())})()

    monkeypatch.setattr(wx, "Printer", _Printer)
    win = lite_window("hello")
    win.path = Path("note.txt")

    win.cmd_print()
    assert win.announcements[-1] == "Printing note.txt"
    assert win.cues == ["print_started", "print_complete"]


@pytest.mark.parametrize("mode", ["plain", "rich"])
def test_printable_lines_mark_headings_only_in_rich_text(lite_window, mode):
    """A heading that prints at body weight is indistinguishable from body text.

    Until real formatted printing lands the level goes in front of the line --
    ugly, honest, and better than losing the only structure the document had.
    """
    win = lite_window("Title\nbody text", mode=mode)
    win.editor.heading_rows = [(0, 1, "Title")]
    lines = win._printable_lines()
    assert lines == (["[H1] Title", "body text"] if mode == "rich" else ["Title", "body text"])


def test_printable_lines_survive_an_editor_that_cannot_answer(lite_window):
    """Printing must never fail on a read-back it only wanted for decoration."""

    def _explode():
        raise RuntimeError("the Rich Edit control went away")

    win = lite_window("Title\nbody", mode="rich")
    win.editor.all_headings = _explode
    assert win._printable_lines() == ["Title", "body"]


def test_an_empty_document_still_prints_one_line(lite_window):
    """``splitlines()`` on "" is empty, and a printout with no pages raises."""
    win = lite_window("")
    assert win._printable_lines() == [""]
