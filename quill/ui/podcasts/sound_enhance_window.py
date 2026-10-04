"""Sound Enhancements for podcasts, as a peer window (qc.md section 6, Phase 4).

The equaliser, Even Out Volume and Smart Speed are things to adjust *while
listening*, so this is a window beside the library rather than a dialog in
front of it. The controls are the shared ``SoundEnhanceDialog``'s, built into a
panel instead of a dialog, so Radio's modal Sound Enhancements and this window
cannot drift apart.

What changed from the dialog, and what did not:

* **OK became Apply.** It puts the values into effect for the podcast named at
  the top (or the shared default) exactly as OK did, and the window stays open.
* **Cancel became Close.** Nothing is applied until Apply, as before; Close,
  Escape and Ctrl+W hide the window and return focus to where you were.
* **Asked for again**, the window is raised and re-read for whatever is playing
  now, so it never shows one podcast's values while naming another.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.ui.sound_enhance_dialog import SoundEnhanceDialog

__all__ = ["TITLE", "SoundEnhancementsWindow", "open_sound_enhancements_window"]

TITLE = "Sound Enhancements"


class _PeerEditor(SoundEnhanceDialog):
    """The shared controls in a panel, with Apply and Close for a peer."""

    def __init__(self, frame: Any, *, on_apply: Callable[[Any], None], **kwargs: Any) -> None:
        self._peer_apply = on_apply
        super().__init__(frame, **kwargs)
        apply_btn = wx.Window.FindWindowById(wx.ID_OK, self.dialog)
        apply_btn.SetLabel("Appl&y")
        apply_btn.SetHelpText(
            "Puts these settings into effect for the podcast named above and keeps "
            "the window open, so you can listen and adjust again."
        )
        close_btn = wx.Window.FindWindowById(wx.ID_CANCEL, self.dialog)
        close_btn.SetLabel("Close")
        close_btn.SetHelpText(
            "Closes this window and returns to where you were. Anything not applied "
            "is left as it was."
        )
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(frame, close_btn, modeless=True)

    def _peer_panel(self, parent: object) -> object | None:
        return wx.Panel(parent, style=wx.TAB_TRAVERSAL)

    def _on_apply(self, _event: object) -> None:
        self._collect()
        self._peer_apply(self._result)


class SoundEnhancementsWindow:
    """The frame; its contents are rebuilt for whatever is playing."""

    TITLE = TITLE
    MENU_TITLE = "Soun&d"

    def __init__(self, host: Any) -> None:
        self._host = host
        self._show: Any = None
        self._editor: _PeerEditor | None = None
        self.frame = wx.Frame(host.frame, title="Sound Enhancements")
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.frame.SetSizer(self._sizer)
        self.refresh()
        self.frame.CentreOnParent()

    def refresh(self) -> None:
        """Read the values afresh for what is playing now (or the shared default)."""
        host = self._host
        if self._editor is not None:
            self._sizer.Clear(delete_windows=True)
        show = host._podcast_enhance_context_show()
        library = host._podcast_library
        settings = library.effective_settings(show) if show else library.settings
        self._show = show
        self._editor = _PeerEditor(
            self.frame,
            on_apply=self._apply,
            bass_db=settings.eq_bass_db,
            mid_db=settings.eq_mid_db,
            treble_db=settings.eq_treble_db,
            compressor_enabled=settings.compressor_enabled,
            subject=show.title if show else "episode",
            show_smart_speed=True,
            smart_speed_enabled=settings.smart_speed_enabled,
            announce_cb=host._announce,
        )
        self._sizer.Add(self._editor.dialog, 1, wx.EXPAND)
        self.frame.Fit()

    def focus_target(self) -> Any:
        return self._editor._preset_choice if self._editor is not None else None

    def _apply(self, result: Any) -> None:
        self._host._podcast_apply_sound_enhancements(self._show, result)


def open_sound_enhancements_window(
    host: Any, *, focus: bool = True, opener: Any = None
) -> SoundEnhancementsWindow:
    """Open, or raise and refresh, the host's Sound Enhancements window."""
    from quill.ui.podcasts.peer_window import open_peer

    window: SoundEnhancementsWindow = open_peer(
        host, "_sound_enhancements_window", SoundEnhancementsWindow, focus=focus, opener=opener
    )
    return window
