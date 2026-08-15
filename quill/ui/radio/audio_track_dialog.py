"""Choosing an audio track -- and finding the described one.

The window behind **Playback > Audio and Described Audio...**. A list of every
audio rendition a video publishes, each named the way a person would say it, and
the described one -- the narration that says what is happening on screen --
called out first and by name rather than hidden among "Track 2, Track 3".

Two decisions in here are the whole feature:

* **The described track is named and listed first.** Not promoted silently: the
  ordinary track is still there and still labelled, so somebody who did not want
  description is not surprised by it. But if a described track exists, the window
  says so in its own heading, before the list, because that is the single fact
  the listener opened this window to learn.
* **When there is none, the window still opens and says so.** It reports what the
  video *does* have. A greyed-out menu item would leave somebody guessing whether
  the video lacks description or the app lacks the feature, and those are very
  different things to know.

Same shape as ``chapter_list_dialog``: a plain ``wx.ListBox``, Enter or the
button to choose, and every row a whole sentence rather than a set of columns.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.radio.audio_tracks import described_track, summarise
from quill.ui.dialog_contract import apply_modal_ids

#: What the window says above the list when a described track exists. The point
#: of the whole feature, stated before anything else in the reading order.
DESCRIBED_HEADING = "Described audio is available for this video."

#: And when there is not one. Never a greyed-out command.
NO_DESCRIBED_HEADING = "No described audio was published for this video."


def row_label(track: Any, *, current: bool = False) -> str:
    """One track as a whole sentence, the way the list speaks it."""
    label = track.display_name
    if track.is_described:
        label = f"{label} -- narrates what is on screen"
    return f"{label} (playing now)" if current else label


class AudioTrackDialog:
    """Pick an audio rendition of the playing video."""

    def __init__(
        self,
        parent: Any,
        *,
        tracks: Sequence[Any],
        current: Any = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        announce: Callable[[str], None] | None = None,
        play_track: Callable[[Any], bool] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._play_track = play_track
        self._show_modal_dialog = show_modal_dialog
        # Described first, everything else in the order the video published it.
        # Ordering, not filtering: the ordinary track is still on the list.
        self._tracks = sorted(tracks, key=lambda t: not t.is_described)

        self._dialog = wx.Dialog(parent, title="Audio and Described Audio")
        root = wx.BoxSizer(wx.VERTICAL)

        described = described_track(list(self._tracks))
        heading = DESCRIBED_HEADING if described is not None else NO_DESCRIBED_HEADING
        root.Add(wx.StaticText(self._dialog, label=heading), 0, wx.ALL, 10)

        root.Add(
            wx.StaticText(self._dialog, label="Audio &tracks:"),
            0,
            wx.LEFT | wx.RIGHT,
            10,
        )
        self._list = wx.ListBox(
            self._dialog,
            choices=[row_label(t, current=t is current) for t in self._tracks],
        )
        self._list.SetName(
            "Audio tracks for this video; a described track narrates what is on screen"
        )
        if self._tracks:
            # Land on the described one where there is one: it is what somebody
            # opening this window is overwhelmingly likely to want.
            self._list.SetSelection(0)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = wx.Button(self._dialog, wx.ID_OK, "&Play This Track")
        self._play_btn.Enable(bool(self._tracks) and play_track is not None)
        buttons.Add(self._play_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_CANCEL, "Cl&ose"), 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        self._dialog.Fit()
        apply_modal_ids(self._dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.play_selected())
        self._play_btn.Bind(wx.EVT_BUTTON, lambda _e: self.play_selected())
        self._list.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    def show(self) -> int:
        """Show the window, and always destroy it afterwards (A11Y-4)."""
        title = "Audio and Described Audio"
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, title))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()

    def play_selected(self) -> bool:
        """Switch to the highlighted track. True when playback moved."""
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._tracks) or self._play_track is None:
            return False
        track = self._tracks[index]
        if not self._play_track(track):
            self._announce(f"{track.display_name} could not be played.")
            return False
        if track.is_described:
            self._announce("Playing the described audio track.")
        else:
            self._announce(f"Playing {track.display_name}.")
        self._dialog.EndModal(self._wx.ID_OK)
        return True


def summary_for(tracks: Sequence[Any]) -> str:
    """What to announce when the command is used and no window is warranted."""
    return summarise(list(tracks))
