"""A compact, always-on-top mini-player window (PRD Section 9.4).

A small floating frame that controls the main player's transport so playback
stays reachable while the reader works in another window. It drives the shared
:class:`~quill.ui.audio_studio.player_panel.PlayerPanel` (Play/Pause and chapter
moves), so there is one playback session -- no second audio stream.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.ui.accessible_names import set_accessible_name


class MiniPlayerFrame(wx.Frame):
    """Compact transport controls for the shared player panel."""

    def __init__(
        self,
        parent: wx.Window,
        player: object,
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="Mini Player",
            style=wx.CAPTION | wx.CLOSE_BOX | wx.FRAME_FLOAT_ON_PARENT | wx.STAY_ON_TOP,
        )
        self._player = player
        self._announce = announce

        panel = wx.Panel(self)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler, name in (
            ("&Play/Pause", self._toggle, "mini.play"),
            ("Pre&vious chapter", self._prev, "mini.prev"),
            ("Ne&xt chapter", self._next, "mini.next"),
        ):
            button = wx.Button(panel, label=label, name=name)
            set_accessible_name(button, label.replace("&", ""))
            button.Bind(wx.EVT_BUTTON, handler)
            row.Add(button, 0, wx.ALL, 4)
        panel.SetSizerAndFit(row)
        self.Fit()

    def _toggle(self, _event: wx.CommandEvent) -> None:
        self._player.toggle()

    def _prev(self, _event: wx.CommandEvent) -> None:
        index = self._player.current_chapter_index()
        self._player.play_chapter(max(0, index - 1))

    def _next(self, _event: wx.CommandEvent) -> None:
        index = self._player.current_chapter_index()
        self._player.play_chapter(index + 1)


__all__ = ["MiniPlayerFrame"]
