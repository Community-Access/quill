"""Which URL Quill Radio's engine should actually load.

Extracted from :mod:`quill.ui.radio.player_controller` under GATE-11
(extract, never rebaseline). One question, asked in one place: the station's
own URL, or a local relay URL when Sound Enhancements have to be applied by
ffmpeg because the engine cannot apply them itself.

A mixin rather than a function because the answer depends on a dozen pieces
of the controller's own state (which engine is live, every enhancement
setting, the relay); passing them all would be a longer signature than the
method is.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from quill.core.audio_enhance import EnhanceError
from quill.core.radio.models import RadioStation

_log = logging.getLogger(__name__)

__all__ = ["PlaybackUrlMixin"]


class PlaybackUrlMixin:
    """The URL resolution half of :class:`RadioPlayerController`."""

    def _resolve_playback_url(self, station: RadioStation) -> str:
        """The URL the engine should load: the station's own URL, or a local
        relay URL when Sound Enhancements is active on the wx engine.

        On the mpv engine the graph applies natively (``af``) and the
        station URL is loaded directly -- no relay, no second ffmpeg
        process, no re-encode.

        The one exception is exact OptiLab playback, which **must** relay on
        every engine: the real engine is a separate process, so the audio has to
        physically pass through it, and there is no filter string that can
        express "someone else's DSP" to mpv. That is the whole cost of the
        option, and it is why it is opt-in and off by default."""
        self._enhance_relay.stop()
        graph = self._current_filter_graph()
        station = (
            station
            if not self._playback_url_override
            else replace(station, stream_url=self._playback_url_override)
        )
        exact = self._exact_live_spec()
        if exact is not None:
            if self._is_mpv_active():
                # The engine below is the polish; mpv must not also apply the
                # adaptation of it, or the stream is processed twice.
                try:
                    self._mpv_engine.set_filter_graph("")  # type: ignore[union-attr]
                except Exception:  # noqa: BLE001 - clearing must never block playback
                    _log.exception("mpv filter graph clear failed")
            try:
                return self._enhance_relay.start(
                    station.stream_url,
                    bass_db=self._eq_bass_db,
                    mid_db=self._eq_mid_db,
                    treble_db=self._eq_treble_db,
                    compressor_enabled=self._compressor_enabled,
                    channel_mode=self._channel_mode,
                    night_mode_enabled=self._night_mode_enabled,
                    exact_optilab=exact,
                )
            except EnhanceError as error:
                if self._on_enhance_error is not None:
                    self._on_enhance_error(str(error))
                return station.stream_url
        if self._is_mpv_active():
            try:
                self._mpv_engine.set_filter_graph(graph)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001 - filtering must never block playback
                _log.exception("mpv filter graph apply failed")
            return station.stream_url
        if not graph:
            return station.stream_url
        try:
            return self._enhance_relay.start(
                station.stream_url,
                bass_db=self._eq_bass_db,
                mid_db=self._eq_mid_db,
                treble_db=self._eq_treble_db,
                compressor_enabled=self._compressor_enabled,
                channel_mode=self._channel_mode,
                night_mode_enabled=self._night_mode_enabled,
                optilab_enabled=self._optilab_enabled,
                optilab_mode=self._optilab_mode,
                optilab_input_db=self._optilab_input_db,
                optilab_auto_adapt=self._optilab_auto_adapt,
            )
        except EnhanceError as error:
            if self._on_enhance_error is not None:
                self._on_enhance_error(str(error))
            return station.stream_url
