"""Stream recovery for Quill Radio: a failing station heals itself (#1065).

On a playback error the recovery ladder runs off the UI thread
(:func:`quill.core.radio.recovery.recover_stream`): re-resolve a moved
StreamTheWorld mount, refresh the address from the directory, and -- unless the
listener turned it off -- scan the station's own website. A confident hit is
played at once **and written into the saved favorite**, so the repair happens
once rather than every session.

That second half is why this is its own module (extracted from
``main_frame_radio.py`` under GATE-11, 2026-09-28): the favorite was looked up
by the *healed* station, whose address is the new one. A favorite with no
directory id is keyed by its address, so it was never found and never healed,
and every session waited out the dead address and repaired it again -- the
slow start and "reconnect" a listener heard on KSPN. It is found by the station
that *failed* now.

``self`` is the RadioMixin host; both functions are called through its
``_radio_maybe_try_fallback_url`` / ``_radio_apply_recovery`` methods, which
tests and the controller already know.
"""

from __future__ import annotations

from typing import Any

__all__ = ["apply_recovery", "maybe_recover"]


def maybe_recover(self: Any, state: Any) -> None:
    """A station whose stream fails heals itself (#1065).

    On a playback error, run the recovery ladder off-thread: re-resolve a
    moved StreamTheWorld mount, refresh from the directory, and -- unless
    the user turned it off -- scan the station's own website (Triton players
    and "Listen Live" links included). A confident hit is played
    automatically; anything ambiguous is announced so the user can pick it
    up in Find Streams. One attempt per station per session, so a truly dead
    station never loops."""
    from quill.ui.radio.playback_state import RadioPlayerState

    station = state.station
    if state.state is not RadioPlayerState.ERROR or station is None or self._safe_mode:
        return
    key = station.station_uuid or station.stream_url
    if self._radio_fallback_tried == key:
        return
    self._radio_fallback_tried = key
    allow_website = bool(getattr(self._radio_history, "recover_from_website", True))

    def _recover(**_kwargs: object) -> object:
        from quill.core.radio.recovery import recover_stream

        return recover_stream(station, allow_website=allow_website, safe_mode=self._safe_mode)

    def _done(_op: str, result: object) -> None:
        self._wx.CallAfter(self._radio_apply_recovery, result, station)

    self._task_manager.submit(
        "radio-stream-recovery",
        _recover,
        on_success=_done,
        on_failure=lambda *_a: None,
    )


def apply_recovery(self: Any, result: object, failed: object = None) -> None:
    from quill.core.radio.recovery import RecoveryResult

    if not isinstance(result, RecoveryResult):
        return
    if result.station is not None:
        self._announce(result.message)
        # Self-heal the saved favorite so the next play starts from the good
        # URL, then play the healed station. Found by the station that
        # FAILED: a favorite with no directory id is keyed by its address,
        # and the healed station's address is the new one -- so looking it
        # up by that never found it, the favorite was never healed, and
        # every session waited out the dead address and repaired it again
        # (KSPN, reported 2026-09-28).
        favorite = None
        if failed is not None:
            favorite = self._radio_favorites.find(
                getattr(failed, "station_uuid", "") or getattr(failed, "stream_url", "")
            )
        if favorite is None:
            favorite = self._radio_favorites.find(
                result.station.station_uuid or result.station.stream_url
            )
        if favorite is not None:
            favorite.station = result.station
            self._save_radio_favorites()
        self._radio_controller.play_station(result.station)
        return
    # No confident stream -- announce whatever we learned (candidates to
    # try via Find Streams, or simply that nothing was found).
    if result.message:
        self._announce(result.message)
