"""The wider smart-playlist rules, and the count that makes them usable.

Seven controls and one number. The controls are the rules the model gained --
match mode, folders, download state, notes, text, progress, limit -- and the
number is **how many episodes the current rules match right now**.

**The preview count is the point.** A set of filters with no feedback is a
guess somebody has to save, close, reopen and check: four steps to answer "did I
mean that?". With a count that moves as the rules change, the same question is
answered before the dialog is even dismissed. It is the difference between a
rule builder people trust and one they abandon, and it matters more here than
in a sighted app -- there is no list quietly filtering itself in the background
to glance at.

**"Any" is where match mode earns its place.** Everything was implicitly ANDed,
which is right for narrowing and useless for the other half of what people want:
"anything from these three shows, *or* anything I have bookmarked" cannot be
said with AND at all.

Its own module because ``playlist_rules_dialog`` is near its GATE-11 ceiling,
and because these rows are a coherent set: they arrived together and they are
read together.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts.models_playlists import (
    PLAYLIST_DOWNLOAD_MODES,
    PLAYLIST_MATCH_MODES,
    PLAYLIST_NOTE_MODES,
    PLAYLIST_PROGRESS_MODES,
    PlaylistRules,
)

__all__ = ["ExtraRules"]

_MATCH_LABELS = ("Match all of these rules", "Match any one of these rules")
_DOWNLOAD_LABELS = ("Downloaded or not", "Only downloaded", "Only not downloaded")
_NOTE_LABELS = ("With or without notes", "Only with a note", "Only without a note")
_PROGRESS_LABELS = ("Anywhere", "Not started", "Started", "Finished")


class ExtraRules:
    """Builds the extra rows into *root*, and reads them back."""

    def __init__(
        self,
        dialog: Any,
        root: Any,
        rules: PlaylistRules,
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._preview_source: Callable[[], int] | None = None

        box = wx.StaticBoxSizer(wx.VERTICAL, dialog, "More rules")
        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        self._match = self._choice(
            dialog,
            grid,
            "&Match:",
            _MATCH_LABELS,
            PLAYLIST_MATCH_MODES.index(rules.match_mode)
            if rules.match_mode in PLAYLIST_MATCH_MODES
            else 0,
            "Whether an episode has to satisfy every rule, or just one of them",
        )
        self._download = self._choice(
            dialog,
            grid,
            "&Downloads:",
            _DOWNLOAD_LABELS,
            PLAYLIST_DOWNLOAD_MODES.index(rules.download_state)
            if rules.download_state in PLAYLIST_DOWNLOAD_MODES
            else 0,
            "Whether the episode has been downloaded to this computer",
        )
        self._note = self._choice(
            dialog,
            grid,
            "&Notes:",
            _NOTE_LABELS,
            PLAYLIST_NOTE_MODES.index(rules.has_note)
            if rules.has_note in PLAYLIST_NOTE_MODES
            else 0,
            "Whether you have left a timestamped note on the episode",
        )
        self._progress = self._choice(
            dialog,
            grid,
            "&Progress:",
            _PROGRESS_LABELS,
            PLAYLIST_PROGRESS_MODES.index(rules.progress)
            if rules.progress in PLAYLIST_PROGRESS_MODES
            else 0,
            "Where your playhead is in the episode. Not the same as the played mark",
        )

        grid.Add(
            wx.StaticText(dialog, label="Title or notes con&tain:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._text = wx.TextCtrl(dialog, value=rules.text_contains)
        self._text.SetName(
            "Words to look for in the episode title or its show notes. Leave "
            "empty to match everything."
        )
        grid.Add(self._text, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(dialog, label="Most episodes (&0 = no limit):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._limit = wx.SpinCtrl(dialog, min=0, max=500, initial=rules.item_limit)
        self._limit.SetName(
            "At most this many episodes, taken after sorting -- so ten, sorted "
            "newest first, is the ten newest."
        )
        grid.Add(self._limit, 0)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 6)

        self._preview = wx.StaticText(dialog, label="")
        self._preview.SetName("How many episodes these rules match right now")
        box.Add(self._preview, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        root.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        for control in (self._match, self._download, self._note, self._progress):
            control.Bind(wx.EVT_CHOICE, lambda _e: self.refresh_preview())
        self._text.Bind(wx.EVT_TEXT, lambda _e: self.refresh_preview())
        self._limit.Bind(wx.EVT_SPINCTRL, lambda _e: self.refresh_preview())

    def _choice(
        self,
        dialog: Any,
        grid: Any,
        label: str,
        choices: tuple[str, ...],
        selection: int,
        name: str,
    ) -> Any:
        wx = self._wx
        grid.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        control = wx.Choice(dialog, choices=list(choices))
        control.SetName(name)
        control.SetSelection(selection)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def set_preview_source(self, source: Callable[[], int]) -> None:
        """Hand in the thing that can count, and show a first number."""
        self._preview_source = source
        self.refresh_preview()

    def refresh_preview(self) -> None:
        """Recount and relabel. Silent about a count it cannot get."""
        if self._preview_source is None:
            return
        count = self._preview_source()
        if count < 0:
            self._preview.SetLabel("")
            return
        self._preview.SetLabel(f"Matches {count} episode{'' if count == 1 else 's'} right now.")

    def values(self) -> dict[str, Any]:
        """The extra rules, ready to hand to ``PlaylistRules``."""
        return {
            "match_mode": PLAYLIST_MATCH_MODES[max(0, self._match.GetSelection())],
            "download_state": PLAYLIST_DOWNLOAD_MODES[max(0, self._download.GetSelection())],
            "has_note": PLAYLIST_NOTE_MODES[max(0, self._note.GetSelection())],
            "progress": PLAYLIST_PROGRESS_MODES[max(0, self._progress.GetSelection())],
            "text_contains": self._text.GetValue().strip(),
            "item_limit": int(self._limit.GetValue()),
        }
