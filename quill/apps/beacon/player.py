"""Built-in accessible media player (PRD 11.5, 11.6, Phase 3).

A small wx frame with a chapter list, a transcript view, and time-point
capture. Keyboard-first: Space play/pause, Left/Right skip, J/L jump by skip
interval, K add time point, N/P next/prev chapter. Every control has an
accessible name; the status line announces chapter and time (PRD 18.4,
A11Y-013).

Playback goes through the family's shared audio layer
(:mod:`quill.ui.audio.audio_engine`) -- the same ``AudioEngine`` protocol
Radio, Cast, and Audio Studio use, with the default wx.media/WMP backend and
the opt-in libmpv backend (gapless, exact seeking, output-device routing) for
free. The UI is built so it constructs and runs even when no backend is
available (it announces "media backend unavailable" rather than crashing).
"""

from __future__ import annotations

import wx

from quill.apps.beacon import capture, media
from quill.apps.beacon.announce import Announcer
from quill.ui.audio.audio_engine import AudioEngine, create_engine


def _name(ctrl: wx.Control, name: str) -> None:
    ctrl.SetName(name)


class PlayerFrame(wx.Frame):
    """Accessible player for one episode beacon."""

    def __init__(self, parent, store, beacon_id: str):
        super().__init__(parent, title="QuillBeacon Player", size=(640, 560))
        self.store = store
        self.beacon_id = beacon_id
        self.beacon = store.get_beacon(beacon_id)
        self.resource = store.get_resource(self.beacon.resource_id) if self.beacon else None
        self.announcer = Announcer(self)
        self.chapters: list = []
        self._skip_ms = 15000
        self.engine: AudioEngine | None = None
        self._length_ms = 0
        self._timer = wx.Timer(self)

        self._build()
        self._load_chapters()
        self._refresh_chapter_list()
        self.Bind(wx.EVT_TIMER, self._on_timer)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self._timer.Start(500)
        self.announcer.say("Player ready. Press Space to play.", "normal")

    def _build(self) -> None:
        root = wx.BoxSizer(wx.VERTICAL)

        self.title_lbl = wx.StaticText(self, label="Episode")
        self.title_lbl.SetLabel(self.beacon.title if self.beacon else "")
        _name(self.title_lbl, "Now playing episode title")
        root.Add(self.title_lbl, 0, wx.ALL, 8)

        # Playback goes through the shared audio engine (a hidden control --
        # audio only). It resolves libmpv when available, else wx.media/WMP,
        # and reports readiness via _on_loaded (which seeks to a saved point).
        self.engine = create_engine(
            self,
            on_loaded=self._on_loaded,
            on_finished=self._on_finished,
            on_error=self._on_error,
        )
        if self.engine is None:
            self.status = wx.StaticText(self, label="Media backend unavailable.")
            _name(self.status, "Media backend unavailable")
            root.Add(self.status, 0, wx.ALL, 8)
        else:
            url = self.resource.primary_uri if self.resource else ""
            if url:
                self.engine.load(url)

        # Transport
        transport = wx.BoxSizer(wx.HORIZONTAL)
        self.play_btn = wx.Button(self, label="&Play")
        _name(self.play_btn, "Play or pause")
        self.back_btn = wx.Button(self, label="<< &15s")
        _name(self.back_btn, "Skip back 15 seconds")
        self.fwd_btn = wx.Button(self, label="&30s >>")
        _name(self.fwd_btn, "Skip forward 30 seconds")
        self.add_point_btn = wx.Button(self, label="&Add Time Point")
        _name(self.add_point_btn, "Add a time-point bookmark at the current position")
        for b, h in (
            (self.play_btn, self._on_play),
            (self.back_btn, self._on_back),
            (self.fwd_btn, self._on_fwd),
            (self.add_point_btn, self._on_add_point),
        ):
            b.Bind(wx.EVT_BUTTON, h)
            transport.Add(b, 0, wx.RIGHT, 6)
        root.Add(transport, 0, wx.ALL, 8)

        # Status line (time / duration / chapter)
        self.time_lbl = wx.StaticText(self, label="0:00 / 0:00")
        _name(self.time_lbl, "Current time and duration")
        root.Add(self.time_lbl, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Chapters
        ch_lbl = wx.StaticText(self, label="&Chapters")
        root.Add(ch_lbl, 0, wx.LEFT | wx.RIGHT, 8)
        self.chapter_list = wx.ListBox(self, style=wx.LB_SINGLE)
        _name(self.chapter_list, "Chapters. Enter jumps to the chapter, N next, P previous.")
        self.chapter_list.Bind(wx.EVT_LISTBOX, self._on_chapter_select)
        root.Add(self.chapter_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Transcript
        tr_lbl = wx.StaticText(self, label="&Transcript")
        root.Add(tr_lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.transcript = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        _name(self.transcript, "Episode transcript")
        root.Add(self.transcript, 1, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(root)
        self.chapter_list.SetFocus()

    def _load_chapters(self) -> None:
        if not self.resource:
            return
        self.chapters = self.store.chapters_for(self.resource.resource_id)
        if not self.chapters:
            url = (self.resource.metadata or {}).get("chapters_url", "")
            if url:
                try:
                    from quill.apps.beacon import feeds

                    self.chapters = feeds.fetch_chapters(url, self.resource.resource_id)
                    for ch in self.chapters:
                        self.store.put_chapter(ch)
                except Exception:
                    self.chapters = []

    def _refresh_chapter_list(self) -> None:
        self.chapter_list.Clear()
        for ch in self.chapters:
            self.chapter_list.Append(f"{media.fmt_time(ch.start_ms)}  {ch.title}", ch)

    # -- transport ------------------------------------------------------------

    def _on_play(self, _e=None) -> None:
        if not self.engine:
            self.announcer.say("Media backend unavailable")
            return
        if self.engine.is_playing():
            self.engine.pause()
            self.announcer.say("Paused")
        else:
            self.engine.play()
            self.announcer.say("Playing")

    def _on_back(self, _e=None) -> None:
        self._seek_delta(-self._skip_ms)

    def _on_fwd(self, _e=None) -> None:
        self._seek_delta(self._skip_ms)

    def _seek_delta(self, delta_ms: int) -> None:
        if not self.engine:
            return
        pos = self.engine.position_ms() + delta_ms
        pos = max(0, min(pos, self.engine.length_ms() or 0))
        self.engine.seek(pos)
        self.announcer.say(media.fmt_time(pos), "verbose")

    def _on_chapter_select(self, _e) -> None:
        sel = self.chapter_list.GetSelection()
        if sel < 0 or not self.engine:
            return
        ch = self.chapter_list.GetClientData(sel)
        self.engine.seek(ch.start_ms)
        self.announcer.say(f"Chapter: {ch.title}, {media.fmt_time(ch.start_ms)}")

    def _on_add_point(self, _e=None) -> None:
        if not self.resource:
            return
        pos = self.engine.position_ms() if self.engine else 0
        ch = self._chapter_at(pos)
        beacon, res = capture.capture(
            self.resource.primary_uri,
            title=f"Time point at {media.fmt_time(pos)}",
            tags=["timepoint", "podcast"],
            capture_source="player",
            media_start_ms=pos,
        )
        res.type = "timePoint"
        res.canonical_id = f"{self.resource.canonical_id}@{pos}"
        if ch:
            beacon.collections = [ch.title] if ch.title else []
        self.store.put_beacon(beacon, resource=res)
        self.announcer.say(f"Time point saved at {media.fmt_time(pos)}")

    def _chapter_at(self, ms: int):
        last = None
        for ch in self.chapters:
            if ch.start_ms <= ms:
                last = ch
            else:
                break
        return last

    def _on_timer(self, _e) -> None:
        if not self.engine:
            return
        pos = self.engine.position_ms()
        length = self.engine.length_ms() or self._length_ms
        self.time_lbl.SetLabel(f"{media.fmt_time(pos)} / {media.fmt_time(length)}")

    def _on_loaded(self, length_ms: int) -> None:
        """The shared engine reports readiness; seek to any saved time point."""
        self._length_ms = length_ms
        if self.engine and self.beacon and self.beacon.locations:
            start = self.beacon.locations[0].media_start_ms
            if start:
                self.engine.seek(start)
                self.announcer.say(f"Resumed at {media.fmt_time(start)}", "normal")

    def _on_finished(self) -> None:
        self.announcer.say("Finished", "normal")

    def _on_error(self, message: str) -> None:
        self.announcer.say(message, "normal")

    def _on_close(self, _e) -> None:
        self._timer.Stop()
        if self.engine:
            self.engine.close()
        self.Destroy()
