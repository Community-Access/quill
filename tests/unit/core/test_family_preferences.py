"""qc.md X-05: shared choices, only for apps that joined, never silent."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core import family_preferences as family


def test_nothing_is_shared_until_an_app_joins(tmp_path: Path) -> None:
    cast = SimpleNamespace(announce_dialog_transitions=True, action_feedback="both")
    family.publish(tmp_path, "cast", cast)
    radio = SimpleNamespace(announce_dialog_transitions=False)
    assert family.adopt(tmp_path, "radio", radio) == []


def test_joining_shares_and_the_next_app_adopts(tmp_path: Path) -> None:
    cast = SimpleNamespace(announce_dialog_transitions=True, action_feedback="speech")
    assert family.set_sharing(tmp_path, "cast", True, cast) == []
    radio = SimpleNamespace(announce_dialog_transitions=False, unrelated=1)
    adopted = family.set_sharing(tmp_path, "radio", True, radio)
    assert adopted == ["announce_dialog_transitions"] and radio.announce_dialog_transitions
    assert family.words_for(adopted) == "announce dialog transitions"


def test_leaving_stops_both_directions(tmp_path: Path) -> None:
    cast = SimpleNamespace(announce_dialog_transitions=True)
    family.set_sharing(tmp_path, "cast", True, cast)
    radio = SimpleNamespace(announce_dialog_transitions=False)
    family.set_sharing(tmp_path, "radio", True, radio)
    family.set_sharing(tmp_path, "radio", False, radio)
    cast.announce_dialog_transitions = False
    family.publish(tmp_path, "cast", cast)
    radio.announce_dialog_transitions = True
    assert family.adopt(tmp_path, "radio", radio) == []


def test_only_the_listed_choices_are_ever_shared() -> None:
    assert set(family.SHARED) == {"announce_dialog_transitions", "action_feedback"}
