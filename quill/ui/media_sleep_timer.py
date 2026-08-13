"""Tools > Media > Sleep Timer... -- a shared sleep timer for both Internet
Radio and Podcasts (Media menu, since it touches both surfaces).

Fades whichever of the two players is currently active down to silence over
the last stretch of the countdown, stops it once the timer reaches zero, then
restores the volume back to what it was before the fade started -- so the
next time you press play, it is not still quiet. Radio and Podcasts are
independent players (nothing stops one when the other starts), so both are
faded/stopped if both happen to be active.

Two 1.1.0 additions, both podcast-shaped and both degrading cleanly when
Radio is what is playing:

- **End of episode.** Not a duration at all but a target, so it re-reads the
  episode's remaining time on every tick: seek forward and the timer moves
  with you rather than cutting you off early or leaving you in silence. A
  live radio stream has no end, so this mode simply refuses to start there.
- **Extend.** A running timer can be pushed back without being restarted,
  which also undoes any fade already in progress -- the point of extending is
  that you are still listening, and it would be absurd to leave the volume
  where the fade had got to.
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
        #: "End of episode" mode: the deadline is re-derived from the playing
        #: episode on every tick instead of being fixed at start time.
        self._end_of_episode = False

    @property
    def is_active(self) -> bool:
        return self._end_time is not None

    @property
    def is_end_of_episode(self) -> bool:
        """Whether the running timer tracks the episode rather than a clock."""
        return self._end_of_episode and self._end_time is not None

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

    def start_end_of_episode(self) -> bool:
        """Stop when the playing episode does. False when nothing bounded is
        playing -- a live radio stream has no end to stop at, and pretending
        otherwise would be worse than saying so."""
        remaining = self._episode_remaining_seconds()
        if remaining is None:
            return False
        self.cancel()
        self._end_of_episode = True
        self._end_time = time.monotonic() + max(1.0, remaining)
        self._timer.Start(_TICK_MS)
        return True

    def extend(self, minutes: float) -> bool:
        """Push a running timer back by *minutes*; False when none is running.

        Also lifts any fade already applied: extending means you are still
        listening, so the volume goes straight back to what it was rather
        than staying wherever the fade had reached.
        """
        if self._end_time is None:
            return False
        self._restore_volumes()
        self._end_of_episode = False
        self._end_time = max(time.monotonic(), self._end_time) + max(0.0, minutes) * 60
        return True

    def cancel(self) -> None:
        """Stop the countdown early and restore any faded volume."""
        if self._end_time is None:
            return
        self._timer.Stop()
        self._restore_volumes()
        self._end_time = None
        self._end_of_episode = False

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

    def _episode_remaining_seconds(self) -> float | None:
        """How long the playing podcast episode has left, or None when there
        is no bounded episode playing (nothing loaded, radio, or a source
        whose length the engine cannot report yet)."""
        podcast = self._get_podcast_controller()
        if podcast is None or podcast.state.show_id is None:
            return None
        if podcast.state.state not in (PodcastPlayerState.PLAYING, PodcastPlayerState.PAUSED):
            return None
        length = podcast.length_ms()
        if length <= 0:
            return None
        return max(0.0, (length - podcast.position_ms()) / 1000.0)

    def _on_timer_tick(self, _event: object) -> None:
        if self._end_of_episode:
            # Re-derive the deadline: a seek (either way) must move the timer
            # with the episode, not leave it pointing at the old end.
            remaining_episode = self._episode_remaining_seconds()
            if remaining_episode is not None:
                self._end_time = time.monotonic() + remaining_episode
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
        self._end_of_episode = False
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
