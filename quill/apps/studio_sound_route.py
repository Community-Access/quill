"""Where Is the Sound? and Recording status in QUILL Studio (FUX-03).

Studio records (a demonstration, a live broadcast) and plays (the audiobook
player, voice previews). "Is the screen reader going into my recording?" and
"which microphone is this?" were answered only in part: Recording status named
the sources as "Microphone" and "System sound", never the device behind them,
and said nothing at all when the device had gone and silence was going in.

* **Recording status** (Ctrl+Alt+Shift+T, the tray and its global key) now names
  the microphone and sound card behind each source and says when one has gone
  (``screen_recorder._spoken_source``). It moved here from ``studio_demo``
  under GATE-11.
* **Where Is the Sound?** (Alt+Shift+A, the key it has in every media app) is
  the whole answer, said once: where Studio's own playback goes, the recording
  or broadcast as Recording status says it, the microphone recordings take and
  whether Windows lists it as connected, and another family app listening on
  that microphone. A microphone that is chosen is not proof of what was
  captured: the quick test in Record a Demonstration plays back what went in.

Studio has no output device of its own. Windows decides where it plays, and
Studio Mixer's Programs tab (or Windows' Volume mixer) can move it, so the
answer names the device Windows gives Studio rather than a setting Studio does
not have.
"""

from __future__ import annotations

import os
from typing import Any

from quill.ui.audio import sound_route

__all__ = ["StudioSoundRouteMixin", "compose"]


def _playback(*, app_output: Any = None, lister: Any = None) -> str:
    """Where Studio's players go: the device Windows gives Studio."""
    try:
        if app_output is None:
            from quill.platform.windows.audio_routing import app_output as windows_app_output

            app_output = windows_app_output
        moved = str(app_output(os.getpid()) or "")
    except Exception:  # noqa: BLE001 - no answer means Windows' default
        moved = ""
    device = sound_route.output_device(moved, lister=lister)
    return f"Studio's players and previews play {sound_route.on_device(device)}."


def _saved_microphone(prefs: dict[str, Any]) -> str | None:
    """The microphone recordings take, as saved; None when they take none."""
    for row in prefs.get("sources", []) if isinstance(prefs, dict) else []:
        if isinstance(row, dict) and row.get("kind") == "microphone":
            return str(row.get("device", "") or "")
    return None


def _microphone(prefs: dict[str, Any], *, lister: Any = None) -> str:
    name = _saved_microphone(prefs)
    if name is None:
        return ""
    device = sound_route.input_device(name, lister=lister)
    return f"Recordings use {sound_route.on_device(device).removeprefix('on ')}."


def compose(host: Any, *, app_output: Any = None, lister: Any = None, holder: Any = None) -> str:
    """The whole answer; the keyword arguments are for tests."""
    recorder = getattr(host, "_demo", None)
    live = getattr(host, "_live", None)
    playback = _playback(app_output=app_output, lister=lister)
    broadcast = f"Live broadcast: {live.status_line()}" if live is not None else ""
    if recorder is not None:
        # Recording first, and only where its sound comes from: the dropped
        # frames and space left are Recording status's, not this answer's.
        line = getattr(recorder, "sound_line", None) or recorder.status_line
        return sound_route.join([
            line(),
            broadcast,
            playback,
            sound_route.microphone_note("studio", holder=holder),
        ])
    busy = str(getattr(host, "_demo_busy", "") or "")
    try:
        prefs = host._demo_preferences()
    except Exception:  # noqa: BLE001 - unreadable settings: say nothing about them
        prefs = {}
    return sound_route.join([
        broadcast,
        f"{busy}." if busy else "No demonstration is recording.",
        _microphone(prefs, lister=lister),
        playback,
        sound_route.microphone_note("studio", holder=holder),
    ])


class StudioSoundRouteMixin:
    """The two readouts; the host is the Studio frame."""

    def where_is_sound(self) -> None:
        self._announce(compose(self))  # type: ignore[attr-defined]

    def speak_demonstration_status(self) -> None:
        recorder = getattr(self, "_demo", None)
        if recorder is None:
            busy = getattr(self, "_demo_busy", "")
            self._announce(busy + "." if busy else "No demonstration is recording.")  # type: ignore[attr-defined]
            return
        # Asked for: spoken even while the reader is recorded, as the user chose to.
        self._announce(recorder.status_line())  # type: ignore[attr-defined]

    def show_demonstration_window(self) -> None:
        status = getattr(self, "_demo_status", None)
        if not status:
            self._announce("No demonstration is recording.")  # type: ignore[attr-defined]
            return
        status.Show()
        status.Raise()
        status.text.SetFocus()
