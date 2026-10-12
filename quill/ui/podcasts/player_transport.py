"""Accepted transport actions, including intent changes while an episode loads."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PodcastTransportMixin:
    def toggle_play_pause(self) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        if getattr(self, "_closed", False):
            return
        state = self._state.state
        if state is PodcastPlayerState.LOADING:
            self._pending_play_after_load = not self._pending_play_after_load
            self._set_state(
                PodcastPlayerState.LOADING,
                message=(
                    "Playback will start after loading."
                    if self._pending_play_after_load
                    else "Playback will remain paused after loading."
                ),
            )
            return
        if state not in (PodcastPlayerState.PLAYING, PodcastPlayerState.PAUSED):
            return
        if self._engine is None:
            self._set_state(
                PodcastPlayerState.ERROR, message="The playback engine is no longer available."
            )
            return
        try:
            if state is PodcastPlayerState.PLAYING:
                self._engine.pause()
            else:
                self._engine.play()
        except (OSError, RuntimeError):
            logger.exception("The podcast audio engine rejected a transport action")
            self._set_state(
                PodcastPlayerState.ERROR,
                message="The audio engine could not pause or resume playback.",
            )
            return
        if self._state.state is not state:
            return
        self._set_state(
            PodcastPlayerState.PAUSED
            if state is PodcastPlayerState.PLAYING
            else PodcastPlayerState.PLAYING
        )
        if state is PodcastPlayerState.PLAYING:
            self._checkpoint_current()

    def _on_loaded(self, _length_ms: int) -> None:
        from quill.ui.podcasts.player_controller import PodcastPlayerState

        if (
            getattr(self, "_closed", False)
            or self._engine is None
            or self._state.state is not PodcastPlayerState.LOADING
        ):
            return
        source = self._enhanced_source
        try:
            if self._is_enhanced():
                self._engine.play() if self._pending_play_after_load else self._engine.pause()
            elif self._resume_ms:
                self._engine.seek(self._resume_ms, resume=self._pending_play_after_load)
            elif self._pending_play_after_load:
                self._engine.play()
            else:
                self._engine.pause()
            self._engine.set_rate(self._pending_rate)
        except (OSError, RuntimeError):
            logger.exception("The podcast audio engine rejected playback after loading")
            self._set_state(
                PodcastPlayerState.ERROR,
                message="The audio engine could not start playback.",
            )
            return
        if self._state.state is not PodcastPlayerState.LOADING or source != self._enhanced_source:
            return
        self._resume_ms = 0
        self._set_state(
            PodcastPlayerState.PLAYING
            if self._pending_play_after_load
            else PodcastPlayerState.PAUSED
        )
