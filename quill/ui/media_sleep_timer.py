"""Tools > Media > Sleep Timer... -- a shared sleep timer for both Internet
Radio and Podcasts (Media menu, since it touches both surfaces).

Fades whichever of the two players is currently active down to silence over
the last stretch of the countdown, stops it once the timer reaches zero, then
restores the volume back to what it was before the fade started -- so the
next time you press play, it is not still quiet. Radio and Podcasts are
independent players (nothing stops one when the other starts), so both are
faded/stopped if both happen to be active.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import wx

from quill.ui.podcasts.player_controller import PodcastPlayerController, PodcastPlayerState
from quill.ui.radio.player_controller import RadioPlayerController, RadioPlayerState

#: Fade gently over the final stretch of the countdown, not the whole thing.
_FADE_WINDOW_SECONDS = 20.0
_TICK_MS = 1000


class SleepTimerController:
    """Owns the one sleep-timer countdown for the whole app."""

    def __init__(
        self,
        *,
        get_radio_controller: Callable[[], RadioPlayerController | None],
        get_podcast_controller: Callable[[], PodcastPlayerController | None],
        on_tick: Callable[[float], None] | None = None,
    ) -> None:
        self._get_radio_controller = get_radio_controller
        self._get_podcast_controller = get_podcast_controller
        self._on_tick = on_tick or (lambda _remaining_seconds: None)
        self._timer = wx.Timer()
        self._timer.Bind(wx.EVT_TIMER, self._on_timer_tick)
        self._end_time: float | None = None
        self._fade_start_volumes: dict[str, int] = {}

    @property
    def is_active(self) -> bool:
        return self._end_time is not None

    @property
    def remaining_seconds(self) -> float:
        if self._end_time is None:
            return 0.0
        return max(0.0, self._end_time - time.monotonic())

    def start(self, minutes: float) -> None:
        """Start (or restart) the countdown for *minutes* from now."""
        self.cancel()
        self._end_time = time.monotonic() + max(0.1, minutes) * 60
        self._timer.Start(_TICK_MS)

    def cancel(self) -> None:
        """Stop the countdown early and restore any faded volume."""
        if self._end_time is None:
            return
        self._timer.Stop()
        self._restore_volumes()
        self._end_time = None

    def shutdown(self) -> None:
        """Called once, from the frame's close path."""
        self._timer.Stop()

    # -- internal -----------------------------------------------------------

    def _active_controllers(self) -> list[tuple[str, object]]:
        pairs: list[tuple[str, object]] = []
        radio = self._get_radio_controller()
        if radio is not None and radio.state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.PAUSED,
        ):
            pairs.append(("radio", radio))
        podcast = self._get_podcast_controller()
        if podcast is not None and podcast.state.state in (
            PodcastPlayerState.PLAYING,
            PodcastPlayerState.PAUSED,
        ):
            pairs.append(("podcast", podcast))
        return pairs

    def _current_volume(self, name: str, controller: object) -> int:
        if name == "radio":
            return controller.state.volume_percent  # type: ignore[attr-defined]
        return controller.volume_percent  # type: ignore[attr-defined]

    def _on_timer_tick(self, _event: object) -> None:
        remaining = self.remaining_seconds
        if remaining <= 0:
            self._finish()
            return
        if remaining <= _FADE_WINDOW_SECONDS:
            self._apply_fade(remaining)
        self._on_tick(remaining)

    def _apply_fade(self, remaining: float) -> None:
        fraction = max(0.0, min(1.0, remaining / _FADE_WINDOW_SECONDS))
        for name, controller in self._active_controllers():
            if name not in self._fade_start_volumes:
                self._fade_start_volumes[name] = self._current_volume(name, controller)
            base = self._fade_start_volumes[name]
            controller.set_volume(int(round(base * fraction)))  # type: ignore[attr-defined]

    def _finish(self) -> None:
        self._timer.Stop()
        for _name, controller in self._active_controllers():
            controller.stop()  # type: ignore[attr-defined]
        self._restore_volumes()
        self._end_time = None
        self._on_tick(0.0)

    def _restore_volumes(self) -> None:
        radio = self._get_radio_controller()
        podcast = self._get_podcast_controller()
        by_name = {"radio": radio, "podcast": podcast}
        for name, volume in self._fade_start_volumes.items():
            controller = by_name.get(name)
            if controller is not None:
                controller.set_volume(volume)  # type: ignore[attr-defined]
        self._fade_start_volumes = {}
