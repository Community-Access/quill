"""The shared surfaces both listening apps grew on 2026-08-24, as one seam.

Undo, Recent Problems, Quiet Hours and Export / Import My Setup are separate
features with separate stores, and they arrive together for the same reason:
each is a *shared* answer -- one undo slot per process, one problem log, one
quiet window, one setup file -- and each has to be claimed, registered and
menu-wired identically in Quill Radio and QUILL Cast or the two drift.

So they compose here rather than four times in each app frame:

* :class:`~quill.ui.undo_last_ui.UndoLastMixin` -- Ctrl+Z, once (11.3).
* :class:`~quill.ui.problems_dialog.RecentProblemsMixin` -- where a spoken
  failure still lives an hour later (11.5).
* :class:`~quill.ui.quiet_hours_ui.QuietHoursMixin` -- the window in which the
  app stops speaking on its own (11.9).
* :class:`~quill.ui.setup_transfer_ui.SetupTransferMixin` -- one file carrying
  the setup to another machine (11.10).
* :class:`~quill.ui.bookmarks_ui.BookmarksMixin` -- one place you marked, and
  one list of them, shared between the apps (4.4, 4.5).

An app mixes in :class:`ListeningAppSupportMixin`, calls
:meth:`_init_app_support` before its windows exist and
:meth:`_register_app_support_commands` after its command registry does, and
appends the menu items with :mod:`quill.ui.support_menu`.
"""

from __future__ import annotations

from typing import Any

from quill.ui.bookmarks_ui import BookmarksMixin
from quill.ui.problems_dialog import RecentProblemsMixin
from quill.ui.quiet_hours_ui import QuietHoursMixin
from quill.ui.setup_transfer_ui import SetupTransferMixin
from quill.ui.undo_last_ui import UndoLastMixin


class ListeningAppSupportMixin(
    UndoLastMixin, RecentProblemsMixin, QuietHoursMixin, SetupTransferMixin, BookmarksMixin
):
    """Undo, Recent Problems, Quiet Hours, setup transfer and bookmarks."""

    def _init_app_support(self) -> None:
        """Claim the process-wide slots. Call before any window can offer them."""
        self._init_undo_last()

    def _register_app_support_commands(self, retries: Any = None) -> None:
        """Register the commands, and what this app can retry from the log.

        *retries* is the app's ``problem_retries`` module (Radio claims stream
        and download; Cast claims feed and download). None registers none,
        which is honest: a row whose kind nothing claims simply has no Retry.
        """
        self._register_undo_last_command()
        self._register_recent_problems_command()
        self._register_quiet_hours_commands()
        self._register_setup_transfer_commands()
        self._register_bookmark_commands()
        if retries is not None:
            retries.register(self)
