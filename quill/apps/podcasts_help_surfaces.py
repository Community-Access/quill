"""Answers QUILL Cast did not have: the sheet, media tools, backup (5.1/5.3/5.6).

**The Keyboard Shortcuts Sheet.** Cast had the shortcuts *editor* -- rebind a
key -- and no sheet. They answer different questions. The editor is for
somebody who knows which key they want to change; the sheet is for somebody
learning the app, who wants to know what keys there *are*. It has to be
generated rather than written down, because a hand-written list of keys is
wrong the first time anybody rebinds one.

The implementation is Quill Radio's, unchanged: ``show_cheat_sheet`` walks the
live ``wx.MenuBar`` rather than the keymap, so it lists the keys this listener
actually has and cannot fall out of step with the menus, because it *is* the
menus. Nothing in it is radio-specific -- it asks the host for its frame, its
announcer and its modal helper, all of which Cast has -- so this is a caller
rather than a copy. A second implementation is how two apps come to disagree
about what a key does.

**Media Tools.** The asked half of what
:mod:`quill.ui.podcasts.media_preflight` says once at launch. Unlike the
notice, this is never silent: somebody who chose a menu item asked a question,
and silence reads as a broken menu item rather than as good news.

**Back Up / Restore.** Cast had Export My Data -- a readable JSON snapshot --
and the shared setup transfer. Neither is a restore, and Cast's library is the
more painful of the two apps' to lose: subscriptions, folders, playlists,
positions, notes and statistics are years of accumulated choices, where a
station list can be rebuilt from a directory in an afternoon. See
:mod:`quill.ui.podcasts.backup_ui`.
"""

from __future__ import annotations

__all__ = ["CastHelpSurfacesMixin"]


class CastHelpSurfacesMixin:
    """Help > Keyboard Shortcuts Sheet and Media Tools, and Back Up / Restore.

    Three thin entry points that each hand off to the module that does the
    work. They live together because they are the app frame's *answers* --
    things it knows how to be asked -- rather than three features with three
    homes.
    """

    def podcast_keyboard_cheat_sheet(self) -> None:
        """Every key this build answers to, read off the menu bar you have."""
        from quill.ui.radio.cheat_sheet_dialog import show_cheat_sheet

        show_cheat_sheet(self)

    def podcast_media_tools_status(self) -> None:
        """Whether FFmpeg is here, and what it costs when it is not.

        Announced rather than shown in a dialog: it is one or two sentences,
        and a modal for two sentences is two extra keystrokes to dismiss
        something already read aloud. The status bar keeps the same words for
        anybody reading the screen instead.
        """
        from quill.ui.podcasts import media_preflight

        said = media_preflight.readout()
        self._announce(said)
        # The status bar keeps the same words for anybody reading the screen
        # rather than listening. It is overwritten by the next playback change,
        # which is correct: this is an answer to a question, not a state.
        setter = getattr(self, "_set_status", None)
        if callable(setter):
            setter(said)

    def back_up_cast_data(self) -> None:
        """Save the whole library as one file (list.md 5.6)."""
        from quill.ui.podcasts.backup_ui import back_up_cast_data

        back_up_cast_data(self)

    def restore_cast_data(self) -> None:
        """Put a library back from a backup, live, without a restart."""
        from quill.ui.podcasts.backup_ui import restore_cast_data

        restore_cast_data(self)

    def surface_cast_media_health(self) -> None:
        """The launch-time half. Deferred by the caller; never raises."""
        from quill.ui.podcasts import media_preflight

        media_preflight.surface_media_health_startup(self)
