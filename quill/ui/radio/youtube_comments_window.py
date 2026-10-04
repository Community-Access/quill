"""YouTube Comments: a video's comments as a list you can read, search and copy.

One row per comment -- "author: first line ... (likes, when)" -- with replies
right after the comment they answer, each saying whose comment that was. The
selected comment is shown in full in a read-only box beside the list, where it
can be read a character at a time and copied. Nothing here speaks on its own
except the outcome of something the listener asked for: how many comments
arrived, how many match a search (once, after typing pauses), and failures.

Keyboard: Tab moves Search comments, Sort by, the list, the full text and the
buttons; Escape, Ctrl+W or Ctrl+F4 close the window and focus goes back where
it was when the window opened. Every fetch runs on the task manager; the
window never waits on the network.

The data work is pure and lives in :mod:`quill.core.radio.youtube_comments`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import youtube_comments as yc

TITLE = "YouTube Comments"

#: How long typing must pause before the list is filtered and the count said.
FILTER_DELAY_MS = 450

SORT_CHOICES: tuple[tuple[str, str], ...] = ((yc.TOP, "Top comments"), (yc.NEWEST, "Newest first"))


class YouTubeCommentsWindow:
    """The comments for one video, in a peer window."""

    def __init__(
        self,
        parent: Any,
        *,
        video_title: str,
        page_url: str,
        task_manager: Any,
        announce: Callable[[str], None],
        copy_text: Callable[[str], object] | None = None,
        on_failure: Callable[[str], None] | None = None,
        fetch: Any = None,
        return_focus: Any = None,
        account_app: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        # The app frame, read by youtube_comments_write while building.
        self.account_app = account_app
        self._title = video_title.strip() or "this video"
        self._page_url = page_url
        self._task_manager = task_manager
        self._announce = announce
        self._copy_text = copy_text
        self._on_failure = on_failure or (lambda _m: None)
        self._fetch = fetch
        self._return_focus = return_focus
        self._comments: list[yc.Comment] = []
        self._shown: list[yc.Comment] = []
        self._limit = yc.PAGE_SIZE
        self._sort = yc.TOP
        self._busy = False
        self._generation = 0

        self.frame = wx.Frame(parent, title=TITLE, style=wx.DEFAULT_FRAME_STYLE)
        self.frame.SetMinSize((560, 460))
        self._panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        self._build()
        self._timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, lambda _e: self.apply_filter(speak=True), self._timer)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)

    # -- construction ----------------------------------------------------------

    def _build(self) -> None:
        wx = self._wx
        panel = self._panel
        root = wx.BoxSizer(wx.VERTICAL)
        self._heading = wx.StaticText(panel, label=f"Comments on {self._title}")
        root.Add(self._heading, 0, wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Search co&mments:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._search = wx.TextCtrl(panel)
        self._search.SetName("Search comments")
        self._search.SetHelpText(
            "Type words to show only the comments that contain all of them, in "
            "the comment or its author's name. The list narrows as you type, and "
            "how many match is said once when you pause. Clear the box to see "
            "every comment again."
        )
        row.Add(self._search, 1, wx.LEFT | wx.RIGHT, 6)
        row.Add(wx.StaticText(panel, label="Sort &by:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._sort_choice = wx.Choice(panel, choices=[label for _v, label in SORT_CHOICES])
        self._sort_choice.SetSelection(0)
        self._sort_choice.SetName("Sort by")
        self._sort_choice.SetHelpText(
            "Top comments shows what YouTube ranks highest; Newest first shows the "
            "most recent. Changing it asks YouTube again."
        )
        row.Add(self._sort_choice, 0, wx.LEFT, 6)
        root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="&Comments:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._list.SetName("Comments")
        self._list.SetHelpText(
            "One comment per row: who wrote it, how it starts, its likes and when. "
            "A reply follows the comment it answers and says whose it was. Emoji "
            "are read as their names and web addresses as links. Tab to Full text "
            "to read the selected comment whole. Keys: Alt+M Search comments, "
            "Alt+B Sort by, Alt+L Load More, Alt+P Copy Comment, Escape closes."
        )
        root.Add(self._list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(panel, label="Full &text:"), 0, wx.LEFT | wx.TOP, 8)
        self._full = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._full.SetName("Full text of the selected comment")
        self._full.SetHelpText(
            "The selected comment in full, with its author, likes and when it was "
            "written. Read it with the arrow keys; it cannot be changed."
        )
        root.Add(self._full, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._more = wx.Button(panel, label="&Load More")
        self._more.SetHelpText(
            f"Asks YouTube for {yc.PAGE_SIZE} more comments, up to "
            f"{yc.MAX_COMMENTS}. The ones already here stay where they are."
        )
        self._copy = wx.Button(panel, label="Co&py Comment")
        self._copy.SetHelpText("Puts the selected comment, with its author, on the clipboard.")
        self._close = wx.Button(panel, wx.ID_CLOSE, label="Close")
        self._close.SetHelpText("Closes the comments and goes back to where you were.")
        for button in (self._more, self._copy):
            buttons.Add(button, 0, wx.RIGHT, 6)
        # Reply / Add a Comment / Delete My Comment, through the official
        # sign-in, when this copy can sign in at all (youtube_comments_write).
        from quill.ui.radio import youtube_comments_write

        youtube_comments_write.attach(self, panel, buttons)
        buttons.Add(self._close, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 8)
        panel.SetSizer(root)

        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, self._close, modeless=True)
        self._search.Bind(wx.EVT_TEXT, self._on_search_text)
        self._sort_choice.Bind(wx.EVT_CHOICE, self._on_sort)
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._show_selected())
        self._more.Bind(wx.EVT_BUTTON, lambda _e: self.load_more())
        self._copy.Bind(wx.EVT_BUTTON, lambda _e: self.copy_selected())
        self._update_buttons()

    # -- loading ---------------------------------------------------------------

    def start(self) -> None:
        """Fetch the first page. Called once the window is on screen."""
        self._announce(f"Fetching comments on {self._title}...")
        self._request(replace=True)

    def _request(self, *, replace: bool) -> None:
        if self._busy:
            return
        self._busy = True
        self._generation += 1
        generation = self._generation
        sort, limit, url, fetch = self._sort, self._limit, self._page_url, self._fetch
        self._update_buttons()

        def _work(**_kwargs: Any) -> object:
            return yc.fetch_comments(url, sort=sort, limit=limit, fetch=fetch)

        def _ok(_op: str, result: object) -> None:
            if generation != self._generation or not self._alive():
                return
            self._busy = False
            found = list(result) if isinstance(result, list) else []
            self.receive(found, replace=replace)

        def _failed(_op: str, error: BaseException) -> None:
            if generation != self._generation or not self._alive():
                return
            self._busy = False
            self._update_buttons()
            from quill.core.radio.youtube_requests import plain

            reason = plain(error) or "YouTube did not answer."
            # announce-punctuation: exempt -- the reason is its own sentence, ending in a period.
            self._announce(f"Comments could not be fetched. {reason}")
            self._on_failure(reason)

        self._task_manager.submit(
            "radio-youtube-comments", _work, on_success=_ok, on_failure=_failed
        )

    def receive(self, found: list[yc.Comment], *, replace: bool) -> None:
        """Show a fetched page and say what arrived, once."""
        before = len(self._comments)
        self._comments = found if replace else yc.merge(self._comments, found)
        self.apply_filter(speak=False)
        added = len(self._comments) - (0 if replace else before)
        if not self._comments:
            self._announce("There are no comments on this video yet.")
        elif replace:
            self._announce(f"{len(self._comments)} comments.")
        elif added > 0:
            self._announce(f"{added} more comments, {len(self._comments)} in all.")
        else:
            self._announce("That is every comment YouTube would give.")
        self._update_buttons()

    def load_more(self) -> None:
        nxt = yc.next_limit(self._limit)
        if not nxt:
            self._announce(f"That is the most Quill Radio reads, {yc.MAX_COMMENTS} comments.")
            return
        self._limit = nxt
        self._announce("Fetching more comments...")
        self._request(replace=False)

    def _on_sort(self, _event: Any = None) -> None:
        index = max(0, self._sort_choice.GetSelection())
        wanted = SORT_CHOICES[index][0]
        if wanted == self._sort:
            return
        self._sort = wanted
        self._limit = yc.PAGE_SIZE
        self._busy = False  # a new order supersedes whatever was in flight
        self._announce(f"Fetching {SORT_CHOICES[index][1].lower()}...")
        self._request(replace=True)

    # -- filtering and reading -------------------------------------------------

    def _on_search_text(self, _event: Any = None) -> None:
        """Restart the pause timer; the filter runs when typing stops."""
        self._timer.StartOnce(FILTER_DELAY_MS)

    def apply_filter(self, *, speak: bool) -> None:
        """Narrow the list to the search words; say the count if asked."""
        words = self._search.GetValue()
        keep = self._selected()
        before = list(self._shown)
        self._shown = yc.filter_comments(self._comments, words)
        if before and self._shown[: len(before)] == before:
            # Load More, or nothing changed: add the new rows at the end and
            # touch nothing else. Rebuilding the list would make a screen
            # reader read it again and could move the selection under the
            # listener's cursor; appending does neither.
            for comment in self._shown[len(before) :]:
                self._list.Append(yc.row_label(comment))
        else:
            self._list.Set([yc.row_label(comment) for comment in self._shown])
            index = self._shown.index(keep) if keep in self._shown else (0 if self._shown else -1)
            if index >= 0:
                self._list.SetSelection(index)
            self._show_selected()
        if speak and words.strip():
            count = len(self._shown)
            if not count:
                self._announce(f"No comments match {words.strip()}.")
            else:
                self._announce(
                    f"{count} of {len(self._comments)} comment"
                    f"{'' if len(self._comments) == 1 else 's'} match."
                )
        elif speak:
            self._announce(f"All {len(self._comments)} comments.")
        self._update_buttons()

    def _selected(self) -> yc.Comment | None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._shown):
            return self._shown[index]
        return None

    def _show_selected(self) -> None:
        comment = self._selected()
        self._full.SetValue(yc.full_text(comment) if comment is not None else "")
        self._update_buttons()

    def copy_selected(self) -> None:
        comment = self._selected()
        if comment is None:
            self._announce("Select a comment first.")
            return
        text = yc.full_text(comment)
        ok = self._copy_text(text) if self._copy_text is not None else _clipboard(self._wx, text)
        self._announce("Comment copied." if ok is not False else "The clipboard is busy.")

    def _update_buttons(self) -> None:
        self._copy.Enable(self._selected() is not None)
        self._more.Enable(
            not self._busy and bool(yc.next_limit(self._limit)) and bool(self._comments)
        )

    # -- window ----------------------------------------------------------------

    def _alive(self) -> bool:
        try:
            return bool(self.frame) and not self.frame.IsBeingDeleted()
        except RuntimeError:
            return False

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE or (event.ControlDown() and key in (ord("W"), wx.WXK_F4)):
            self.frame.Close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        self._generation += 1  # anything still in flight lands nowhere
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001 - a dying timer must not block closing
            pass
        target = self._return_focus
        event.Skip()
        if target is not None:
            self._wx.CallAfter(_refocus, target)


def _refocus(target: Any) -> None:
    """Put focus back where the window was opened from, if it still exists."""
    try:
        if target:
            target.SetFocus()
    except Exception:  # noqa: BLE001 - the opener may have closed meanwhile
        return


def _clipboard(wx: Any, text: str) -> bool:
    try:
        if not wx.TheClipboard.Open():
            return False
        try:
            return bool(wx.TheClipboard.SetData(wx.TextDataObject(text)))
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001 - a busy clipboard is an answer, not a crash
        return False


__all__ = ["TITLE", "YouTubeCommentsWindow"]
