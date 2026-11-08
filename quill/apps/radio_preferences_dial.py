"""Preferences' "Tune as I move through stations" box: dial tuning's seven settings.

Its own module because ``radio_preferences`` is near its GATE-11 ceiling. The
idea comes from BlindRadio by serrebidev (MIT); the design, agreed on
2026-11-07, is docs/design/blindradio-ideas/dial-tuning.md. Two rules from it
shape this box: dial tuning ships off, so nobody's arrow keys change after an
update, and every part of it is a setting.

The box leads with the check box that switches the rest on; the two choices
come after the check boxes (``PreferenceChoice.after_checks``) so the box reads
in the order a person decides. No access keys: this dialog has no letter left
that is not already taken, and a duplicate would be worse than none (GATE-14).
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import dial_tuning as dial

GROUP = "Tune as I move through stations"

ENABLED_LABEL = "Tune as I move through stations"
ENABLED_HELP = (
    "Off by default. When on, the station you stop on in Favorites, Browse "
    "Stations, Networks or Search results starts playing after a short wait, "
    "like turning a radio dial. Holding an arrow plays nothing until you let go. "
    "Enter plays the station for real: it starts a fresh time-shift buffer and "
    "goes into Recently Played. Stations you only pass are not added to Recently "
    "Played, Song History, Listening Statistics or scrobbling. Podcasts, YouTube "
    "and folders never tune. Alt+Shift+U switches it on and off."
)
NEIGHBOURS_LABEL = "Keep the next and previous stations connected"
NEIGHBOURS_HELP = (
    "On by default. While you rest on a station, the stations either side of it "
    "stay connected with the sound off, so moving to one of them plays almost at "
    "once. That uses a little more of your connection: up to two extra streams."
)
METERED_LABEL = "Stop keeping them connected on a metered connection"
METERED_HELP = (
    "On by default. When Windows says your connection is metered, such as a "
    "phone hotspot, the next and previous stations are not kept connected, and "
    "each station connects only when you stop on it. When Windows cannot say, "
    "Quill Radio treats the connection as not metered."
)
HISS_LABEL = "Play a soft hiss between stations"
HISS_HELP = (
    "On by default. While a station you tuned to is connecting, a soft hiss "
    "plays, like a dial between stations, so there is no dead air. It plays at "
    "one fixed level whatever the station's volume, and Mute silences it. If a "
    "station does not answer, the hiss stops and Quill Radio says so once."
)
VOLUME_LABEL = "Remember each station's volume while tuning"
VOLUME_HELP = (
    "Off by default: stations you tune to play at the volume you are hearing, "
    "so the level does not jump as you move. Turn it on to have each station "
    "you tune to come in at its own remembered volume."
)
WAIT_LABEL = "Wait before tuning:"
WAIT_HELP = (
    "How long you have to stay on a station before it plays. 350 milliseconds, "
    "the default, is about a third of a second: long enough to move past a "
    "station without hearing it. Instant plays every station you stop on at once."
)
LEVEL_LABEL = "Hiss level:"
LEVEL_HELP = (
    "How loud the hiss between stations is: Low, the default, or Medium. It "
    "stays at that level whatever the volume of the station."
)


class DialRows:
    """The rows, and what to do with their answers."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._history = app._radio_history

    def checkboxes(self) -> list[Any]:
        from quill.ui.app_preferences_dialog import PreferenceCheckbox

        s = dial.DialSettings.from_history(self._history)
        return [
            PreferenceCheckbox(ENABLED_LABEL, ENABLED_HELP, s.enabled, group=GROUP),
            PreferenceCheckbox(NEIGHBOURS_LABEL, NEIGHBOURS_HELP, s.keep_neighbours, group=GROUP),
            PreferenceCheckbox(METERED_LABEL, METERED_HELP, s.metered_stop, group=GROUP),
            PreferenceCheckbox(HISS_LABEL, HISS_HELP, s.hiss, group=GROUP),
            PreferenceCheckbox(VOLUME_LABEL, VOLUME_HELP, s.remember_volume, group=GROUP),
        ]

    def choices(self) -> list[Any]:
        from quill.ui.app_preferences_dialog import PreferenceChoice

        s = dial.DialSettings.from_history(self._history)
        return [
            PreferenceChoice(
                WAIT_LABEL,
                WAIT_HELP,
                [label for _ms, label in dial.WAIT_CHOICES],
                dial.wait_index(s.wait_ms),
                group=GROUP,
                after_checks=True,
            ),
            PreferenceChoice(
                LEVEL_LABEL,
                LEVEL_HELP,
                [label for _id, label in dial.HISS_LEVELS],
                dial.hiss_level_index(s.hiss_level),
                group=GROUP,
                after_checks=True,
            ),
        ]

    def apply(self, checks: list[bool], choice_indices: list[int]) -> str:
        """Save what came back and apply it now. Returns "" (nothing to add)."""
        history = self._history
        (
            history.dial_tuning,
            history.dial_keep_neighbours,
            history.dial_metered_stop,
            history.dial_hiss,
            history.dial_remember_volume,
        ) = (bool(value) for value in checks)
        wait, level = (int(value) for value in choice_indices)
        history.dial_wait_ms = dial.WAIT_CHOICES[min(max(0, wait), len(dial.WAIT_CHOICES) - 1)][0]
        history.dial_hiss_level = dial.HISS_LEVELS[min(max(0, level), len(dial.HISS_LEVELS) - 1)][0]
        from quill.ui.radio import dial_tuning_commands, dial_tuning_ui

        dial_ui = dial_tuning_ui.for_controller(getattr(self.app, "_radio_controller", None))
        if dial_ui is not None:
            dial_ui.reload_settings()
        dial_tuning_commands.sync_menu(self.app)
        return ""


__all__ = ["GROUP", "DialRows"]
