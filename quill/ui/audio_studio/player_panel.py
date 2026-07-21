"""The Audio Studio's chapter-aware player panel.

Ported from ChapterForge's PlayerPanel (``s:\\code99\\forum``, MIT) onto
QUILL's engine protocol and accessibility idioms. Play/Pause, Stop,
Previous/Next chapter, Rewind/Forward (configurable step), a position slider
that speaks human time, and a volume slider. The current chapter is announced
as playback crosses into it ("Chapter 4: The Long Road").

Pure UI over :mod:`quill.ui.audio.audio_engine`; chapter math stays in
:mod:`quill.core.speech.chapters`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import wx

from quill.core.audio_studio.book_prefs import BookPrefs
from quill.core.i18n import _
from quill.core.speech.chapter_io import format_timestamp
from quill.core.speech.chapters import Chapter
from quill.ui.audio.audio_engine import AudioEngine, create_engine
from quill.ui.audio_studio.pages_base import set_accessible_name

_log = logging.getLogger(__name__)

_TICK_MS = 500  # position slider refresh cadence


class PlayerPanel(wx.Panel):
    """Chapter-aware transport controls over one loaded audio file."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        announce: Callable[[str], None] | None = None,
        skip_step_ms: int = 10_000,
        on_volume: Callable[[int], None] | None = None,
        on_mute: Callable[[bool], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.SetName(_("Player"))
        self._announce_fn = announce
        self._on_volume_cb = on_volume
        self._on_mute_cb = on_mute
        self._on_finished_cb = on_finished
        self._skip_step_ms = max(1_000, int(skip_step_ms))
        self._chapters: list[Chapter] = []
        self._length_ms = 0
        self._loaded = False
        self._announced_chapter = -1
        self._muted = False
        self._pre_mute_volume = 100
        self._engine: AudioEngine | None = create_engine(
            self,
            on_loaded=self._on_engine_loaded,
            on_finished=self._on_engine_finished,
            on_error=self._on_engine_error,
        )

        sizer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = self._button(row, _("&Play"), self._on_play_pause, "player.play")
        self._stop_btn = self._button(row, _("S&top"), self._on_stop, "player.stop")
        self._prev_btn = self._button(row, _("Pre&vious chapter"), self._on_prev, "player.prev")
        self._next_btn = self._button(row, _("Ne&xt chapter"), self._on_next, "player.next")
        self._rew_btn = self._button(row, _("Re&wind"), self._on_rewind, "player.rewind")
        self._fwd_btn = self._button(row, _("&Forward"), self._on_forward, "player.forward")
        self._where_btn = self._button(
            row, _("Where am &I?"), self._on_where_am_i, "player.where_am_i"
        )
        row.Add(wx.StaticText(self, label=_("Spee&d:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self._rate = wx.Choice(self, choices=["0.75x", "1x", "1.25x", "1.5x", "2x"])
        self._rate.SetName(_("Playback speed"))
        self._rate.SetSelection(1)
        self._rate.Bind(wx.EVT_CHOICE, lambda _e: self._on_rate())
        row.Add(self._rate, 0, wx.LEFT, 6)
        sizer.Add(row, 0, wx.LEFT | wx.TOP, 8)

        slider_row = wx.BoxSizer(wx.HORIZONTAL)
        self._position = wx.Slider(self, minValue=0, maxValue=1000)
        set_accessible_name(self._position, _("Position"))
        self._position.Bind(wx.EVT_SLIDER, self._on_slider)
        slider_row.Add(self._position, 3, wx.EXPAND | wx.RIGHT, 8)
        self._volume = wx.Slider(self, value=100, minValue=0, maxValue=100)
        set_accessible_name(self._volume, _("Volume"))
        self._volume.Bind(wx.EVT_SLIDER, self._on_volume)
        slider_row.Add(self._volume, 1, wx.EXPAND)
        self._mute_btn = wx.Button(self, label=_("M&ute"), name="player.mute")
        self._mute_btn.Bind(wx.EVT_BUTTON, lambda _e: self.toggle_mute())
        slider_row.Add(self._mute_btn, 0, wx.LEFT, 6)
        sizer.Add(slider_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self._status = wx.StaticText(self, label=_("No file loaded."), name="player.status")
        sizer.Add(self._status, 0, wx.ALL, 8)
        self.SetSizer(sizer)

        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda _e: self._on_tick(), self._timer)
        self._sync_enabled()

    # -- public API -------------------------------------------------------------

    def load(
        self,
        path: str,
        chapters: list[Chapter],
        *,
        resume_ms: int = 0,
        book_prefs: BookPrefs | None = None,
    ) -> bool:
        """Begin loading *path*; chapter navigation uses *chapters*.

        A positive *resume_ms* parks the playhead there once loading finishes
        (paused) — the remembered listening position. When *book_prefs* is
        supplied, the remembered per-book volume (and mute state) is applied
        before the first play; an unset volume (``-1``) falls back to 100%.
        """
        self._chapters = list(chapters)
        self._loaded = False
        self._announced_chapter = -1
        self._resume_ms = max(0, int(resume_ms))
        if self._engine is None:
            return False
        self._apply_book_prefs(book_prefs)
        self._status.SetLabel(_("Loading {name}...").format(name=path))
        return self._engine.load(path)

    def set_chapters(self, chapters: list[Chapter]) -> None:
        """Adopt an edited chapter list without reloading the audio."""
        self._chapters = list(chapters)
        self._announced_chapter = -1

    def playhead_ms(self) -> int:
        """The current position — the anchor for split-at-playhead and retiming."""
        return self._engine.position_ms() if self._engine is not None else 0

    def current_chapter_index(self) -> int:
        """The chapter the playhead is in (-1 when no chapters loaded)."""
        return self._chapter_at(self.playhead_ms())

    def play_chapter(self, index: int) -> None:
        """Jump to chapter *index* and play it."""
        if self._engine is None or not (0 <= index < len(self._chapters)):
            return
        chapter = self._chapters[index]
        self._engine.seek(chapter.start_ms, resume=True)
        self._announce_chapter(index)
        self._sync_play_label()
        self._timer.Start(_TICK_MS)

    def shutdown(self) -> None:
        """Stop the timer and release the file (call before the dialog closes)."""
        self._timer.Stop()
        if self._engine is not None:
            self._engine.close()

    def has_media(self) -> bool:
        return self._loaded

    def toggle_mute(self) -> None:
        """Flip mute; unmuting restores the pre-mute engine volume."""
        if self._engine is None:
            return
        if self._muted:
            self._muted = False
            self._engine.set_volume(self._pre_mute_volume)
            self._mute_btn.SetLabel(_("M&ute"))
        else:
            self._pre_mute_volume = self._volume.GetValue()
            self._muted = True
            self._engine.set_volume(0)
            self._mute_btn.SetLabel(_("Un&mute"))
        self._announce(_("Muted") if self._muted else _("Unmuted"))
        if self._on_mute_cb is not None:
            self._on_mute_cb(self._muted)

    # -- helpers ----------------------------------------------------------------

    def _button(
        self, row: wx.BoxSizer, label: str, handler: Callable[[], None], name: str
    ) -> wx.Button:
        btn = wx.Button(self, label=label, name=name)
        btn.Bind(wx.EVT_BUTTON, lambda _e: handler())
        row.Add(btn, 0, wx.RIGHT, 6)
        return btn

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def _chapter_at(self, ms: int) -> int:
        for i, c in enumerate(self._chapters):
            if c.start_ms <= ms < c.end_ms:
                return i
        return len(self._chapters) - 1 if self._chapters else -1

    def _announce_chapter(self, index: int) -> None:
        if 0 <= index < len(self._chapters) and index != self._announced_chapter:
            self._announced_chapter = index
            c = self._chapters[index]
            self._announce(
                _("Chapter {num}: {title}, {duration}").format(
                    num=index + 1, title=c.title, duration=format_timestamp(c.duration_ms)
                )
            )

    def _sync_enabled(self) -> None:
        on = self._loaded and self._engine is not None
        for btn in (
            self._play_btn,
            self._stop_btn,
            self._prev_btn,
            self._next_btn,
            self._rew_btn,
            self._fwd_btn,
            self._where_btn,
        ):
            btn.Enable(on)
        self._position.Enable(on)
        self._rate.Enable(on)

    def _sync_play_label(self) -> None:
        playing = self._engine is not None and self._engine.is_playing()
        self._play_btn.SetLabel(_("&Pause") if playing else _("&Play"))

    def _update_status(self) -> None:
        pos = self.playhead_ms()
        idx = self._chapter_at(pos)
        chapter = (
            _("Chapter {num}: {title}").format(num=idx + 1, title=self._chapters[idx].title)
            if idx >= 0
            else _("No chapters")
        )
        self._status.SetLabel(
            _("{chapter} — {pos} of {total}").format(
                chapter=chapter,
                pos=format_timestamp(pos),
                total=format_timestamp(self._length_ms),
            )
        )

    # -- engine callbacks ---------------------------------------------------------

    def _on_engine_loaded(self, length_ms: int) -> None:
        self._loaded = True
        self._length_ms = length_ms
        if self._chapters and length_ms > 0:
            from quill.core.speech.chapters import clamp_chapters

            self._chapters = clamp_chapters(self._chapters, length_ms)
        self._position.SetRange(0, max(1, length_ms))
        self._sync_enabled()
        resume = getattr(self, "_resume_ms", 0)
        if 0 < resume < length_ms and self._engine is not None:
            self._engine.seek(resume, resume=False)
            self._position.SetValue(resume)
            self._announce(
                _("Resuming where you left off, at {pos}").format(pos=format_timestamp(resume))
            )
        else:
            self._announce(
                _("Loaded: {count} chapters, {total}").format(
                    count=len(self._chapters), total=format_timestamp(length_ms)
                )
            )
        self._update_status()
        self._timer.Start(_TICK_MS)

    def _on_engine_finished(self) -> None:
        self._sync_play_label()
        self._announce(_("End of book"))
        if self._on_finished_cb is not None:
            self._on_finished_cb()

    def _on_engine_error(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    # -- transport ---------------------------------------------------------------

    def play_pause(self) -> None:
        """Toggle play/pause (the media-key and host-facing transport entry)."""
        if self._engine is None:
            return
        if self._engine.is_playing():
            self._engine.pause()
        else:
            self._engine.play()
            self._timer.Start(_TICK_MS)
        self._sync_play_label()

    def stop_playback(self) -> None:
        """Stop and reset the announced-chapter tracker (host-facing)."""
        if self._engine is not None:
            self._engine.stop()
            self._announced_chapter = -1
            self._sync_play_label()
            self._update_status()

    def next_chapter(self) -> None:
        """Jump to the next chapter, or announce at the last."""
        idx = self._chapter_at(self.playhead_ms())
        if idx + 1 < len(self._chapters):
            self.play_chapter(idx + 1)
        else:
            self._announce(_("This is the last chapter"))

    def previous_chapter(self) -> None:
        """Jump to the previous chapter (first-seconds rule applies)."""
        idx = self._chapter_at(self.playhead_ms())
        # Within the first seconds of a chapter, previous means the one before.
        if idx > 0 and self.playhead_ms() - self._chapters[idx].start_ms < 3_000:
            idx -= 1
        self.play_chapter(max(0, idx))

    def apply_book_prefs(self, book_prefs: BookPrefs | None) -> None:
        """Apply remembered per-book volume + mute (host-facing wrapper)."""
        self._apply_book_prefs(book_prefs)

    def _on_play_pause(self) -> None:
        self.play_pause()

    def _on_stop(self) -> None:
        self.stop_playback()

    def _on_prev(self) -> None:
        self.previous_chapter()

    def _on_next(self) -> None:
        self.next_chapter()

    def _on_where_am_i(self) -> None:
        """Speak book, chapter, position, and remaining time — the audible glance."""
        if not self._loaded:
            self._announce(_("No file loaded."))
            return
        pos = self.playhead_ms()
        idx = self._chapter_at(pos)
        parts: list[str] = []
        if idx >= 0:
            c = self._chapters[idx]
            parts.append(
                _("Chapter {num} of {total}: {title}").format(
                    num=idx + 1, total=len(self._chapters), title=c.title
                )
            )
            parts.append(
                _("{elapsed} into the chapter, {left} left in it").format(
                    elapsed=format_timestamp(pos - c.start_ms),
                    left=format_timestamp(max(0, c.end_ms - pos)),
                )
            )
        parts.append(
            _("{pos} of {total} in the book, {left} remaining").format(
                pos=format_timestamp(pos),
                total=format_timestamp(self._length_ms),
                left=format_timestamp(max(0, self._length_ms - pos)),
            )
        )
        self._announce(". ".join(parts))

    def _on_rate(self) -> None:
        rates = (0.75, 1.0, 1.25, 1.5, 2.0)
        idx = self._rate.GetSelection()
        if self._engine is not None and 0 <= idx < len(rates):
            self._engine.set_rate(rates[idx])
            self._announce(_("Speed {rate}").format(rate=self._rate.GetString(idx)))

    def _on_rewind(self) -> None:
        self._skip(-self._skip_step_ms)

    def _on_forward(self) -> None:
        self._skip(self._skip_step_ms)

    def _skip(self, delta_ms: int) -> None:
        if self._engine is None or not self._loaded:
            return
        target = max(0, min(self._length_ms, self.playhead_ms() + delta_ms))
        self._engine.seek(target)
        self._announce(format_timestamp(target))
        self._update_status()

    def _on_slider(self, _evt: wx.Event) -> None:
        if self._engine is not None and self._loaded:
            self._engine.seek(self._position.GetValue())
            self._update_status()

    def _on_volume(self, _evt: wx.Event) -> None:
        if self._engine is not None:
            value = self._volume.GetValue()
            self._engine.set_volume(value)
            # A manual volume change exits the muted state (slider is the
            # source of truth for the level we restored to).
            if self._muted and value > 0:
                self._muted = False
                self._pre_mute_volume = value
                self._mute_btn.SetLabel(_("M&ute"))
            if self._on_volume_cb is not None:
                self._on_volume_cb(value)

    def _apply_book_prefs(self, book_prefs: BookPrefs | None) -> None:
        """Apply remembered per-book volume + mute to the slider and engine."""
        vp = book_prefs.volume_percent if book_prefs and book_prefs.volume_percent >= 0 else 100
        muted = bool(book_prefs and book_prefs.muted)
        self._volume.SetValue(vp)
        self._pre_mute_volume = vp
        self._muted = muted
        self._mute_btn.SetLabel(_("Un&mute") if muted else _("M&ute"))
        if self._engine is not None:
            self._engine.set_volume(0 if muted else vp)

    def _on_tick(self) -> None:
        if not self._loaded:
            return
        pos = self.playhead_ms()
        # Don't fight the user mid-drag; only follow during playback.
        if self._engine is not None and self._engine.is_playing():
            self._position.SetValue(min(pos, self._position.GetMax()))
            self._announce_chapter(self._chapter_at(pos))
        self._update_status()
        self._sync_play_label()
