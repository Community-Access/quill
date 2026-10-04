"""**About This Episode** -- everything the feed said that nothing was reading.

The window behind *Episode > About This Episode...*. One tab per kind of thing
the podcast published: who is on it, the moments it marked, a live stream it is
carrying, other versions of the audio, the shows it recommends, where to support
it, where it is about.

Three decisions carry this window:

* **A tab exists only when it has something in it.** No empty People tab on a
  podcast that publishes no credits. Arrowing through tabs that all say "none"
  is a worse way to learn there is nothing than being told once.
* **The button names the thing it is about to do**, and changes as the highlight
  moves: *Open in Browser*, *Play*, *Follow This Podcast*, *Go There*. On a row with
  nothing to do it reads *Nothing to Open* and is disabled -- because a control
  that silently declines is worse than one not offered.
* **Every row is a whole sentence.** No columns: "Jane Smith, guest (this
  episode)" is one thing to hear, and a Name column plus a Role column is two.

The tabs are a real ``wx.Notebook``, so they are reached with Ctrl+Tab and
announced as tabs, and each page is a plain ``wx.ListBox`` -- the same shape as
the chapter and audio-track lists, for the same reason.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts.extras import (
    ACTION_JUMP,
    ACTION_OPEN,
    ACTION_PLAY,
    ACTION_SUBSCRIBE,
    Extras,
    Row,
)

TITLE = "About This Episode"

#: What the window says when the feed published none of it. Never a greyed-out
#: menu item: "this podcast publishes no extra details" and "QUILL cannot read
#: them" are very different facts, and only one of them is true.
NOTHING_HEADING = (
    "This podcast published no extra details for this episode -- "
    "no credits, no marked moments, and no links."
)


class EpisodeExtrasWindow:
    """One tab per kind of extra the podcast published -- a peer window.

    Made once (qc.md Phase 4). Asked for again, for this episode or another,
    the same window is raised and its tabs rebuilt from :meth:`load`; the
    action button simply acts, and the window stays open beside the library
    until Escape or Close hides it.
    """

    TITLE = TITLE
    MENU_TITLE = "&Episode"

    def __init__(
        self,
        parent: Any,
        *,
        extras: Extras,
        episode_title: str = "",
        announce: Callable[[str], None] | None = None,
        open_url: Callable[[str], bool] | None = None,
        play_url: Callable[[str, str], bool] | None = None,
        subscribe_feed: Callable[[str], bool] | None = None,
        jump_to: Callable[[str], bool] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._lists: list[Any] = []
        self._notebook: Any = None
        self._heading: Any = None

        self.frame = wx.Frame(parent, title=TITLE, size=(660, 480))
        self.frame.SetMinSize((620, 440))
        self._panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)
        self._body = wx.BoxSizer(wx.VERTICAL)
        root.Add(self._body, 1, wx.EXPAND)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._action_btn = wx.Button(self._panel, label="&Open in Browser")
        self._action_btn.SetHelpText(
            "Does what its name says to the highlighted row: opens the link, plays "
            "the stream, follows the podcast, or plays from the bookmark. Its name "
            "changes as you move through the list."
        )
        buttons.Add(self._action_btn, 0, wx.RIGHT, 6)
        close_btn = wx.Button(self._panel, label="Close")
        self._close_btn = close_btn
        close_btn.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close_btn, modeless=True)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.ALL, 12)
        self._panel.SetSizer(root)

        self._action_btn.Bind(wx.EVT_BUTTON, lambda _e: self.activate_selected())
        self.load(
            extras,
            episode_title=episode_title,
            open_url=open_url,
            play_url=play_url,
            subscribe_feed=subscribe_feed,
            jump_to=jump_to,
        )
        self.frame.CentreOnParent()

    def focus_target(self) -> Any:
        if self._lists and self._notebook is not None:
            page = max(0, int(self._notebook.GetSelection()))
            return self._lists[min(page, len(self._lists) - 1)]
        # Nothing published: the heading says so, and Close is the one thing to do.
        return self._close_btn

    def load(
        self,
        extras: Extras,
        *,
        episode_title: str = "",
        open_url: Callable[[str], bool] | None = None,
        play_url: Callable[[str, str], bool] | None = None,
        subscribe_feed: Callable[[str], bool] | None = None,
        jump_to: Callable[[str], bool] | None = None,
    ) -> None:
        """Show *extras* -- the first time, or for whichever episode is asked next."""
        from quill.ui.dialog_contract import apply_listbox_activation

        wx = self._wx
        self._extras = extras
        self._open_url = open_url
        self._play_url = play_url
        self._subscribe_feed = subscribe_feed
        self._jump_to = jump_to
        self.frame.SetTitle(TITLE if not episode_title else f"{TITLE} -- {episode_title}")
        self._body.Clear(delete_windows=True)
        self._lists = []
        self._notebook = None
        self._heading = None
        panel = self._panel

        if extras.is_empty:
            self._heading = wx.StaticText(panel, label=NOTHING_HEADING)
            self._body.Add(self._heading, 0, wx.ALL, 12)
        else:
            self._notebook = wx.Notebook(panel)
            self._notebook.SetName("Details this podcast published about this episode")
            self._notebook.SetHelpText(
                "One tab for each kind of thing this podcast published. Ctrl+Tab "
                "moves between them."
            )
            for section in extras.sections:
                page = wx.Panel(self._notebook)
                page_sizer = wx.BoxSizer(wx.VERTICAL)
                page_sizer.Add(wx.StaticText(page, label=section.heading), 0, wx.ALL | wx.EXPAND, 8)
                listbox = wx.ListBox(page, choices=[row.label for row in section.rows])
                listbox.SetName(f"{section.title}: {section.heading}")
                listbox.SetHelpText(
                    "Each row is one thing the podcast published. The button below "
                    "says what Enter on it does."
                )
                if section.rows:
                    listbox.SetSelection(0)
                page_sizer.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
                page.SetSizer(page_sizer)
                self._notebook.AddPage(page, section.title)
                self._lists.append(listbox)
                listbox.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_button())
                # A frame has no default button, so Enter on a row is wired here.
                apply_listbox_activation(listbox, lambda _e: self.activate_selected())
            self._body.Add(self._notebook, 1, wx.EXPAND | wx.ALL, 8)
            # Built after the buttons, so put it back ahead of them in Tab order.
            self._notebook.MoveBeforeInTabOrder(self._action_btn)
            self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, lambda _e: self._sync_button())
        self._panel.Layout()
        self._sync_button()

    def selected_row(self) -> Row | None:
        """The highlighted row on the visible tab, if there is one."""
        if self._notebook is None or not self._lists:
            return None
        page = int(self._notebook.GetSelection())
        if page < 0 or page >= len(self._lists):
            return None
        index = int(self._lists[page].GetSelection())
        rows = self._extras.sections[page].rows
        if index < 0 or index >= len(rows):
            return None
        return rows[index]

    def _sync_button(self) -> None:
        """Name the button after the highlighted row, or disable and say so.

        The label is the affordance. A generic *OK* on a row that does nothing
        is a promise the window cannot keep.
        """
        row = self.selected_row()
        if row is None:
            self._action_btn.SetLabel("Nothing to Open")
            self._action_btn.Enable(False)
            return
        self._action_btn.SetLabel(row.button_label)
        self._action_btn.Enable(row.is_actionable and self._handler_for(row) is not None)

    def _handler_for(self, row: Row) -> Callable[[], bool] | None:
        if row.action == ACTION_OPEN and self._open_url is not None:
            return lambda: bool(self._open_url and self._open_url(row.target))
        if row.action == ACTION_PLAY and self._play_url is not None:
            return lambda: bool(self._play_url and self._play_url(row.target, row.label))
        if row.action == ACTION_SUBSCRIBE and self._subscribe_feed is not None:
            return lambda: bool(self._subscribe_feed and self._subscribe_feed(row.target))
        if row.action == ACTION_JUMP and self._jump_to is not None:
            return lambda: bool(self._jump_to and self._jump_to(row.target))
        return None

    def activate_selected(self) -> bool:
        """Do what the button says. Always speaks the outcome, either way.

        In a peer the button simply acts: the window stays open, so a listener
        can try a second link or bookmark without opening it again.
        """
        row = self.selected_row()
        if row is None or not row.is_actionable:
            return False
        handler = self._handler_for(row)
        if handler is None:
            return False
        if not handler():
            self._announce(f"{row.label} could not be opened.")
            return False
        if row.action == ACTION_SUBSCRIBE:
            # Deliberately silent here: subscribing fetches the feed off the UI
            # thread, so the only honest thing to say now is "fetching", and the
            # caller already said it. Announcing success before the fetch
            # returns would be a guess.
            pass
        elif row.action == ACTION_PLAY:
            self._announce(f"Playing {row.label}.")
        elif row.action == ACTION_JUMP:
            self._announce(f"Playing from {row.label}.")
        else:
            self._announce("Opened in your browser.")
        return True
