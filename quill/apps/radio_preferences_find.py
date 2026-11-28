"""Preferences' "Find Streams" box: what Find Streams does while it works.

Its own module because ``radio_preferences`` is near its GATE-11 ceiling, the
same reason the dial and scrobbling boxes are. The ideas come from Andre Louis's
StreamSift (https://github.com/OnjLouis/StreamSift, MIT).

No access keys: this dialog has no letter left that is not already taken, and a
duplicate would be worse than none (GATE-14).
"""

from __future__ import annotations

from typing import Any

GROUP = "Find Streams"

SOUNDS_LABEL = "Play sounds while Find Streams searches"
SOUNDS_HELP = (
    "On by default. A soft sound every two seconds while a long scan runs, a "
    "different sound when a search finds nothing, and another when it could not "
    "finish. Turning this off silences those three sounds; what Find Streams "
    "says is not changed. The Sound Scheme list still applies on top."
)

FALLBACK_LABEL = "Try other ways when a website has no stream"
FALLBACK_HELP = (
    "Off by default. When on, and Find Streams finds no playable stream on the "
    "website you typed, it looks for the station in the public directories, Radio "
    "Browser, IPRD and Radio Garden, by the name in the address, and says which way "
    "found it. "
    "A station name typed on its own is always looked up in the directories, "
    "whatever this says. Nothing is contacted that Find Stations does not already "
    "use, and Safe Mode contacts nothing."
)


class FindRows:
    """The rows, and what to do with their answers."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._history = app._radio_history

    def checkboxes(self) -> list[Any]:
        from quill.ui.app_preferences_dialog import PreferenceCheckbox

        return [
            PreferenceCheckbox(
                SOUNDS_LABEL, SOUNDS_HELP, self._history.find_streams_sounds, group=GROUP
            ),
            PreferenceCheckbox(
                FALLBACK_LABEL, FALLBACK_HELP, self._history.find_streams_fallback, group=GROUP
            ),
        ]

    def apply(self, checks: list[bool]) -> None:
        self._history.find_streams_sounds, self._history.find_streams_fallback = (
            bool(value) for value in checks
        )


__all__ = ["GROUP", "FindRows"]
