"""The small player window behind Play and Play Media Here (wordpress.md 6.1a).

It is the shared transport panel QUILL and Quill Media Player already use
(:class:`~quill.ui.audio_studio.player_panel.PlayerPanel`), so the keys are the
familiar ones, with four buttons of this window's own: Captions, Go to
Position, Open in Quill Media Player and Open in Browser. The file streams from
its address on the site; nothing is saved.

**The picture.** The family's engines are audio engines: libmpv starts with
``vid=no`` and the Windows Media control is hidden. For a video this window
turns the picture back on in a frame inside the panel -- libmpv draws into it
(``wid``), and the classic Windows Media control is moved into it and shown --
through :func:`show_picture`, so there is still one engine and one panel. The
modern Windows Media engine has no surface to draw on; there the window says,
once, that the sound plays here and the browser shows the picture.

**Closing** stops playback and releases the stream (:meth:`release`), on the
Close button, on Escape and on the window's own close box alike, so nothing is
left playing behind a closed window.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import wx

from quill.core.speech.chapter_io import format_timestamp
from quill.core.wordpress import media_play as mp
from quill.core.wordpress.listening import Cue
from quill.ui.audio_studio.player_panel import PlayerPanel
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip_size

_log = logging.getLogger(__name__)

ShowModal = Callable[[wx.Dialog, str], int]
ReadCaptions = Callable[[mp.CaptionTrack, Callable[[list[Cue]], None]], None]

#: The panel's chapter buttons: a single Media Library file has no chapters.
_CHAPTER_BUTTONS = ("player.prev", "player.next")


def show_picture(engine: object, picture: wx.Window) -> bool:
    """Let *engine* draw a video's picture in *picture*; False when it cannot."""
    mpv = getattr(engine, "_mpv", None)
    if mpv is not None and hasattr(mpv, "set_str"):
        try:
            handle = str(int(picture.GetHandle()))
            return mpv.set_str("wid", handle) >= 0 and mpv.set_str("vid", "auto") >= 0
        except Exception:  # noqa: BLE001 - no picture is not a reason to stop the sound
            _log.exception("libmpv would not draw the picture")
            return False
    media = getattr(engine, "_media", None)
    if media is not None and hasattr(media, "Reparent"):
        try:
            media.Reparent(picture)
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(media, 1, wx.EXPAND)
            picture.SetSizer(sizer)
            media.Show()
            picture.Layout()
            return True
        except Exception:  # noqa: BLE001 - as above
            _log.exception("Windows Media would not show the picture")
            return False
    return False


