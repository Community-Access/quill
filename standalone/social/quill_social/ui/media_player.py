"""Accessible media player dialog (PRD section 19).

A screen-reader-first playback surface over the deterministic player state
machine (PRD 19.2, 19.3). Playback is driven by :class:`NullMediaEngine` by
default -- so the dialog works with no libmpv installed -- and upgrades to the
libmpv backend only when :meth:`MpvMediaEngine.available` reports it is present.
Every transport control (play/pause, stop, seek, skip, speed, volume) is a
labelled, keyboard-reachable control, and a read-only status line reflects the
player state after each action via ``player_status_text`` (PRD 19.4).

When a transcript is supplied (PRD 19.5) its cues appear in a report list;
pressing Enter on a cue seeks playback to the cue start, and Quote time point
places a quotable ``"text @ mm:ss"`` string on :attr:`quoted_text`.
"""

from __future__ import annotations

import wx

from quill_social.model import Media
from quill_social.services import transcripts as transcripts_svc
from quill_social.services.media import (
    MpvMediaEngine,
    NullMediaEngine,
    PlayerState,
    Track,
    player_status_text,
)
from quill_social.services.transcripts import Transcript

_SPEEDS = ("0.5", "0.75", "1.0", "1.25", "1.5", "2.0")


def _fmt_ms(ms: int) -> str:
    """Format milliseconds as ``m:ss`` (or ``h:mm:ss``) for speech (PRD 19.4)."""
    total = max(0, int(ms)) // 1000
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _track_from_media(media: Media, has_transcript: bool) -> Track:
    return Track(
        uri=media.uri or media.local_path,
        title=media.caption or media.alt_text or media.media_id,
        kind=media.kind,
        duration_ms=media.duration_ms,
        has_transcript=has_transcript,
    )


