"""Send earcons to one chosen sound card, and fall back without going quiet.

:class:`~quill.platform.sound_player.SoundPlayer` normally plays through
whatever backend it detected, and every one of those plays on the system
default device. :class:`RoutedBackend` sits in front of that backend when an
app has been told which card its sounds belong on, and plays them there through
:mod:`quill.platform.windows.wave_out`.

Three promises, in order:

1. **A sound always plays.** When the chosen card is unplugged, asleep, or
   held by another program, the sound plays on the default device instead. A
   cue in the wrong place is a nuisance; a missing cue is indistinguishable
   from nothing having happened, which is the one thing an earcon must never be.
2. **It notices hardware changing.** The card is looked up by its endpoint
   GUID, not its position, and looked up again every few seconds, so a headset
   unplugged and plugged back in is found again without anybody touching a
   setting.
3. **It says so once.** ``on_route`` hears about a change of state -- on the
   card, or off it -- not about every sound, so the app can tell the listener
   "your sounds are on the default device for now" exactly once.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from quill.platform.sound_backends import WavBackend

__all__ = ["SILENT", "RoutedBackend", "SilentRoute", "route_for"]

logger = logging.getLogger(__name__)

#: The device name that means "this app makes no sounds".
SILENT = "none"

#: How long a lookup of the chosen card is trusted. Enumerating waveOut costs
#: well under a millisecond, but an earcon burst should not pay it per sound;
#: and a card plugged back in is found within this long.
_RESOLVE_SECONDS = 3.0


class RoutedBackend:
    """Plays on the device named *device*, or on *fallback* when it cannot.

    *device* is a saved device name in any spelling
    :func:`~quill.platform.windows.wave_out.device_guid` reads -- in practice
    the ``wasapi/{guid}`` the radio's own setting uses. *on_route* is called
    with True when sounds start reaching the card and False when they stop,
    on whichever thread played the sound; never per sound.
    """

    def __init__(
        self,
        device: str,
        fallback: WavBackend,
        on_route: Callable[[bool], None] | None = None,
    ) -> None:
        self.device = str(device or "").strip()
        self._fallback = fallback
        self._on_route = on_route
        self._lock = threading.Lock()
        self._player: object | None = None
        self._checked_at = float("-inf")
        self._volume = 1.0
        self._routed: bool | None = None

    # -- the WavBackend protocol -------------------------------------------

    def play_wav(self, wav: bytes) -> None:
        player = self._current_player()
        played = False
        if player is not None:
            try:
                played = bool(player.play_wav(wav))  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                played = False
        if not played:
            self._fallback.play_wav(wav)
        self._report(played)

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        player = self._current_player()
        if player is not None:
            try:
                if player.play_wav_blocking(wav, timeout):  # type: ignore[attr-defined]
                    self._report(True)
                    return True
            except Exception:  # noqa: BLE001
                pass
        self._report(False)
        blocking = getattr(self._fallback, "play_wav_blocking", None)
        return bool(callable(blocking) and blocking(wav, timeout))

    def set_volume(self, volume: float) -> None:
        self._volume = volume
        self._fallback.set_volume(volume)
        player = self._player
        if player is not None:
            player.set_volume(volume)  # type: ignore[attr-defined]

    def shutdown(self, timeout: float = 2.0) -> None:
        """Release the card. The fallback belongs to the player, not to us."""
        with self._lock:
            player, self._player = self._player, None
        if player is not None:
            try:
                player.shutdown(timeout=timeout)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass

    # -- routing -----------------------------------------------------------

    def available(self) -> bool:
        """Whether the chosen card can be reached right now (looks again)."""
        with self._lock:
            self._checked_at = float("-inf")
        return self._current_player() is not None

    def _current_player(self) -> object | None:
        now = time.monotonic()
        with self._lock:
            if now - self._checked_at < _RESOLVE_SECONDS:
                return self._player
            self._checked_at = now
            stale = self._player
            index = self._resolve()
            if stale is not None and getattr(stale, "device_index", None) == index:
                return stale
            self._player = None
            if index is not None:
                try:
                    from quill.platform.windows.wave_out import WaveOutPlayer

                    self._player = WaveOutPlayer(index)
                    self._player.set_volume(self._volume)  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    logger.debug("sound routing: could not open device %s", index, exc_info=True)
                    self._player = None
            current = self._player
        if stale is not None and stale is not current:
            try:
                stale.shutdown(timeout=0.5)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        return current

    def _resolve(self) -> int | None:
        try:
            from quill.platform.windows.wave_out import find_device_index

            return find_device_index(self.device)
        except Exception:  # noqa: BLE001 - no waveOut is "not reachable"
            return None

    def _report(self, routed: bool) -> None:
        if routed == self._routed:
            return
        self._routed = routed
        callback = self._on_route
        if callback is None:
            return
        try:
            callback(routed)
        except Exception:  # noqa: BLE001 - a listener must not cost a sound
            logger.debug("sound routing: on_route raised", exc_info=True)


class SilentRoute:
    """Where sounds go when an app's setting is None (no sounds): nowhere.

    A route rather than the player's mute, on purpose: mute belongs to the
    family-wide sound switch and to Quiet Mode, and an app that has chosen
    silence must not be woken by somebody turning those back on.
    """

    device = SILENT

    def play_wav(self, wav: bytes) -> None:
        return None

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        return True  # "finished" -- there is nothing to wait for or fall back to

    def set_volume(self, volume: float) -> None:
        return None

    def shutdown(self, timeout: float = 2.0) -> None:
        return None

    def available(self) -> bool:
        return True


def route_for(device: str, fallback: WavBackend, on_route: object = None) -> WavBackend:
    """The backend for setting *device*: the default, silence, or a card."""
    name = str(device or "").strip()
    if not name:
        return fallback
    if name == SILENT:
        return SilentRoute()
    return RoutedBackend(name, fallback, on_route)  # type: ignore[arg-type]
