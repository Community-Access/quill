"""The Video Window: a picture you can close without losing the sound.

The whole design is in one sentence. **Video is a view onto playback, never a
mode of playback.** Closing this window, or never opening it, leaves Quill Radio
behaving exactly as it did before video existed -- because mpv can be given a
window to draw into and have it taken away again while playing, so showing and
hiding the picture costs nothing and never loses your place.

Why a separate top-level frame rather than a panel in the main window:

1. The main window is a list-driven surface with a settled tab order and a
   screen-reader-tested layout. A docked video panel would perturb both every
   time it appeared.
2. A separate frame can be moved to a second monitor, which is what a sighted
   person in the room will want.
3. Closing it is unambiguous: one window, one Close, audio continues.

**The part video players usually get wrong** is the surface itself. An
mpv-rendered child window is, to assistive technology, an unnamed handle
containing nothing: a screen reader lands on it and says "graphic", or says
nothing. So the panel here carries a real accessible **name** (the video's
title) and a **description** that says what it is and where the controls are,
and it is a *pane* rather than a graphic -- claiming to be an image invites a
screen reader to hunt for alt text that cannot exist.

There are deliberately **no on-screen buttons**. Every command lives on the
Playback menu, on the Command Palette, and on a rebindable key. Duplicating them
into an unlabelled button strip is how video players become inaccessible.

One repository-specific hazard, named here so it is not rediscovered: the close
handler **must not open a modal dialog**. Quill Radio has already been bitten by
exactly this on wxMSW, where showing a modal from inside a close event made
Alt+F4 appear to do nothing while playing. If the close path ever needs to
confirm something, it confirms before the close, not during it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: What the video surface tells assistive technology it is. Not "graphic": it is
#: a container the application draws into, and there is no alt text to find.
SURFACE_DESCRIPTION = (
    "Video image. All playback controls are on the Playback menu, and work from "
    "this window. Ctrl+Shift+T reads the transcript, Ctrl+Shift+K toggles "
    "captions, F11 is full screen, and Ctrl+Shift+V or Escape closes the picture "
    "without stopping the sound."
)


def surface_name(title: str) -> str:
    """The video panel's accessible name.

    The title, so somebody navigating to the panel is told *which* video they
    have landed on -- and updated when the video changes, without firing an
    announcement, because the name is for someone who navigates there rather
    than for someone trying to listen.
    """
    return f"Video: {title}" if title else "Video image"


class VideoWindow:
    """A frame that mpv draws into, and a status line you can read on demand."""

    def __init__(
        self,
        parent: Any,
        *,
        title: str = "",
        announce: Callable[[str], None] | None = None,
        on_closed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _m: None)
        self._on_closed = on_closed or (lambda: None)

        self._frame = wx.Frame(parent, title="Quill Radio Video", style=wx.DEFAULT_FRAME_STYLE)
        self._frame.SetMinSize((480, 320))
        root = wx.BoxSizer(wx.VERTICAL)

        self._surface = wx.Panel(self._frame, style=wx.TAB_TRAVERSAL)
        self._surface.SetBackgroundColour(wx.Colour(0, 0, 0))
        self._surface.SetName(surface_name(title))
        self._surface.SetHelpText(SURFACE_DESCRIPTION)
        root.Add(self._surface, 1, wx.EXPAND)

        # Read on demand, never a live region: a position display that announces
        # itself is the single most common way a media player becomes unusable.
        self._status = wx.TextCtrl(
            self._frame, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL
        )
        self._status.SetName("Video status: title, position, chapter and audio track")
        self._status.SetHelpText(
            "A read-on-demand status line -- it never announces itself. Arrow "
            "through it for the title, position, chapter and audio track."
        )
        self._status.SetMinSize((-1, 56))
        root.Add(self._status, 0, wx.EXPAND)

        self._frame.SetSizer(root)
        self._frame.Bind(wx.EVT_CLOSE, self._on_close)
        self._frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    # -- the window ------------------------------------------------------------

    @property
    def frame(self) -> Any:
        return self._frame

    @property
    def surface(self) -> Any:
        return self._surface

    def handle(self) -> int | None:
        """The window handle mpv renders into, or ``None`` if it has none yet."""
        try:
            return int(self._surface.GetHandle())
        except Exception:  # noqa: BLE001 - a platform without a native handle
            return None

    def show(self) -> None:
        """Show the window and put focus on the picture, once."""
        self._frame.Show()
        self._frame.Raise()
        # Deliberate, and only here: opening the window focuses the surface so
        # the listener is told where they are. Nothing after this moves focus
        # without a user action.
        self._surface.SetFocus()

    def set_title(self, title: str) -> None:
        """Update the accessible name when the video changes.

        Silently: the name is for somebody who navigates to the panel, not an
        announcement for somebody who is trying to listen.
        """
        self._surface.SetName(surface_name(title))

    def set_status(self, text: str) -> None:
        """Replace the status line. Never announced -- it is read on demand."""
        self._status.SetValue(text)

    def close(self) -> None:
        self._frame.Close()

    def is_full_screen(self) -> bool:
        return bool(self._frame.IsFullScreen())

    def toggle_full_screen(self) -> bool:
        """Enter or leave full screen. Returns the new state, and says so.

        Both exits are spoken on entry rather than merely existing: WCAG's
        no-keyboard-trap rule is satisfied by there being a way out, and a
        listener is only served by being told what it is.
        """
        wanted = not self.is_full_screen()
        self._frame.ShowFullScreen(wanted)
        if wanted:
            self._announce("Full screen. Press F11 or Escape to leave.")
        else:
            self._announce("Left full screen.")
        return wanted

    def resize_to(self, width: int, height: int) -> None:
        """Size the window so the picture is *width* by *height*."""
        if width > 0 and height > 0:
            self._frame.SetClientSize((int(width), int(height) + 56))

    # -- events ----------------------------------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if key == wx.WXK_F11:
            self.toggle_full_screen()
            return
        if key == wx.WXK_ESCAPE:
            # Full screen first: Escape's job there is to get you back to a
            # window, not to take the picture away entirely.
            if self.is_full_screen():
                self.toggle_full_screen()
            else:
                self.close()
            return
        event.Skip()

    def _on_close(self, event: Any) -> None:
        # No modal dialog here, ever -- see the module docstring.
        self._on_closed()
        event.Skip()
