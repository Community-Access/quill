"""The Lyrics window: the words of a song, as text you can read.

Shared by Quill Radio and Quill Media Player, and modelled on Quill Radio's
Captions window, which solved the same problem first: words a screen reader can
read, a braille display can show, and a person can copy and search -- not
pixels, and not a voice that talks over the song.

* **The whole lyric in one read-only text control.** Arrow line by line,
  Ctrl+C copies, Ctrl+Home goes back to the top. Opening the window puts you in
  it, so the reader already says everything there is to say: the window adds
  nothing of its own when it opens and nothing per line.
* **Radio gets the words; the Player gets the words *and* the time.** A radio
  stream gives no position within the song, so a caret following it would be
  confidently in the wrong place -- worse than no caret, and worst for a
  listener who cannot see it drift. A file has a real playhead, so in the
  Player (``position_ms`` given, timed lyrics found) **Current line** shows the
  line being sung, and **Follow playback** moves the caret in the lyrics to it.
  Turn Follow playback off and the window holds still while you read back;
  turn it on again and it catches up.
* **The current line is never spoken by itself.** It changes every few
  seconds; a window that announced each change would talk over the music it is
  showing the words to. It is shown, for reviewing whenever you like, and
  spoken only when you ask: **Say Current Line**.

Escape, Ctrl+W and Ctrl+F4 close it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.lyrics.lrclib import LrcLine, Lyrics, line_at, parse_lrc

__all__ = ["TITLE_PREFIX", "LyricsWindow"]

#: Every Lyrics window's title starts with this; F1 resolves it by prefix.
TITLE_PREFIX = "Lyrics:"

#: How often the Player's window asks where playback is. Lyric lines last
#: seconds; four polls a second is imperceptibly late and costs one integer read.
TICK_MS = 250

BEFORE_FIRST = "(The words have not started yet.)"
BREAK = "(No words here -- an instrumental break.)"


class LyricsWindow:
    """A frame holding one song's lyrics, optionally following playback."""

    def __init__(
        self,
        parent: Any,
        *,
        song: str,
        lyrics: Lyrics,
        position_ms: Callable[[], int] | None = None,
        announce: Callable[[str], None] | None = None,
        on_closed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._on_closed = on_closed or (lambda: None)
        self._position_ms = position_ms
        self._song = song
        self._lines: tuple[LrcLine, ...] = ()
        self._index = -1

        self._frame = wx.Frame(parent, title=f"Lyrics: {song}", style=wx.DEFAULT_FRAME_STYLE)
        self._frame.SetMinSize((480, 320))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self._frame, label="&Lyrics"), 0, wx.LEFT | wx.TOP, 8)
        self._text = wx.TextCtrl(
            self._frame,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP | wx.HSCROLL,
        )
        self._text.SetName(f"Lyrics for {song}")
        self._text.SetHelpText(
            "The words of the song, one line per line, from LRCLIB (lrclib.net). "
            "Arrow through them, or copy them with Ctrl+C. Nothing here is "
            "spoken by itself. Escape closes the window."
        )
        root.Add(self._text, 1, wx.EXPAND | wx.ALL, 8)

        self._current: Any = None
        self._follow: Any = None
        self._timer: Any = None
        if position_ms is not None:
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(wx.StaticText(self._frame, label="C&urrent line:"), 0, wx.ALIGN_CENTER_VERTICAL)
            self._current = wx.TextCtrl(self._frame, style=wx.TE_READONLY)
            self._current.SetHelpText(
                "The line being sung now, kept up to date as the song plays. It "
                "is never read out by itself: come here to review it, or press "
                "Say Current Line to hear it."
            )
            row.Add(self._current, 1, wx.LEFT | wx.EXPAND, 6)
            root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

            self._follow = wx.CheckBox(self._frame, label="&Follow playback")
            self._follow.SetHelpText(
                "On, the cursor in the lyrics moves to the line being sung. Off, "
                "the lyrics hold still so you can read back without the song "
                "moving you; turning it on again catches up. Unavailable when the "
                "song has words but no timings."
            )
            self._follow.Bind(wx.EVT_CHECKBOX, lambda _e: self._catch_up())
            root.Add(self._follow, 0, wx.LEFT | wx.TOP, 8)

            say = wx.Button(self._frame, label="&Say Current Line")
            say.SetHelpText("Speaks the line being sung now, once.")
            say.Bind(wx.EVT_BUTTON, lambda _e: self.say_current_line())
            root.Add(say, 0, wx.ALL, 8)

            self._timer = wx.Timer(self._frame)
            self._frame.Bind(wx.EVT_TIMER, lambda _e: self.tick(), self._timer)

        self._frame.SetSizer(root)
        self._frame.Bind(wx.EVT_CLOSE, self._on_close)
        self._frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        # The Player closing takes this window with it, without a close event;
        # the clock must stop with the window, never tick into a freed one.
        self._frame.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.set_lyrics(song, lyrics)

    @staticmethod
    def title_for(song: str) -> str:
        """The window title for *song*; a literal f-string in ``__init__`` too,
        so the F1 audit can read its prefix."""
        return f"{TITLE_PREFIX} {song}"

    # -- the window ------------------------------------------------------------

    @property
    def frame(self) -> Any:
        return self._frame

    @property
    def text(self) -> Any:
        return self._text

    @property
    def song(self) -> str:
        return self._song

    @property
    def is_synced(self) -> bool:
        return bool(self._lines)

    def set_lyrics(self, song: str, lyrics: Lyrics) -> None:
        """Show *lyrics* for *song*, replacing whatever was there."""
        self._song = song
        self._frame.SetTitle(self.title_for(song))
        self._text.SetName(f"Lyrics for {song}")
        self._lines = parse_lrc(lyrics.synced) if self._position_ms is not None else ()
        self._index = -1
        if self._lines:
            # One text line per timed line, blank breaks included, so line N of
            # the control is line N of the song and the caret can be put on it.
            self._text.SetValue("\n".join(line.text for line in self._lines))
        else:
            self._text.SetValue(lyrics.text)
        self._text.SetInsertionPoint(0)
        if self._follow is not None:
            self._follow.SetValue(self.is_synced)
            self._follow.Enable(self.is_synced)
        if self._current is not None:
            self._current.SetValue(
                BEFORE_FIRST if self.is_synced else "This song has words but no timings."
            )

    def show(self) -> None:
        """Show the window with the keyboard in the lyrics."""
        self._frame.Show()
        self._frame.Raise()
        self._text.SetFocus()
        if self._timer is not None and self.is_synced:
            self.tick()
            self._timer.Start(TICK_MS)

    def close(self) -> None:
        self._frame.Close()

    # -- following (the Player) --------------------------------------------------

    def current_line(self) -> str:
        """The line being sung now, or "" when there is none."""
        if 0 <= self._index < len(self._lines):
            return self._lines[self._index].text
        return ""

    def tick(self) -> bool:
        """One poll of the playhead. True when the current line changed.

        Returns rather than announces: nothing is spoken either way.
        """
        if self._position_ms is None or not self._lines:
            return False
        try:
            position = int(self._position_ms())
        except Exception:  # noqa: BLE001 - a stopped player must not raise here
            return False
        index = line_at(self._lines, position)
        if index == self._index:
            return False
        self._index = index
        if self._current is not None:
            if index < 0:
                self._current.SetValue(BEFORE_FIRST)
            else:
                self._current.SetValue(self._lines[index].text or BREAK)
        self._catch_up()
        return True

    def _catch_up(self) -> None:
        """Put the caret on the current line, when following."""
        if self._follow is None or not self._follow.GetValue() or self._index < 0:
            return
        position_in_text = self._text.XYToPosition(0, self._index)
        if position_in_text >= 0:
            self._text.SetInsertionPoint(position_in_text)
            self._text.ShowPosition(position_in_text)

    def say_current_line(self) -> None:
        """Speak the current line -- only ever because somebody asked."""
        if not self._lines:
            self._announce("This song has words but no timings.")
            return
        line = self.current_line()
        if self._index < 0:
            self._announce("The words have not started yet.")
        else:
            self._announce(line or "No words here; an instrumental break.")

    # -- events ----------------------------------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE or (event.ControlDown() and key in (ord("W"), wx.WXK_F4)):
            self.close()
            return
        event.Skip()

    def _on_destroy(self, event: Any) -> None:
        if event.GetEventObject() is self._frame and self._timer is not None:
            self._timer.Stop()
        event.Skip()

    def _on_close(self, event: Any) -> None:
        if self._timer is not None:
            self._timer.Stop()
        self._on_closed()
        event.Skip()
