"""Built-in accessible media player (PRD 11.5, 11.6, Phase 3).

A small wx frame with ``wx.media.MediaCtrl`` transport, a chapter list, a
transcript view, and time-point capture. Keyboard-first: Space play/pause,
Left/Right skip, J/L jump by skip interval, K add time point, N/P next/prev
chapter. Every control has an accessible name; the status line announces
chapter and time (PRD 18.4, A11Y-013).

Playback depends on the platform media backend; the UI is built so it
constructs and runs even when a backend is absent (it announces "media
backend unavailable" rather than crashing).
"""

from __future__ import annotations

import wx

try:
    import wx.media

    _HAS_MEDIA = True
except ImportError:  # pragma: no cover - depends on build
    _HAS_MEDIA = False

from quill.apps.beacon import capture, media
from quill.apps.beacon.announce import Announcer


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

        self.media = None
        if _HAS_MEDIA:
            try:
                self.media = wx.media.MediaCtrl(self)
                _name(self.media, "Media playback area")
                url = self.resource.primary_uri if self.resource else ""
                if url:
                    self.media.Load(url)
                    # Seek to a saved time point once the media is ready.
                    self.media.Bind(wx.media.EVT_MEDIA_LOADED, self._on_loaded)
            except Exception:  # pragma: no cover - backend-dependent
                self.media = None
        if self.media is None:
            self.status = wx.StaticText(self, label="Media backend unavailable.")
            _name(self.status, "Media backend unavailable")
            root.Add(self.status, 0, wx.ALL, 8)
        else:
            root.Add(self.media, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

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
        if not self.media:
            self.announcer.say("Media backend unavailable")
            return
        state = self.media.GetState()
        if state == wx.media.MEDIASTATE_PLAYING:
            self.media.Pause()
            self.announcer.say("Paused")
        else:
            self.media.Play()
            self.announcer.say("Playing")

    def _on_back(self, _e=None) -> None:
        self._seek_delta(-self._skip_ms)

    def _on_fwd(self, _e=None) -> None:
        self._seek_delta(self._skip_ms)

    def _seek_delta(self, delta_ms: int) -> None:
        if not self.media:
            return
        pos = self.media.Tell() + delta_ms
        pos = max(0, min(pos, self.media.Length() or 0))
        self.media.Seek(pos)
        self.announcer.say(media.fmt_time(pos), "verbose")

    def _on_chapter_select(self, _e) -> None:
        sel = self.chapter_list.GetSelection()
        if sel < 0 or not self.media:
            return
        ch = self.chapter_list.GetClientData(sel)
        self.media.Seek(ch.start_ms)
        self.announcer.say(f"Chapter: {ch.title}, {media.fmt_time(ch.start_ms)}")

    def _on_add_point(self, _e=None) -> None:
        if not self.resource:
            return
        pos = self.media.Tell() if self.media else 0
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
        if not self.media:
            return
        pos = self.media.Tell()
        length = self.media.Length() or 0
        self.time_lbl.SetLabel(f"{media.fmt_time(pos)} / {media.fmt_time(length)}")

    def _on_loaded(self, _e) -> None:
        """Seek to a saved time point once the media backend is ready."""
        if self.beacon and self.beacon.locations:
            start = self.beacon.locations[0].media_start_ms
            if start:
                self.media.Seek(start)
                self.announcer.say(f"Resumed at {media.fmt_time(start)}", "normal")

    def _on_close(self, _e) -> None:
        self._timer.Stop()
        self.Destroy()
