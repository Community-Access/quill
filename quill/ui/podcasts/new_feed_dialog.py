"""Find This Show's New Feed: the search, the choice, and Replace Feed (check.md bug 8).

Reached from Feed Check, on a row whose feed is not coming back at its address
-- removed by the host, a domain that no longer exists, a web page where the
feed was, an empty feed. The search and the verification are
``quill/core/podcasts/new_feed_finder.py`` (wx-free, tested); this module is the
background task that runs it and the one small dialog that offers the answer.

The dialog is a list of verified candidates, each said as one row -- title,
publisher, how many episodes, the newest one's date, the host -- because the
date is what tells a revived show from a dead one that shares its name. Replace
Feed keeps every episode, play position and setting; only the address changes.
Nothing is replaced without that press.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["TITLE", "NewFeedDialog", "find_new_feed_for"]

#: The window title; a key in ``surface_help.PURPOSES``.
TITLE = "Find This Show's New Feed"


class NewFeedDialog:
    """``show()`` returns the chosen candidate's feed address, or ``""``."""

    def __init__(
        self,
        parent: Any,
        *,
        show_title: str,
        summary: str,
        candidates: list[Any],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._candidates = list(candidates)
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((620, 360))
        root = wx.BoxSizer(wx.VERTICAL)

        self._summary = wx.StaticText(self.dialog, label=summary)
        self._summary.SetHelpText(
            "What Cast found for this podcast, and anything a podcast directory could not answer."
        )
        root.Add(self._summary, 0, wx.EXPAND | wx.ALL, 10)

        # Label first, then the list: on wxMSW that order is the list's name.
        label = wx.StaticText(self.dialog, label=f"&Feeds that might be {show_title}:")
        root.Add(label, 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(
            self.dialog, choices=[candidate.describe() for candidate in self._candidates]
        )
        self._list.SetHelpText(
            "Each feed was found by looking up this show's title in the podcast "
            "directories, and was read to check it answers with episodes. The "
            "newest episode's date tells a show that carried on from an older one "
            "with the same name. Replace Feed switches this podcast to the selected "
            "feed and keeps everything you have already heard."
        )
        if self._candidates:
            self._list.SetSelection(0)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._replace_btn = wx.Button(self.dialog, wx.ID_OK, "&Replace Feed")
        self._replace_btn.SetHelpText(
            "Switch this podcast to the selected feed. Its episodes, play positions, "
            "notes and settings stay as they are; only the feed address changes, "
            "and the new feed is checked straight away."
        )
        self._replace_btn.Enable(bool(self._candidates))
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Leave this podcast's feed address as it is.")
        buttons.Add(self._replace_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizer(root)
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK if self._candidates else wx.ID_CANCEL,
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )

    def chosen_url(self) -> str:
        index = self._list.GetSelection()
        if 0 <= index < len(self._candidates):
            return str(self._candidates[index].feed_url)
        return ""

    def show(self) -> str:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            return self.chosen_url() if answer == self._wx.ID_OK else ""
        finally:
            self.dialog.Destroy()


def find_new_feed_for(host: Any, show_id: str, *, on_replaced: Callable[[], None]) -> None:
    """Search for *show_id*'s new feed in the background, then offer it.

    The search is the one Add Podcast runs, against the directories chosen
    there, and it happens only because somebody pressed this -- the same
    consent the rest of directory search rests on. Safe Mode does nothing.
    """
    library = host._podcast_library
    show = library.find_show(show_id)
    if show is None:
        return
    if getattr(host, "_safe_mode", False):
        host._announce("Finding podcasts is disabled in Safe Mode.")
        return
    from quill.core.podcasts import new_feed_finder
    from quill.ui.podcasts.preview_command import podcast_index_credentials

    key, secret = podcast_index_credentials()
    settings = getattr(library, "settings", None)
    source = str(getattr(settings, "directory_source", "both") or "both")
    title = str(show.title or "")
    # Said before, not after: the search takes a few seconds and reads feeds.
    host._announce(f"Looking for a new feed for {title}...")

    def _work(**_kwargs: object) -> new_feed_finder.FindResult:
        return new_feed_finder.find_new_feed(
            show, safe_mode=False, source=source, key=key, secret=secret
        )

    def _done(_op: str, found: new_feed_finder.FindResult) -> None:
        summary = found.summary(title)
        if not found.candidates:
            host._announce(summary)
            return
        dialog = NewFeedDialog(
            host.frame,
            show_title=title,
            summary=summary,
            candidates=found.candidates,
            announce=host._announce,
        )
        chosen = dialog.show()
        if not chosen:
            return
        new_feed_finder.replace_feed(library, show, chosen)
        host._save_podcast_library()
        host._announce(f"{title} now follows the new feed. Checking it now.")
        from quill.ui.podcasts.feed_refresh import refresh_feed

        refresh_feed(host, show_id)
        on_replaced()

    def _failed(_op: str, error: BaseException) -> None:
        from quill.core.podcasts.feed_problems import plain

        host._announce(f"Finding {title}'s new feed did not finish. {plain(error)}")

    host._task_manager.submit("podcast-find-new-feed", _work, on_success=_done, on_failure=_failed)