class MediaPlayerDialog(wx.Dialog):
    """Keyboard-complete media player over :class:`PlayerState` (PRD 19)."""

    def __init__(self, parent, media, transcript: Transcript | None = None):
        super().__init__(
            parent,
            title="Media player",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        if isinstance(media, Media):
            media = [media]
        self._media: list[Media] = list(media or [])
        self._transcript = transcript
        self.quoted_text: str = ""

        # Default to the deterministic engine; only use libmpv if it is present.
        engine = MpvMediaEngine() if MpvMediaEngine.available() else NullMediaEngine()
        self.player = PlayerState(engine)
        tracks = [_track_from_media(m, transcript is not None) for m in self._media]
        if tracks:
            self.player.set_queue(tracks, start=0)

        outer = wx.BoxSizer(wx.VERTICAL)

        # Transport buttons.
        transport = wx.BoxSizer(wx.HORIZONTAL)
        self.play_btn = wx.Button(self, label="&Play/Pause")
        self.play_btn.SetName("Play or pause")
        self.stop_btn = wx.Button(self, label="&Stop")
        self.stop_btn.SetName("Stop")
        self.back_btn = wx.Button(self, label="Skip &back")
        self.back_btn.SetName("Skip back")
        self.fwd_btn = wx.Button(self, label="Skip &forward")
        self.fwd_btn.SetName("Skip forward")
        for b in (self.play_btn, self.stop_btn, self.back_btn, self.fwd_btn):
            transport.Add(b, 0, wx.RIGHT, 6)
        outer.Add(transport, 0, wx.ALL, 8)

        # Seek slider.
        outer.Add(wx.StaticText(self, label="Seek:"), 0, wx.LEFT, 8)
        dur = self.player.engine.duration_ms()
        self.seek = wx.Slider(
            self,
            value=0,
            minValue=0,
            maxValue=max(dur, 1000),
            style=wx.SL_HORIZONTAL,
        )
        self.seek.SetName("Seek position")
        outer.Add(self.seek, 0, wx.EXPAND | wx.ALL, 8)

        # Speed and volume.
        sv = wx.BoxSizer(wx.HORIZONTAL)
        sv.Add(
            wx.StaticText(self, label="Speed:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.speed = wx.Choice(self, choices=list(_SPEEDS))
        self.speed.SetName("Playback speed")
        self.speed.SetSelection(_SPEEDS.index("1.0"))
        sv.Add(self.speed, 0, wx.RIGHT, 12)
        sv.Add(
            wx.StaticText(self, label="Volume:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self.volume = wx.Slider(
            self, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL
        )
        self.volume.SetName("Volume")
        sv.Add(self.volume, 1)
        outer.Add(sv, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Status line.
        outer.Add(wx.StaticText(self, label="Status:"), 0, wx.LEFT, 8)
        self.status = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.status.SetName("Player status")
        outer.Add(self.status, 0, wx.EXPAND | wx.ALL, 8)

        # Transcript cues (optional).
        if self._transcript is not None:
            outer.Add(wx.StaticText(self, label="Transcript cues:"), 0, wx.LEFT, 8)
            self.cues = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
            self.cues.SetName("Transcript cues")
            self.cues.InsertColumn(0, "Start", width=90)
            self.cues.InsertColumn(1, "End", width=90)
            self.cues.InsertColumn(2, "Text", width=420)
            for cue in self._transcript.cues:
                idx = self.cues.InsertItem(self.cues.GetItemCount(), _fmt_ms(cue.start_ms))
                self.cues.SetItem(idx, 1, _fmt_ms(cue.end_ms))
                self.cues.SetItem(idx, 2, cue.text.replace("\n", " "))
            outer.Add(self.cues, 1, wx.EXPAND | wx.ALL, 8)
            self.quote_btn = wx.Button(self, label="&Quote time point")
            self.quote_btn.SetName("Quote time point")
            outer.Add(self.quote_btn, 0, wx.LEFT | wx.BOTTOM, 8)
            self.cues.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_cue_activated)
            self.quote_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_quote())
        else:
            self.cues = None

        close_btn = wx.Button(self, wx.ID_CANCEL, label="&Close")
        close_btn.SetName("Close")
        outer.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        self.SetSizer(outer)
        self.SetSize((720, 620))

        self.play_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_toggle())
        self.stop_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_stop())
        self.back_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_skip_back())
        self.fwd_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_skip_forward())
        self.seek.Bind(wx.EVT_SLIDER, lambda _e: self._on_seek())
        self.speed.Bind(wx.EVT_CHOICE, lambda _e: self._on_speed())
        self.volume.Bind(wx.EVT_SLIDER, lambda _e: self._on_volume())

        self._refresh_status()

    # -- transport -----------------------------------------------------------

    def _on_toggle(self) -> None:
        self.player.toggle()
        self._refresh_status()

    def _on_stop(self) -> None:
        self.player.stop()
        self._sync_seek()
        self._refresh_status()

    def _on_skip_back(self) -> None:
        self.player.skip_back()
        self._sync_seek()
        self._refresh_status()

    def _on_skip_forward(self) -> None:
        self.player.skip_forward()
        self._sync_seek()
        self._refresh_status()

    def _on_seek(self) -> None:
        self.player.seek_ms(self.seek.GetValue())
        self._refresh_status()

    def seek_to(self, ms: int) -> None:
        """Seek playback to ``ms`` and update the slider and status (test hook)."""
        self.player.seek_ms(ms)
        self._sync_seek()
        self._refresh_status()

    def _on_speed(self) -> None:
        self.player.set_speed(float(_SPEEDS[self.speed.GetSelection()]))
        self._refresh_status()

    def _on_volume(self) -> None:
        self.player.set_volume(self.volume.GetValue())
        self._refresh_status()

    # -- transcript ----------------------------------------------------------

    def _on_cue_activated(self, event) -> None:
        if self._transcript is None:
            return
        idx = event.GetIndex()
        if 0 <= idx < len(self._transcript.cues):
            self.seek_to(self._transcript.cues[idx].start_ms)

    def _on_quote(self) -> None:
        if self._transcript is None:
            return
        self.quoted_text = transcripts_svc.quote_timepoint(
            self._transcript, self.player.engine.position_ms()
        )
        self._refresh_status()

    # -- status --------------------------------------------------------------

    def _sync_seek(self) -> None:
        dur = self.player.engine.duration_ms()
        self.seek.SetMax(max(dur, 1000))
        self.seek.SetValue(min(self.player.engine.position_ms(), self.seek.GetMax()))

    def _refresh_status(self) -> None:
        self.status.SetValue(player_status_text(self.player))