class MediaPlayerWindow(wx.Dialog):
    """One audio or video file from a WordPress site, playing."""

    def __init__(
        self,
        parent: wx.Window | None,
        *,
        playable: mp.Playable,
        site_name: str,
        show_modal: ShowModal,
        announce: Callable[[str], None],
        read_captions: ReadCaptions,
        open_in_player: Callable[[mp.Playable], None],
        open_in_browser: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            title=f"Play: {playable.title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.playable = playable
        self._site_name = site_name
        self._show_modal = show_modal
        self._announce = announce
        self._read_captions = read_captions
        self._open_in_player = open_in_player
        self._open_in_browser = open_in_browser
        self._cues: list[Cue] | None = None
        self._released = False
        self.SetHelpText(
            f"Plays {playable.title} from {site_name}, streamed from the site over HTTPS; "
            "nothing is saved on this computer. The buttons are the same as in QUILL's "
            "player and Quill Media Player. Closing the window stops playback."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.panel = PlayerPanel(self, announce=announce)
        self.panel.SetHelpText(
            "Play or pause, stop, rewind and forward ten seconds, where am I, speed, "
            "position and volume, for the file from the site."
        )
        for name in _CHAPTER_BUTTONS:
            button = self.panel.FindWindowByName(name)
            if button is not None:
                button.Hide()
        self.picture: wx.Panel | None = None
        if playable.kind == "video":
            # Inside the panel, so the engine's own events still reach it.
            self.picture = wx.Panel(self.panel, name="Picture")
            self.picture.SetHelpText(
                "The video's picture. It is not a control: Tab moves past it, and the "
                "buttons control playback."
            )
            self.picture.SetMinSize(dip_size(self, 480, 270))
            self.picture.SetBackgroundColour(wx.BLACK)
            self.picture.SetCanFocus(False)
            self.panel.GetSizer().Insert(0, self.picture, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, 4)

        bar = wx.BoxSizer(wx.HORIZONTAL)
        self.captions_button: wx.Button | None = None
        if playable.kind == "video":
            self.captions_button = self._button(
                bar,
                "&Captions",
                "Speaks the caption on screen at the current position, from the video's "
                "captions track on the site. Playback keeps going.",
                self.on_captions,
            )
        self._button(
            bar,
            "&Go to Position...",
            "Jump to a time in the file, typed as hours, minutes and seconds.",
            self.on_go_to_position,
        )
        self._button(
            bar,
            "Open in &Quill Media Player",
            "Play the file in Quill Media Player instead, for bookmarks and resume. "
            "Playback here pauses.",
            self.on_open_in_player,
        )
        self._button(
            bar,
            "Open in &Browser",
            "Open the file's address in your web browser.",
            self.on_open_in_browser,
        )
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Stop playback and close this window. Escape does the same.")
        bind_close_button(self, close, modeless=False)
        bar.Add(close, 0, wx.ALL, 4)
        sizer.Add(bar, 0, wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(dip_size(self, 520, -1))
        apply_modal_ids(self)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    def _button(
        self, bar: wx.BoxSizer, label: str, help_text: str, run: Callable[[], None]
    ) -> wx.Button:
        button = wx.Button(self, label=label)
        button.SetHelpText(help_text)
        button.Bind(wx.EVT_BUTTON, lambda _e: run())
        bar.Add(button, 0, wx.ALL, 4)
        return button

    # ------------------------------------------------------------------ #
    # starting and stopping

    def start(self) -> bool:
        """Turn on the picture for a video, then begin streaming and playing."""
        if self.picture is not None and not show_picture(self.panel.output_engine(), self.picture):
            self.picture.Hide()
            self._announce(
                "On this computer the video's sound plays here; Open in Browser shows the picture."
            )
        return bool(self.panel.load(self.playable.url, [], autoplay=True))

    def release(self) -> None:
        """Stop playback and let go of the stream. Safe to call more than once."""
        if self._released:
            return
        self._released = True
        try:
            self.panel.stop()
            self.panel.shutdown()
        except Exception:  # noqa: BLE001 - closing must always finish
            _log.exception("The player did not stop cleanly")

    def _on_close(self, event: wx.CloseEvent) -> None:
        self.release()
        event.Skip()

    def _on_destroy(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self:
            self.release()
        event.Skip()

    # ------------------------------------------------------------------ #
    # the window's own buttons

    def on_captions(self) -> None:
        tracks = self.playable.captions
        if not tracks:
            self._announce(f"This video has no captions track on {self._site_name}.")
            return
        if self._cues is not None:
            self._say_caption()
            return

        def done(cues: list[Cue]) -> None:
            self._cues = list(cues)
            self._say_caption()

        self._read_captions(tracks[0], done)

    def _say_caption(self) -> None:
        position = self.panel.playhead_ms()
        words = mp.caption_at(self._cues or [], position)
        if words:
            self._announce(words)
        else:
            self._announce(f"No caption at {format_timestamp(position)}.")

    def on_go_to_position(self) -> None:
        from quill.ui.media.go_to_position_dialog import GoToPositionDialog

        dialog = GoToPositionDialog(
            self,
            duration_ms=self.panel.length_ms(),
            current_ms=self.panel.playhead_ms(),
            announce=self._announce,
        )
        try:
            if self._show_modal(dialog, "Go to Position") == wx.ID_OK:
                self.panel.seek_to(dialog.get_target_ms())
                clamped = dialog.clamped_message()
                if clamped:
                    self._announce(clamped)
        finally:
            dialog.Destroy()

    def on_open_in_player(self) -> None:
        if self.panel.is_playing():
            self.panel.pause()
        self._open_in_player(self.playable)

    def on_open_in_browser(self) -> None:
        if self.panel.is_playing():
            self.panel.pause()
        self._open_in_browser(self.playable.url)


def play(parent: Any, show_modal: ShowModal, playable: mp.Playable, **kwargs: Any) -> None:
    """Open the player window on *playable*, and stop everything when it closes."""
    window = MediaPlayerWindow(parent, playable=playable, show_modal=show_modal, **kwargs)
    try:
        window.start()
        show_modal(window, window.GetTitle())
    finally:
        window.release()
        window.Destroy()
