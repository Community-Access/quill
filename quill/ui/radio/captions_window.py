"""The Captions window: captions you can actually read.

Quill Radio could turn captions on, and where they went was *into the picture*
-- mpv drawing text as pixels over the video. For the person this application
is built for that is the same as turning them off: pixels cannot be read by a
screen reader, cannot reach a braille display, cannot be copied and cannot be
searched, and the Video Window may not even be open. "Toggling captions on and
off is not showing the captions in a window" (2026-08-23) is the whole brief.

So captions land in an ordinary text control, in a window of their own:

* **A running transcript that follows playback.** Each line joins the ones
  already said, so a line you missed is one Up arrow away. The model is pure
  and lives in :mod:`quill.core.radio.live_captions`.
* **Following is a checkbox, not a fact of life.** While Follow Playback is on,
  the caret rides the current line; turn it off and the window holds still so
  you can read back without fighting the player. Turning it back on catches up.
* **It never announces itself.** The same rule the Video Window's status line
  follows and for the same reason: a control that speaks on every change makes a
  media player unusable, and captions change every few seconds. What it *is*
  is readable on demand, at any moment, with the keyboard already on it.
* **It does not need mpv, and it does not need the picture.** The cues come
  from the caption track the resolve already fetched, so captions work on the
  classic engine and while listening to audio only -- which is how most people
  here will use them.
* **The style is the one Caption Settings already edits.** Size especially:
  WCAG 1.4.4 asks for 200% and the existing dialog offers up to 300%, so the
  same percentage that scales mpv's captions scales this window's font.

Escape, Ctrl+W and Ctrl+F4 close it. Closing it turns captions off, because a
caption window you closed and a caption setting still on is the app disagreeing
with itself.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.radio import live_captions

#: How often the window asks the player where it is. Captions change on the
#: order of seconds; polling four times a second is imperceptibly late and
#: costs one integer read.
TICK_MS = 250

#: The font size the window draws at, per Caption Settings' size percentage.
BASE_POINT_SIZE = 14

WAITING = "Captions will appear here as they are spoken."


class CaptionsWindow:
    """A frame that shows the captions as they are spoken, and keeps them."""

    def __init__(
        self,
        parent: Any,
        *,
        title: str = "",
        cues: Sequence[Any] = (),
        position_ms: Callable[[], int] | None = None,
        size_percent: int = 100,
        is_automatic: bool = False,
        announce: Callable[[str], None] | None = None,
        on_closed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._cues = list(cues)
        self._position_ms = position_ms
        self._announce = announce or (lambda _m: None)
        self._on_closed = on_closed or (lambda: None)
        self._current = -1

        # A literal title, like the Video Window's: the window is "the
        # captions", and which video they belong to is on the control that is
        # actually read (below), where somebody navigating to it is told.
        self._frame = wx.Frame(parent, title="Quill Radio Captions", style=wx.DEFAULT_FRAME_STYLE)
        self._frame.SetMinSize((460, 240))
        root = wx.BoxSizer(wx.VERTICAL)

        heading = "&Captions"
        if is_automatic:
            # Said in the label, not left to be discovered. An automatic
            # caption presented as authoritative is a confident wrong answer.
            heading = "&Captions (automatic -- machine-generated, so expect mistakes)"
        root.Add(wx.StaticText(self._frame, label=heading), 0, wx.LEFT | wx.TOP, 8)

        self._text = wx.TextCtrl(
            self._frame,
            value=WAITING,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        named = f"Captions for {title}" if title else "Captions"
        self._text.SetName(
            f"{named}, newest last. Arrow up to re-read; turn off Follow Playback to hold still"
        )
        self._text.SetHelpText(
            "The captions for what is playing, as they are spoken. It never "
            "announces itself -- read it whenever you like. The line marked "
            "with a greater-than sign is the one being spoken now. Escape closes."
        )
        self._apply_size(size_percent)
        root.Add(self._text, 1, wx.EXPAND | wx.ALL, 8)

        self._follow = wx.CheckBox(self._frame, label="&Follow playback")
        self._follow.SetValue(True)
        self._follow.SetHelpText(
            "On, the view moves to the caption being spoken. Off, it holds "
            "still so you can read back without the player moving you."
        )
        root.Add(self._follow, 0, wx.LEFT | wx.BOTTOM, 8)

        self._frame.SetSizer(root)
        self._frame.Bind(wx.EVT_CLOSE, self._on_close)
        self._frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        self._timer = wx.Timer(self._frame)
        self._frame.Bind(wx.EVT_TIMER, lambda _e: self.tick(), self._timer)

    # -- the window ------------------------------------------------------------

    @property
    def frame(self) -> Any:
        return self._frame

    @property
    def text(self) -> Any:
        return self._text

    def _apply_size(self, size_percent: int) -> None:
        """Scale the font by Caption Settings' own percentage."""
        wx = self._wx
        percent = max(100, min(300, int(size_percent or 100)))
        font = self._text.GetFont()
        try:
            font.SetPointSize(max(8, round(BASE_POINT_SIZE * percent / 100)))
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            self._text.SetFont(font)
        except Exception:  # noqa: BLE001 - a font is never worth a failed window
            return

    def show(self) -> None:
        """Show the window and start following, without taking focus.

        Deliberately not focused: captions are something you read *while* doing
        something else, and a window that steals the keyboard the moment it
        opens takes you out of the list you were browsing.
        """
        self._frame.Show()
        self.tick()
        self._timer.Start(TICK_MS)

    def close(self) -> None:
        self._frame.Close()

    def set_cues(self, cues: Sequence[Any]) -> None:
        """Replace the caption track (a different video started playing)."""
        self._cues = list(cues)
        self._current = -1
        self._text.SetValue(WAITING)
        self.tick()

    # -- following -------------------------------------------------------------

    def tick(self) -> bool:
        """One poll. True when the displayed caption changed.

        Returns rather than announces: the caller (and the tests) can tell
        whether anything moved, and nothing is spoken either way.
        """
        if self._position_ms is None or not self._cues:
            return False
        try:
            position = int(self._position_ms())
        except Exception:  # noqa: BLE001 - a stopped player must not raise here
            return False
        index = live_captions.cue_index_at(self._cues, position)
        if index == self._current:
            return False
        self._current = index
        text = live_captions.visible_text(self._cues, index)
        self._text.SetValue(text or WAITING)
        if self._follow.GetValue():
            # The caret ends on the newest line, which is what a braille
            # display follows and where a sighted reader is looking.
            self._text.SetInsertionPointEnd()
            self._text.ShowPosition(self._text.GetLastPosition())
        return True

    def current_caption(self) -> str:
        """The line being spoken, for a caller that wants to say it out loud."""
        return live_captions.current_text(self._cues, self._current)

    # -- events ----------------------------------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        control = event.ControlDown()
        if key == wx.WXK_ESCAPE or (control and key in (ord("W"), wx.WXK_F4)):
            self.close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        self._timer.Stop()
        self._on_closed()
        event.Skip()
