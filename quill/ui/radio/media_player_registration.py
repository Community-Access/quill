"""Make Quill Radio My Media Player: the editors' command, with Radio's profile.

Somebody who wants their music to open in Quill Radio when they press Enter on
it in File Explorer is asking for the same thing as somebody who wants their
``.txt`` files to open in QUILL, and Windows answers both the same way: an app
may say what it *can* open, and only the person chooses what *does*. So this is
not a second implementation. It is the shared
:class:`~quill.ui.text_editor_commands.TextEditorCommandsMixin` -- the same
explanation, the same per-user registration (skipped when an administrator
install already registered this copy), the same Default apps page -- run with
:data:`quill.core.windows_media.RADIO` and pointed at Quill Radio's window and
voice. Quill Radio has no Notepad switch; that half of the mixin is an editor's
and is never reached from here.

The doors in are Preferences > Windows and your files (the same group name the
editors use) and the Command Palette. No key: a once-a-year command gets a
place to find it, not a chord (family rule 9).
"""

from __future__ import annotations

from typing import Any

from quill.core import windows_editor as editor
from quill.core.windows_media import RADIO
from quill.ui.text_editor_commands import TextEditorCommandsMixin
from quill.ui.text_editor_prefs import GROUP_TITLE

__all__ = ["COMMAND_ID", "COMMAND_TITLE", "GROUP_TITLE", "RadioMediaPlayer", "make_media_player"]

COMMAND_ID = "radio.make_media_player"
COMMAND_TITLE = "Quill Radio: Make Quill Radio My Media Player..."
#: The Preferences button; Q is the access key no other Preferences row uses.
BUTTON_LABEL = "Make &Quill Radio My Media Player..."
BUTTON_HELP = (
    "Tells Windows, for your account, that Quill Radio can play music, audiobooks, "
    "video and playlists, then opens Windows' Default apps page for Quill Radio, "
    "where you choose which types it opens. Windows makes that choice, not Quill Radio."
)


class RadioMediaPlayer(TextEditorCommandsMixin):
    """The shared command's host, standing in for Quill Radio's app frame."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def _text_editor_profile(self) -> editor.EditorProfile:
        return RADIO

    def _text_editor_parent(self) -> Any:
        """Preferences, when the button there was pressed; else the main window."""
        import wx

        active = wx.GetActiveWindow() if wx.GetApp() is not None else None
        return active if active is not None else getattr(self._app, "frame", None)

    def _text_editor_refocus(self) -> None:
        """Focus stays where it was: Preferences, or the window the palette left."""

    def _announce(self, text: str) -> None:
        speak = getattr(self._app, "_announce", None)
        if callable(speak):
            speak(text)


def make_media_player(app: Any) -> bool:
    """Run Make Quill Radio My Media Player for *app*; True when Windows was told."""
    return RadioMediaPlayer(app).cmd_make_default_editor()


def register(app: Any) -> None:
    """Put the command in Quill Radio's Command Palette (standalone Radio only)."""
    app.commands.try_register(
        COMMAND_ID,
        COMMAND_TITLE,
        lambda: make_media_player(app),
        app._binding_for(COMMAND_ID),
        feature_id="core.radio",
    )
