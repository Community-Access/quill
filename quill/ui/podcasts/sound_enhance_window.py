"""Sound Enhancements for podcasts, as a peer window (qc.md section 6, Phase 4).

The equaliser, Even Out Volume and Smart Speed are things to adjust *while
listening*, so this is a window beside the library rather than a dialog in
front of it. The controls are the shared ``SoundEnhanceDialog``'s, built into a
panel instead of a dialog, so Radio's modal Sound Enhancements and this window
cannot drift apart.

What changed from the dialog, and what did not:

* **OK became Apply.** It puts the values into effect for the podcast named at
  the top (or the shared default) exactly as OK did, and the window stays open.
* **Cancel became Close.** Nothing is saved until Apply, as before; Close,
  Escape and Ctrl+W hide the window and return focus to where you were.
* **Heard as you change it** (FUX-08, 2026-11-24). Each slider and box is
  heard on the playing episode a moment after it moves, the way Radio's Sound
  Enhancements works, through the controller's ``set_enhancement``, which
  saves nothing. Apply saves and keeps it. Close puts back what the window
  opened with, or what was last applied, so trying a change never keeps it.
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

#: How long a change waits, at most per try, for an episode reload to finish.
_WAIT_MS = 250


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
            "Closes this window and returns to where you were. A change you heard "
            "but did not apply is put back as it was."
        )
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(frame, close_btn, modeless=True)

    def _peer_panel(self, parent: object) -> object | None:
        return wx.Panel(parent, style=wx.TAB_TRAVERSAL)

    def _on_apply(self, _event: object) -> None:
        self._collect()
        self._peer_apply(self._result)
        # What was just applied is what Close keeps from now on.
        self._original_snapshot = self._live_snapshot()
        self._previewed = False

    def put_back(self) -> bool:
        """Undo what was heard but not applied. True when there was something."""
        try:
            self._live_timer.Stop()  # a change still waiting is not heard after Close
        except Exception:  # noqa: BLE001 - a timer already gone is stopped
            pass
        if not self._previewed or self._on_live_change is None:
            return False
        self._previewed = False
        try:
            self._on_live_change(self._original_snapshot)
        except Exception:  # noqa: BLE001 - putting back must never break Close
            return False
        return True


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
            self._editor.put_back()
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
            on_live_change=self._hear,
        )
        self._sizer.Add(self._editor.dialog, 1, wx.EXPAND)
        self.frame.Fit()

    def focus_target(self) -> Any:
        return self._editor._preset_choice if self._editor is not None else None

    def _apply(self, result: Any) -> None:
        self._host._podcast_apply_sound_enhancements(self._show, result)

    def _hear(self, snapshot: Any) -> None:
        """Play the window's values on the episode now, saving nothing."""
        host = self._host
        controller = getattr(host, "_podcast_controller", None)
        if controller is None or self._other_podcast():
            return
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        if controller.state.state is PodcastPlayerState.LOADING:
            # A reload is still under way: the latest change waits for it. A
            # second reload started now would come up paused, and from a raw
            # source at the start of the episode.
            self._waiting = snapshot
            if getattr(self, "_wait_timer", None) is None:
                self._wait_timer = wx.CallLater(_WAIT_MS, self._hear_waiting)
            return
        bass, mid, treble, compressor, smart_speed, _options = snapshot
        from quill.core.audio.compressor_levels import compressor_value

        library = host._podcast_library
        settings = library.effective_settings(self._show) if self._show else library.settings
        controller.set_enhancement(
            bass_db=bass,
            mid_db=mid,
            treble_db=treble,
            compressor_enabled=compressor_value(compressor, settings.compression_level),
            smart_speed_enabled=smart_speed,
        )

    def _hear_waiting(self) -> None:
        self._wait_timer = None
        snapshot, self._waiting = getattr(self, "_waiting", None), None
        if snapshot is not None:
            self._hear(snapshot)

    def _other_podcast(self) -> bool:
        """True when what is playing now is not the podcast this window names:
        its values are not tried on, or put back onto, another podcast."""
        now = self._host._podcast_enhance_context_show()
        return getattr(now, "id", None) != getattr(self._show, "id", None)

    def before_hide(self) -> None:
        """Close: put back what was heard but not applied, and say so."""
        if self._editor is not None and self._editor.put_back():
            announce = getattr(self._host, "_announce", None)
            if callable(announce):
                announce("Changes not applied were put back.")


def open_sound_enhancements_window(
    host: Any, *, focus: bool = True, opener: Any = None
) -> SoundEnhancementsWindow:
    """Open, or raise and refresh, the host's Sound Enhancements window."""
    from quill.ui.podcasts.peer_window import open_peer

    window: SoundEnhancementsWindow = open_peer(
        host, "_sound_enhancements_window", SoundEnhancementsWindow, focus=focus, opener=opener
    )
    return window
