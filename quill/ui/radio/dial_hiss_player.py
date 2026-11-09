"""Plays the dial's soft hiss in a loop while a tuned station connects.

The idea, "FM Sound Between Stations", comes from BlindRadio by serrebidev (MIT).
The clip is Quill's own (:mod:`quill.core.radio.dial_hiss`).

**One fixed level, and Mute silences it.** The level is baked into the file, so
it does not follow the station's volume; the caller passes ``muted`` and a muted
radio gets no hiss at all.

**Why MCI and not mpv.** Dial tuning promises at most three mpv players, the
station and two neighbours, and a fourth for a noise loop would break that
promise for the least important sound in the feature. Windows' MCI (winmm,
the same route Studio's voice preview takes) loops a file on a named device of
its own, so stopping the hiss stops only the hiss, and an earcon played through
``winsound`` meanwhile neither stops it nor is cut off by it -- both of which
happened when the hiss was a ``winsound`` loop, because ``winsound`` has one
sound per process. ``winsound`` remains the fallback when MCI will not open
the clip. It plays on the default output device, which is the one honest
limitation: a radio routed to another sound card still hisses on the default one.

Nothing here is spoken, and nothing here reaches the network.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from quill.core.radio.dial_hiss import clip_path

_log = logging.getLogger(__name__)

__all__ = ["HissPlayer", "default_backend", "mci_backend", "winsound_backend"]

_ALIAS = "quill_dial_hiss"


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


def mci_backend(
    send: Callable[[str], int] | None = None,
) -> tuple[Callable[[Path], None], Callable[[], None]] | None:
    """``(start_loop(path), stop())`` on MCI's own device, or None without winmm.

    *send* runs one MCI command string and returns its error code (0 is
    success); tests pass a fake.
    """
    if send is None:
        try:
            import ctypes

            winmm = ctypes.windll.winmm  # type: ignore[attr-defined]
        except (ImportError, AttributeError, OSError):
            return None

        def send(command: str) -> int:
            return int(winmm.mciSendStringW(command, None, 0, None))

    sender = send

    def stop() -> None:
        sender(f"stop {_ALIAS}")
        sender(f"close {_ALIAS}")

    def start(path: Path) -> None:
        stop()
        if sender(f'open "{path}" type mpegvideo alias {_ALIAS}'):
            raise OSError("MCI could not open the dial hiss")
        if sender(f"play {_ALIAS} repeat"):
            sender(f"close {_ALIAS}")
            raise OSError("MCI could not loop the dial hiss")

    return (start, stop)


def default_backend() -> tuple[Callable[[Path], None], Callable[[], None]]:
    """MCI where it works; ``winsound`` when MCI cannot open the clip."""
    mci = mci_backend()
    fallback = winsound_backend()
    if mci is None:
        return fallback
    mci_start, mci_stop = mci
    fallback_start, fallback_stop = fallback
    on_fallback = [False]

    def start(path: Path) -> None:
        try:
            mci_start(path)
            on_fallback[0] = False
        except OSError:
            _log.debug("dial hiss: MCI refused the clip; using winsound", exc_info=True)
            fallback_start(path)
            on_fallback[0] = True

    def stop() -> None:
        if on_fallback[0]:
            fallback_stop()
            on_fallback[0] = False
        else:
            mci_stop()

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
            self._backend = default_backend()
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
