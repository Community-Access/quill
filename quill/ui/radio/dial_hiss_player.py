"""Plays the dial's soft hiss in a loop while a tuned station connects.

The idea, "FM Sound Between Stations", comes from BlindRadio by serrebidev (MIT).
The clip is Quill's own (:mod:`quill.core.radio.dial_hiss`).

**One fixed level, and Mute silences it.** The level is baked into the file, so
it does not follow the station's volume; the caller passes ``muted`` and a muted
radio gets no hiss at all.

**Why ``winsound`` and not mpv.** Dial tuning promises at most three mpv players,
the station and two neighbours, and a fourth for a noise loop would break that
promise for the least important sound in the feature. ``winsound`` loops a file
asynchronously with no player to manage. It plays on the default output device,
which is the one honest limitation: a radio routed to another sound card still
hisses on the default one. An earcon played through ``winsound`` while the hiss
runs stops it, which is harmless -- dial tuning keeps its own earcons quiet.

Nothing here is spoken, and nothing here reaches the network.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from quill.core.radio.dial_hiss import clip_path

_log = logging.getLogger(__name__)

__all__ = ["HissPlayer", "winsound_backend"]


def winsound_backend() -> tuple[Callable[[Path], None], Callable[[], None]]:
    """``(start_loop(path), stop())`` on Windows; no-ops anywhere else."""
    try:
        import winsound
    except ImportError:  # not Windows: the hiss is a courtesy, never a failure
        return (lambda _path: None, lambda: None)

    flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
    flags |= winsound.SND_NODEFAULT

    def start(path: Path) -> None:
        winsound.PlaySound(str(path), flags)

    def stop() -> None:
        winsound.PlaySound(None, 0)

    return (start, stop)


class HissPlayer:
    """Starts and stops the loop; every call is idempotent and never raises."""

    def __init__(
        self,
        backend: tuple[Callable[[Path], None], Callable[[], None]] | None = None,
    ) -> None:
        self._backend = backend
        self._playing_level = ""

    @property
    def playing(self) -> bool:
        return bool(self._playing_level)

    def _start_stop(self) -> tuple[Callable[[Path], None], Callable[[], None]]:
        if self._backend is None:
            self._backend = winsound_backend()
        return self._backend

    def apply(self, wanted: bool, *, level: str, muted: bool) -> None:
        """Make the hiss match *wanted*: sounding at *level* unless *muted*."""
        target = level if (wanted and not muted) else ""
        if target == self._playing_level:
            return
        start, stop = self._start_stop()
        try:
            if not target:
                stop()
            else:
                start(clip_path(target))
        except Exception:  # noqa: BLE001 - a sound that will not play is silence
            _log.debug("dial hiss could not change", exc_info=True)
            target = ""
        self._playing_level = target

    def stop(self) -> None:
        self.apply(False, level="", muted=False)
