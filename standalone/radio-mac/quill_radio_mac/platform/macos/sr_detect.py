"""Detect an active macOS screen reader (VoiceOver).

Mirrors the public surface of upstream ``quill.platform.windows.sr_detect``
so call sites (e.g. deciding whether to lean on VoiceOver announcements
alone or also start the :mod:`quill_radio_mac.platform.macos.tts`
self-voicing fallback) can dispatch by platform without special-casing the
return type: both modules expose ``detect_screen_reader() ->
ScreenReaderDetection`` with the same field names.

Detection works by scanning the process list for VoiceOver's process names,
via the ``ps`` command-line tool -- no pyobjc dependency, since a plain
subprocess call is sufficient and keeps this module usable even when
pyobjc is not installed. Ported verbatim from
``quill.platform.macos.sr_detect``; only this docstring was expanded for
the port.

Threading contract: :func:`detect_screen_reader` runs a blocking
subprocess and should be called off the UI thread (e.g. from a
:mod:`quill_radio_mac.core.tasks` worker) to avoid stalling the event loop;
it touches no AppKit / UI state so it is otherwise thread-safe.

macOS notes: on non-macOS platforms ``ps -axco command`` may not exist or
may list unrelated processes; in either case no VoiceOver-named process
will match and :func:`detect_screen_reader` returns a not-detected result
rather than raising -- ``subprocess.run`` failures are caught explicitly.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreenReaderDetection:
    """Result of a screen-reader detection scan."""

    detected: bool
    name: str
    source: str


# VoiceOver runs as "VoiceOver" with a helper "VoiceOverAgent".
_VOICEOVER_PROCESSES = ("VoiceOver", "VoiceOverAgent")


def detect_screen_reader(process_snapshot: str | None = None) -> ScreenReaderDetection:
    """Return whether VoiceOver appears to be running.

    *process_snapshot* is normally omitted; it exists so tests can pass a
    canned ``ps`` listing instead of shelling out for real.
    """
    snapshot = process_snapshot if process_snapshot is not None else _process_snapshot()
    lowered = snapshot.lower()
    for process_name in _VOICEOVER_PROCESSES:
        if process_name.lower() in lowered:
            return ScreenReaderDetection(detected=True, name="VoiceOver", source=process_name)
    return ScreenReaderDetection(detected=False, name="none", source="")


def _process_snapshot() -> str:
    """Return the current process command-name listing, or "" if it can't be read."""
    try:
        completed = subprocess.run(
            ["ps", "-axco", "command"],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
        )
    except OSError:
        return ""
    return completed.stdout
