"""Say Clipboard, Say Time, Say Windows Open, Copy Log: one implementation, both editors.

QUILL and QUILL Lite both bind these commands to the same keys and run these
same handlers -- QUILL through :mod:`quill.ui.main_frame_say_commands`, QUILL
Lite through :mod:`quill.apps.lite_window_say`. Each host supplies a handful of
small hooks (its window, its documents, its log folder, how it shows a window);
every command, every word spoken and every rule about the clipboard is here, so
the two cannot do one of these two ways (family rule 10).

The words come from :mod:`quill.core.say_commands`. The repeated-press counting
is :class:`quill.core.press_streak.PressStreak`, which answers on every press
rather than waiting: the first press of Say Clipboard is heard at once, and a
quick second press simply supersedes it with the spelling.

The system clipboard is reached only through the four module-level functions
below, so a test replaces those and never touches the machine's clipboard --
which a screen reader and the user's own copies are also using.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.press_streak import PressStreak
from quill.core.say_commands import (
    PRESS_WINDOW_SECONDS,
    ClipboardContents,
    append_selection,
    describe_append,
    describe_clear,
    describe_clipboard,
    describe_copied_log,
    describe_saved_clipboard,
    review_text,
    save_clipboard_text,
    say_date,
    say_time,
    session_log_file,
    spell_clipboard,
    suggested_clipboard_file_name,
    windows_open_count,
    windows_open_names,
)

__all__ = [
    "SayCommandsMixin",
    "clear_clipboard",
    "put_file_on_clipboard",
    "read_clipboard",
    "set_clipboard_text",
]

#: The title of the third press's window, and the name it is announced by.
REVIEW_TITLE = "Clipboard"


# ---------------------------------------------------------------------- #
# The system clipboard. Every read and write is guarded: the Windows
# clipboard is a shared, single-owner resource that can refuse to open, and a
# refusal must read as "nothing there", never as an error dialog.
# ---------------------------------------------------------------------- #


def read_clipboard() -> ClipboardContents:
    """What is on the clipboard now: text, files, or something else."""
    import wx

    clipboard = wx.TheClipboard
    try:
        if not clipboard.Open():
            return ClipboardContents()
        try:
            files: tuple[str, ...] = ()
            if clipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                file_data = wx.FileDataObject()
                if clipboard.GetData(file_data):
                    files = tuple(str(name) for name in file_data.GetFilenames())
            text = ""
            if clipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)) or clipboard.IsSupported(
                wx.DataFormat(wx.DF_TEXT)
            ):
                text_data = wx.TextDataObject()
                if clipboard.GetData(text_data):
                    text = str(text_data.GetText())
            other = False
            if not files and not text:
                other = any(
                    clipboard.IsSupported(wx.DataFormat(kind))
                    for kind in (wx.DF_BITMAP, wx.DF_DIB, wx.DF_METAFILE, wx.DF_ENHMETAFILE)
                )
        finally:
            clipboard.Close()
    except Exception:  # noqa: BLE001 - a clipboard read must never raise
        return ClipboardContents()
    return ClipboardContents(text=text, files=files, other=other)


def set_clipboard_text(text: str) -> bool:
    """Put *text* on the clipboard, replacing what was there."""
    import wx

    try:
        if not wx.TheClipboard.Open():
            return False
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001
        return False
    return True


def clear_clipboard() -> bool:
    """Empty the clipboard."""
    import wx

    try:
        if not wx.TheClipboard.Open():
            return False
        try:
            wx.TheClipboard.Clear()
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001
        return False
    return True


def put_file_on_clipboard(path: Path) -> bool:
    """Put *path* on the clipboard twice over: as a file, and as its path in text.

    Pasting into an email or a folder brings the file; pasting into a document
    or a support form brings the path. One copy serves both, which is the whole
    point -- somebody asked to "send the log" should not need to know which.
    """
    import wx

    both = wx.DataObjectComposite()
    files = wx.FileDataObject()
    files.AddFile(str(path))
    both.Add(files, True)
    both.Add(wx.TextDataObject(str(path)))
    try:
        if not wx.TheClipboard.Open():
            return False
        try:
            wx.TheClipboard.SetData(both)
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001
        return False
    return True


class SayCommandsMixin:
    """The seven commands. Hosts override the ``_say_*`` hooks they differ on."""

    # -- hooks ------------------------------------------------------------ #
    # Defaults here are QUILL Lite's shape; QUILL's adapter overrides them.

    def _say_result(self, message: str) -> None:
        """Speak and braille a result through the host's announcement path."""
        self._announce(message)  # type: ignore[attr-defined]

    def _say_selected_text(self) -> str:
        return str(self._selected_text())  # type: ignore[attr-defined]

    def _say_open_documents(self) -> tuple[list[str], int]:
        """(document names in window order, index of this one)."""
        app: Any = getattr(self, "app", None)
        frames = list(getattr(app, "frames", []))
        names = [str(frame.document_name()) for frame in frames]
        current = next((i for i, frame in enumerate(frames) if frame is self), -1)
        return names, current

    def _say_log_dir(self) -> Path:
        return Path(self.app.data_dir) / "logs"  # type: ignore[attr-defined]

    def _say_show_text(self, title: str, text: str) -> None:
        raise NotImplementedError  # each host shows its own read-only window

    def _say_ask_save_path(self, suggested: str) -> Path | None:
        raise NotImplementedError  # each host shows its own Save dialog

    def _say_now(self) -> datetime:
        return datetime.now()

    def _say_presses(self, binding: str, ceiling: int) -> int:
        streak = self.__dict__.get("_say_streak")
        if streak is None:
            streak = PressStreak(PRESS_WINDOW_SECONDS)
            self.__dict__["_say_streak"] = streak
        return int(streak.press(binding, time.monotonic(), max_count=ceiling))

    # -- the clipboard ---------------------------------------------------- #

    def cmd_say_clipboard(self) -> None:
        """Say the clipboard; a quick second press spells it, a third shows it."""
        press = self._say_presses("say_clipboard", 3)
        contents = read_clipboard()
        if press == 3 and (contents.text or contents.files):
            self._say_show_text(REVIEW_TITLE, review_text(contents))
            return
        self._say_result(spell_clipboard(contents) if press == 2 else describe_clipboard(contents))

    def cmd_append_to_clipboard(self) -> None:
        """Add the selection to the end of the clipboard's text, on a new line."""
        selection = self._say_selected_text()
        if not selection:
            self._say_result("Select text first to append it to the clipboard")
            return
        contents = read_clipboard()
        # Files on the clipboard carry their paths as text too; appending to
        # those would quietly turn a copied file into a list of paths.
        existing = "" if contents.files else contents.text
        combined = append_selection(existing, selection)
        if not set_clipboard_text(combined):
            self._say_result("Could not reach the clipboard. Try again in a moment")
            return
        self._say_result(describe_append(selection, combined))

    def cmd_clear_clipboard(self) -> None:
        """Empty the clipboard, so nothing private is left there to paste."""
        had_anything = not read_clipboard().empty
        if not clear_clipboard():
            self._say_result("Could not reach the clipboard. Try again in a moment")
            return
        self._say_result(describe_clear(had_anything))

    def cmd_save_clipboard(self) -> None:
        """Save the clipboard's text to a file you name."""
        contents = read_clipboard()
        if contents.files or not contents.text:
            if contents.files:
                self._say_result("The clipboard holds files, not text, so there is nothing to save")
            else:
                self._say_result(describe_clipboard(contents))
            return
        target = self._say_ask_save_path(suggested_clipboard_file_name(self._say_now()))
        if target is None:
            return  # cancelled: the Save dialog closing is the answer
        try:
            save_clipboard_text(target, contents.text)
        except OSError as error:
            self._say_result(f"Could not save the clipboard: {error}")
            return
        self._say_result(describe_saved_clipboard(target, contents.text))

    # -- the time, the documents, the log --------------------------------- #

    def cmd_say_time(self) -> None:
        """Say the time; a quick second press says the date."""
        now = self._say_now()
        press = self._say_presses("say_time", 2)
        self._say_result(say_date(now) if press == 2 else say_time(now))

    def cmd_say_windows_open(self) -> None:
        """Say how many documents are open; a quick second press names them."""
        names, current = self._say_open_documents()
        press = self._say_presses("say_windows_open", 2)
        self._say_result(
            windows_open_names(names, current) if press == 2 else windows_open_count(names)
        )

    def cmd_copy_log(self) -> None:
        """Put this session's log on the clipboard as a file and as its path."""
        path = session_log_file(self._say_log_dir())
        if path is None:
            self._say_result("No log has been written yet")
            return
        if not put_file_on_clipboard(path):
            self._say_result("Could not reach the clipboard. Try again in a moment")
            return
        self._say_result(describe_copied_log(path))
