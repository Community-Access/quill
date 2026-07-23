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


def play_alert_sound(custom_path: str = "", repeat: int = 1) -> None:
    """Play the alert cue ``repeat`` times (1-10), fire-and-forget. Best-effort:
    any failure is swallowed so a sound problem never blocks the alert. When
    repeating, the plays run back-to-back on a daemon thread so the caller (the
    UI thread) is never blocked."""
    path = resolve_alert_sound(custom_path)
    if not path.is_file():
        return
    times = max(1, min(10, int(repeat)))
    if _winsound is not None and sys.platform.startswith("win"):
        if times == 1:
            try:
                _winsound.PlaySound(
                    str(path),
                    _winsound.SND_FILENAME | _winsound.SND_ASYNC | _winsound.SND_NODEFAULT,
                )
            except Exception:  # noqa: BLE001 - a sound must never crash the caller
                pass
            return

        # Repeat: play synchronously (each waits for the prior to finish) on a
        # background thread so consecutive plays don't cut each other off.
        def _run() -> None:
            for _ in range(times):
                try:
                    _winsound.PlaySound(str(path), _winsound.SND_FILENAME | _winsound.SND_NODEFAULT)
                except Exception:  # noqa: BLE001
                    break

        threading.Thread(target=_run, name="QuillWeatherAlertSound", daemon=True).start()
        return
    try:  # pragma: no cover - non-Windows fallback
        import wx.adv  # type: ignore[import-untyped]

        sound = wx.adv.Sound(str(path))
        if sound.IsOk():
            sound.Play(wx.adv.SOUND_ASYNC)
    except Exception:  # noqa: BLE001
        pass
