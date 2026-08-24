"""Closing a window obeys the same preference that opening one obeys.

``show_modeless_surface`` checks ``announce_dialog_transitions`` before it says
"Entered Browse Stations" -- and every frame's own close handler said "Exited
Browse Stations." unconditionally, because the exit half was left to each
window to do for itself. A listener who had switched the cues off still heard
half of them (reported 2026-08-23).

One helper now owns the exit cue, so the two halves of one preference cannot
disagree again, and a new surface gets the rule without having to remember it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from quill.ui import dialog_contract


@pytest.fixture(autouse=True)
def _reset_policy():
    yield
    dialog_contract.set_transition_announcement_policy(None)


def test_the_exit_cue_is_spoken_when_the_listener_wants_transition_cues() -> None:
    dialog_contract.set_transition_announcement_policy(lambda: True)
    said: list[str] = []

    assert dialog_contract.announce_surface_exit("Browse Stations", said.append) is True
    assert said == ["Exited Browse Stations."]


def test_the_exit_cue_is_silent_when_they_do_not() -> None:
    """The bug: this was the half that never asked."""
    dialog_contract.set_transition_announcement_policy(lambda: False)
    said: list[str] = []

    assert dialog_contract.announce_surface_exit("Browse Stations", said.append) is False
    assert said == []


def test_no_announcer_at_all_says_nothing_and_does_not_raise() -> None:
    dialog_contract.set_transition_announcement_policy(lambda: True)

    assert dialog_contract.announce_surface_exit("Anything", None) is False


def test_a_policy_that_raises_leaves_the_cues_on() -> None:
    """A broken lookup must not silence an app; the default is the shipped one."""

    def _boom() -> bool:
        raise RuntimeError("no settings yet")

    dialog_contract.set_transition_announcement_policy(_boom)
    said: list[str] = []

    assert dialog_contract.announce_surface_exit("Player", said.append) is True
    assert said == ["Exited Player."]


def test_no_radio_surface_announces_its_own_exit_any_more() -> None:
    """The gate: a new window must not reinvent the unconditional cue.

    Scanned rather than asserted per file, because the failure mode is somebody
    adding a *tenth* window with `self._announce(f"Exited ...")` in its close
    handler and nobody noticing until a listener with the cues off hears it.
    """
    radio_ui = pathlib.Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio"
    offenders = []
    for source in sorted(radio_ui.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        for match in re.finditer(r"_announce\(\s*f?\"Exited ", text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{source.name}:{line}")

    assert offenders == [], (
        "These say 'Exited ...' directly instead of through "
        "dialog_contract.announce_surface_exit, so they ignore the "
        "announce_dialog_transitions preference:\n" + "\n".join(offenders)
    )


def test_every_radio_surface_that_closes_uses_the_helper() -> None:
    """And the other direction: the cue did not simply disappear."""
    radio_ui = pathlib.Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio"
    users = [
        source.name
        for source in sorted(radio_ui.glob("*.py"))
        if "announce_surface_exit(" in source.read_text(encoding="utf-8")
    ]

    # The nine windows that had one, and any that join them later.
    assert len(users) >= 9, users
    assert "browse_tree_dialog.py" in users
    assert "player_panel.py" in users
