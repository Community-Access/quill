"""See what a podcast actually is, before subscribing to it.

Add Podcast subscribed straight from a search result, so the only way to find
out what a feed held was to subscribe and then unsubscribe -- which leaves an
episode list, possibly some downloads, and a library entry somebody has to
undo. **Subscribing from a title alone is the thing that produces regret**, and
a title is all a search result shows.

So: a read-only look first. Title, publisher, how many episodes, the show's own
description as a text field somebody arrows through, and the ten most recent
episode titles with their dates -- which between them answer "is this the show
I meant, is it still running, and is it in my language".

**A list, not a preview player.** Playing an episode from here would need the
audio, the player and a position to not save, and the question being asked is
"is this the right show", which the titles answer. The subscribe button is right
there for the other question.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = ["FeedPreviewDialog"]

#: How many episode titles are shown. Enough to see the run of a show and its
#: cadence; not so many that the list becomes the thing being read.
PREVIEW_EPISODES = 10


class FeedPreviewDialog:
    """Read-only look at a feed. ``show()`` returns True when Subscribe was pressed."""

    def __init__(
        self,
        parent: object,
        *,
        feed: Any,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._subscribe = False
        title = str(getattr(feed, "title", "") or "This podcast")
        episodes = list(getattr(feed, "episodes", []) or [])

        self.dialog = wx.Dialog(
            parent,
            title=f"Preview -- {title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        publisher = str(getattr(feed, "author", "") or getattr(feed, "publisher", "") or "")
        headline = title if not publisher else f"{title}, by {publisher}"
        count = len(episodes)
        headline += f". {count} episode{'' if count == 1 else 's'}."
        heading = wx.StaticText(self.dialog, label=headline)
        heading.SetName("What this podcast is")
        root.Add(heading, 0, wx.ALL | wx.EXPAND, 10)

        root.Add(
            wx.StaticText(self.dialog, label="&About this podcast:"), 0, wx.LEFT | wx.RIGHT, 10
        )
        self._description = wx.TextCtrl(
            self.dialog,
            value=_plain_text(str(getattr(feed, "description", "") or "No description.")),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self._description.SetName("The podcast's own description")
        root.Add(self._description, 1, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(self.dialog, label="&Recent episodes:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._episodes = wx.ListBox(
            self.dialog, choices=[_episode_label(row) for row in episodes[:PREVIEW_EPISODES]]
        )
        self._episodes.SetName("The ten most recent episodes")
        root.Add(self._episodes, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        subscribe_btn = wx.Button(self.dialog, wx.ID_OK, "&Subscribe")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "&Close")
        buttons.Add(subscribe_btn, 0, wx.RIGHT, 6)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        subscribe_btn.Bind(wx.EVT_BUTTON, self._on_subscribe)
        # A wx.Dialog answers ID_CANCEL for free, but this surface can be shown
        # modelessly by a caller that has one, and a Close that does nothing is
        # the failure test_close_button_contract exists to catch.
        bind_close_button(self.dialog, close_btn, wx.ID_CANCEL)
        self._headline = headline

    def _on_subscribe(self, event: Any) -> None:
        self._subscribe = True
        event.Skip()

    def show(self) -> bool:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Subscribe",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        self._announce(f"Previewing {self._headline}")
        try:
            answer = show_modal_dialog(self.dialog, "Preview", announce=self._announce)
            return bool(self._subscribe and answer == self._wx.ID_OK)
        finally:
            self.dialog.Destroy()


def _plain_text(raw: str) -> str:
    """A feed description as something a text field can hold.

    Feeds put HTML in here more often than not, and a read-only field showing
    ``<p>`` tags is a field somebody has to read around.
    """
    import html
    import re

    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", raw)
    text = re.sub(r"(?i)</\s*(p|div|li)\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip() or "No description."


def _episode_label(episode: Any) -> str:
    """One episode row: what it is and when it came out, as one sentence."""
    title = str(getattr(episode, "title", "") or "Untitled episode")
    published = str(getattr(episode, "published", "") or "").strip()
    return f"{title}, {published[:10]}" if published else title
