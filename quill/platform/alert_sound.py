"""Play the weather-alert cue.

A small, dependency-light helper: resolve the effective sound file (the user's
chosen ``.wav`` when set and present, otherwise the bundled default) and play it
asynchronously. Windows uses ``winsound`` (the same async, non-blocking pattern
``main_frame_quill_key`` already uses for custom sounds); elsewhere it falls back
to ``wx.adv.Sound`` if wx is importable. Every call is best-effort and never
raises -- a missing or malformed sound must never break the alert itself, which
is always still shown and spoken.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

try:  # Windows stdlib; absent elsewhere.
    import winsound as _winsound
except ImportError:  # pragma: no cover - non-Windows
    _winsound = None  # type: ignore[assignment]


def bundled_alert_sound() -> Path:
    """Path to the default weather-alert WAV bundled with QUILL."""
    import quill

    return Path(quill.__file__).resolve().parent / "assets" / "audio" / "weather_alert.wav"


def resolve_alert_sound(custom_path: str = "") -> Path:
    """The sound file to play: the user's choice when it is set and exists, else
    the bundled default."""
    if custom_path:
        candidate = Path(custom_path)
        if candidate.is_file():
            return candidate
    return bundled_alert_sound()


#: Each play takes the next number; a repeat loop stops when it is no longer
#: the latest, so a second Play replaces the first instead of overlapping it.
_lock = threading.Lock()
_generation = 0
#: When the latest play should be over (``time.monotonic``), for "is it playing?".
_busy_until = 0.0


def _seconds(path: Path) -> float:
    try:
        import wave

        with wave.open(str(path), "rb") as clip:
            return clip.getnframes() / float(clip.getframerate() or 1)
    except Exception:  # noqa: BLE001 - unknown length: assume a short chime
        return 2.0


def play_alert_sound(custom_path: str = "", repeat: int = 1) -> int:
    """Play the alert cue ``repeat`` times (1-10), fire-and-forget. Best-effort:
    any failure is swallowed so a sound problem never blocks the alert. When
    repeating, the plays run back-to-back on a daemon thread so the caller (the
    UI thread) is never blocked. Returns this play's number, for
    :func:`stop_alert_sound`; 0 when nothing was played."""
    global _generation, _busy_until
    path = resolve_alert_sound(custom_path)
    if not path.is_file():
        return 0
    times = max(1, min(10, int(repeat)))
    with _lock:
        _generation += 1
        mine = _generation
        _busy_until = time.monotonic() + _seconds(path) * times
    if _winsound is not None and sys.platform.startswith("win"):
        if times == 1:
            try:
                _winsound.PlaySound(
                    str(path),
                    _winsound.SND_FILENAME | _winsound.SND_ASYNC | _winsound.SND_NODEFAULT,
                )
            except Exception:  # noqa: BLE001 - a sound must never crash the caller
                pass
            return mine

        # Repeat: play synchronously (each waits for the prior to finish) on a
        # background thread so consecutive plays don't cut each other off.
        def _run() -> None:
            for _ in range(times):
                if _generation != mine:
                    break  # stopped, or replaced by a newer play
                try:
                    _winsound.PlaySound(str(path), _winsound.SND_FILENAME | _winsound.SND_NODEFAULT)
                except Exception:  # noqa: BLE001
                    break

        threading.Thread(target=_run, name="QuillWeatherAlertSound", daemon=True).start()
        return mine
    try:  # pragma: no cover - non-Windows fallback
        import wx.adv  # type: ignore[import-untyped]

        sound = wx.adv.Sound(str(path))
        if sound.IsOk():
            sound.Play(wx.adv.SOUND_ASYNC)
    except Exception:  # noqa: BLE001
        pass
    return mine


def is_playing() -> bool:
    """Whether an alert sound, a preview or a real alert, is still playing.

    Judged from the file's length; a file :mod:`wave` cannot read counts as a
    two-second chime, so a long one may count as finished early.
    """
    return time.monotonic() < _busy_until


def stop_alert_sound(play: int = 0) -> bool:
    """Stop the alert sound, and any repeats still to come. True when it was
    still playing. With *play* (a number :func:`play_alert_sound` returned),
    only that play is stopped: a preview's Stop never cuts off a real alert
    that started after it (FUX-08)."""
    global _generation, _busy_until
    with _lock:
        if play and play != _generation:
            return False
        playing = time.monotonic() < _busy_until
        _generation += 1
        _busy_until = 0.0
    if _winsound is not None and sys.platform.startswith("win"):
        try:
            _winsound.PlaySound(None, 0)
        except Exception:  # noqa: BLE001 - nothing to stop
            pass
    return playing
