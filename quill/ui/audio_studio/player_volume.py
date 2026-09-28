"""Volume, mute and duck for the book player panel.

Extracted from ``player_panel.py`` on 2026-09-28, when binding Up-means-more
on its two sliders took the panel over its GATE-11 ceiling. These methods
own one thing: the relationship between the Volume slider (the level the
listener chose, and what unmute restores to), the engine's actual volume
(zero while muted, lowered while ducked) and the two callbacks the host
frame watches. The slider itself is built in the panel, beside its F1 help.

Mixed into :class:`quill.ui.audio_studio.player_panel.PlayerPanel`, which
supplies ``_engine``, ``_volume``, ``_mute_btn``, ``_muted``,
``_pre_mute_volume``, ``_announce``, ``_on_mute_cb`` and ``_on_volume_cb``.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.i18n import _


class PlayerVolumeMixin:
    _engine: Any
    _volume: wx.Slider
    _mute_btn: wx.Button
    _muted: bool
    _pre_mute_volume: int
    _duck_saved: int | None
    _on_mute_cb: Any
    _on_volume_cb: Any

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

    def volume(self) -> int:
        """The current volume (0-100)."""
        return int(self._volume.GetValue())

    def set_volume(self, percent: int) -> int:
        """Set the volume (0-100) and return what it ended up as.

        Moves the slider and then takes the *same* path a manual drag does,
        so the mute state, the engine and the on-volume callback all stay in
        step -- a keyboard volume change that only told the engine would
        leave the slider lying about the level, and the slider is what
        :meth:`toggle_mute` restores to.
        """
        self._volume.SetValue(max(0, min(100, int(percent))))
        self._on_volume(None)  # type: ignore[arg-type]
        return int(self._volume.GetValue())

    def duck(self, level_percent: int = 20) -> None:
        """Temporarily lower the *engine* volume for a spoken prompt.

        Leaves the slider (the user's chosen level) untouched so :meth:`unduck`
        restores exactly what was playing. Used while listening for a voice
        command so an earcon/announcement is clearly audible over the book
        without pausing or losing the user's place.
        """
        if self._engine is None:
            return
        self._duck_saved = int(self._volume.GetValue())
        self._engine.set_volume(min(self._duck_saved, max(0, int(level_percent))))

    def unduck(self) -> None:
        """Restore the volume ducked by :meth:`duck` (respecting mute)."""
        if self._engine is None:
            return
        saved = getattr(self, "_duck_saved", None)
        if saved is None:
            return
        self._engine.set_volume(0 if self._muted else saved)
        self._duck_saved = None

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
