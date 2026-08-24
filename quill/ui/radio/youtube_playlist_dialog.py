"""Pick videos out of a YouTube playlist to add as stations.

A playlist link is a *list*, not a station, so pasting one into Add Custom
Station would save something that could never play. This is where a playlist
goes instead: its videos, in the uploader's own running order, as a list you can
read and choose from.

Accessibility shapes the whole dialog:

* The list is a plain ``wx.ListBox`` with extended selection -- one focusable
  item per video whose label already says everything ("3. Introducing layers,
  5 minutes 31 seconds"), so a screen reader reads a row without the user having
  to arrow across columns. Deliberately not a checkbox list: checkbox state in a
  wx list control is announced inconsistently across readers, and Shift+arrow /
  Ctrl+arrow selection is what people already know.
* Nothing is ever added silently. Every action announces what it did, including
  how many were skipped as duplicates, because "Add All" on a fifty-video
  playlist is otherwise indistinguishable from a button that did nothing.
* The order is the uploader's. A series is meant to be watched in order, and
  re-sorting it would quietly destroy the one piece of structure a playlist has.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.radio.youtube import YouTubePlaylistEntry
from quill.ui.dialog_contract import apply_modal_ids


def describe_entry(index: int, entry: YouTubePlaylistEntry) -> str:
    """The spoken row label for one playlist entry (pure, so it is testable).

    Duration is spelled in words rather than punctuation because the row is read
    aloud verbatim: "5:31" is fine on screen, but a bare colon-separated number
    is ambiguous to a reader that has not been told it is a time.
    """
    title = entry.title.strip() or entry.page_url
    parts = [f"{index}. {title}"]
    if entry.duration_ms > 0:
        total_seconds = entry.duration_ms // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''} {minutes} minutes")
        elif minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} seconds")
        else:
            parts.append(f"{seconds} seconds")
    if entry.uploader.strip():
        parts.append(entry.uploader.strip())
    return ", ".join(parts)


class YouTubePlaylistDialog:
    """Choose videos from a resolved playlist and add them as stations."""

    def __init__(
        self,
        parent: object,
        *,
        entries: Sequence[YouTubePlaylistEntry],
        playlist_title: str,
        show_modal_dialog: Callable,
        announce: Callable[[str], None],
        add_stations: Callable[[list[YouTubePlaylistEntry]], tuple[int, int]],
    ) -> None:
        import wx

        self._wx = wx
        self._entries = list(entries)
        self._announce = announce
        self._add_stations = add_stations
        self._show_modal = show_modal_dialog
        self._title = "Add from YouTube Playlist"

        self.dialog = wx.Dialog(
            parent,
            title=self._title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(620, 480))
        self._build_ui(playlist_title)

    def _build_ui(self, playlist_title: str) -> None:
        wx = self._wx
        panel = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        heading = playlist_title.strip() or "YouTube playlist"
        summary = wx.StaticText(
            panel, label=f"{heading} -- {len(self._entries)} videos, in the playlist's own order."
        )
        root.Add(summary, 0, wx.ALL, 8)

        label = wx.StaticText(panel, label="&Videos:")
        root.Add(label, 0, wx.LEFT, 8)
        self._list = wx.ListBox(
            panel,
            choices=[describe_entry(i, e) for i, e in enumerate(self._entries, start=1)],
            style=wx.LB_EXTENDED,
        )
        self._list.SetName("Videos in this playlist")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        hint = wx.StaticText(
            panel,
            label=(
                "Select one or more videos, or use Add All. "
                "Each becomes a station you can play, favorite, and record."
            ),
        )
        root.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(panel, label="Add &Selected")
        self._add_btn.SetHelpText(
            "Adds the checked entries to your favorites, each as its own row."
        )
        self._add_all_btn = wx.Button(panel, label="Add &All")
        self._add_all_btn.SetHelpText("Adds every entry of the playlist to your favorites.")
        close_btn = wx.Button(panel, wx.ID_CLOSE, label="C&lose")
        close_btn.SetHelpText("Closes without adding anything more.")
        for button in (self._add_btn, self._add_all_btn, close_btn):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)

        apply_modal_ids(
            self.dialog,
            affirmative_id=close_btn.GetId(),
            escape_id=close_btn.GetId(),
        )
        self.dialog.SetSizer(root)

        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._update_buttons())
        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add_selected)
        self._add_all_btn.Bind(wx.EVT_BUTTON, self._on_add_all)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

        self._add_all_btn.Enable(bool(self._entries))
        self._update_buttons()
        wx.CallAfter(self._list.SetFocus)

    def _update_buttons(self) -> None:
        self._add_btn.Enable(bool(self._list.GetSelections()))

    def _on_add_selected(self, _event: object) -> None:
        chosen = [self._entries[i] for i in self._list.GetSelections() if i < len(self._entries)]
        if not chosen:
            self._announce("Select at least one video first.")
            return
        self._report(*self._add_stations(chosen), asked=len(chosen))

    def _on_add_all(self, _event: object) -> None:
        if not self._entries:
            return
        self._report(*self._add_stations(list(self._entries)), asked=len(self._entries))

    def _report(self, added: int, skipped: int, *, asked: int) -> None:
        """Say exactly what happened -- including nothing, and why."""
        if added and skipped:
            message = (
                f"Added {added} station{'s' if added != 1 else ''}. "
                f"{skipped} already in your favorites."
            )
        elif added:
            message = f"Added {added} station{'s' if added != 1 else ''}."
        elif skipped:
            message = (
                f"Nothing added -- {'all ' if skipped == asked else ''}"
                f"{skipped} already in your favorites."
            )
        else:
            message = "Nothing was added."
        self._announce(message)

    def show(self) -> int:
        result = self._show_modal(self.dialog, self._title)
        self.dialog.Destroy()
        return result
