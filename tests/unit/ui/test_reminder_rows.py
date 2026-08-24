"""Reminders on an ordinary row, and the priority that means something (7.1, 7.3).

Two things list.md called out as promises the code did not keep:

* The store had taken ``station``, ``episode`` and ``other`` kinds since it was
  written, and only calendar programmes could produce one -- so three quarters
  of the vocabulary was decoration.
* ``PRIORITY_HIGH`` existed and nothing could set it, and nothing read it. A
  stored value nothing can set is a promise the UI does not keep; a stored
  value nothing *reads* is worse, because it looks kept.

Both are now real, and the priority is the interesting one: it has to work on
its own, without the standing let-reminders-through switch, or it does nothing
for the only person who would reach for it.
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from types import SimpleNamespace

import pytest

from quill.core.quiet_hours import Kind, QuietHours, silences
from quill.core.radio import reminders, row_reminders
from quill.core.radio.row_actions import RowAction

SHOWTIME = datetime(2026, 8, 26, 19, 0, tzinfo=UTC)


class _Dialog:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.dialog = None

    def _announce(self, message: str) -> None:
        self.said.append(message)


def _station(url: str = "https://s/live", name: str = "Main Menu") -> SimpleNamespace:
    return SimpleNamespace(stream_url=url, name=name)


# -- the paired verb --------------------------------------------------------------


def test_a_row_with_no_reminder_offers_to_set_one() -> None:
    action = row_reminders.reminder_action(RowAction, has_reminder=False)
    assert action.id == row_reminders.SET_REMINDER
    assert "&" in action.label


def test_a_row_that_has_one_offers_to_remove_it_instead() -> None:
    """A menu that cannot tell you what you already did is a menu you have to
    remember for -- which is the job a reminder exists to take off somebody."""
    action = row_reminders.reminder_action(RowAction, has_reminder=True)
    assert action.id == row_reminders.REMOVE_REMINDER


def test_the_two_verbs_never_appear_together() -> None:
    assert row_reminders.SET_REMINDER != row_reminders.REMOVE_REMINDER


def test_every_station_row_carries_the_verb() -> None:
    from quill.core.radio import row_actions

    actions = row_actions.actions_for("station", station=_station())
    assert row_reminders.SET_REMINDER in [action.id for action in actions]


def test_a_row_that_already_has_one_shows_the_other_verb() -> None:
    from quill.core.radio import row_actions

    actions = row_actions.actions_for("station", station=_station(), has_reminder=True)
    ids = [action.id for action in actions]

    assert row_reminders.REMOVE_REMINDER in ids
    assert row_reminders.SET_REMINDER not in ids


# -- the target -------------------------------------------------------------------


def test_a_row_is_identified_by_its_stream_address() -> None:
    """A favourite renamed is the same station, and one station reached
    through two directories has two ids and one address -- the same argument
    bookmarks make, and deliberately the same answer."""
    from quill.ui.radio import row_reminders_wiring

    assert row_reminders_wiring.target_for(_station()) == "https://s/live"


def test_a_row_with_no_address_has_no_target() -> None:
    from quill.ui.radio import row_reminders_wiring

    assert row_reminders_wiring.target_for(SimpleNamespace(stream_url="")) == ""
    assert row_reminders_wiring.target_for(None) == ""


def test_setting_one_on_a_row_with_no_address_refuses_and_says_why() -> None:
    from quill.ui.radio import row_reminders_wiring

    dialog = _Dialog()
    row_reminders_wiring.set_reminder(dialog, None, SimpleNamespace(stream_url="", name="X"))

    assert "no address" in dialog.said[-1]


def test_asking_whether_a_row_has_one_never_raises(monkeypatch) -> None:
    """The only cost of being wrong is the menu offering Set when it could
    have offered Remove. The cost of raising is a menu that does not open."""
    from quill.ui.radio import row_reminders_wiring

    monkeypatch.setattr(
        "quill.core.paths.app_data_dir", lambda: (_ for _ in ()).throw(RuntimeError("no disk"))
    )
    assert row_reminders_wiring.has_reminder(_station()) is False


def test_a_row_reminder_is_found_and_removed(tmp_path, monkeypatch) -> None:
    from quill.ui.radio import row_reminders_wiring

    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    reminders.add_reminder(
        tmp_path,
        "Main Menu",
        SHOWTIME,
        kind=reminders.KIND_STATION,
        target="https://s/live",
    )

    assert row_reminders_wiring.has_reminder(_station()) is True

    dialog = _Dialog()
    row_reminders_wiring.remove_reminder(dialog, _station())

    assert reminders.load_reminders(tmp_path) == []
    assert "Main Menu" in dialog.said[-1]


def test_removing_one_that_is_not_there_says_so(tmp_path, monkeypatch) -> None:
    from quill.ui.radio import row_reminders_wiring

    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    dialog = _Dialog()

    row_reminders_wiring.remove_reminder(dialog, _station())

    assert "no reminder on that row" in dialog.said[-1]


# -- priority actually does something (7.3) ---------------------------------------

QUIET = QuietHours(enabled=True, start=time(22, 0), end=time(7, 0))
MIDNIGHT = time(23, 30)


def test_an_ordinary_reminder_is_held_during_quiet_hours() -> None:
    assert silences(QUIET, Kind.REMINDER, MIDNIGHT) is True


def test_a_high_priority_reminder_comes_through_on_its_own() -> None:
    """On its own is the point. Requiring the standing switch as well would
    make this do nothing for the only person who would set it -- somebody who
    did *not* want every reminder through."""
    assert silences(QUIET, Kind.REMINDER, MIDNIGHT, high_priority=True) is False


def test_the_standing_switch_still_lets_everything_through() -> None:
    everything = QuietHours(enabled=True, start=time(22, 0), end=time(7, 0), allow_reminders=True)
    assert silences(everything, Kind.REMINDER, MIDNIGHT) is False


def test_priority_changes_nothing_outside_quiet_hours() -> None:
    noon = time(12, 0)
    assert silences(QUIET, Kind.REMINDER, noon) is False
    assert silences(QUIET, Kind.REMINDER, noon, high_priority=True) is False


def test_priority_is_a_reminder_idea_and_touches_no_other_kind() -> None:
    """A high-priority *download notice* is not a thing, and must not become
    one by accident."""
    assert silences(QUIET, Kind.DOWNLOAD, MIDNIGHT, high_priority=True) is True
    assert silences(QUIET, Kind.NEW_EPISODE, MIDNIGHT, high_priority=True) is True


def test_a_priority_survives_a_save_and_load(tmp_path) -> None:
    made = reminders.add_reminder(
        tmp_path, "Board meeting", SHOWTIME, target="a", priority=reminders.PRIORITY_HIGH
    )
    assert made.priority == reminders.PRIORITY_HIGH
    assert reminders.load_reminders(tmp_path)[0].priority == reminders.PRIORITY_HIGH


def test_an_unknown_priority_reads_as_normal(tmp_path) -> None:
    import json

    reminders.store_path(tmp_path).write_text(
        json.dumps([
            {
                "reminder_id": "r",
                "title": "X",
                "due": SHOWTIME.isoformat(),
                "priority": "catastrophic",
            }
        ]),
        encoding="utf-8",
    )
    assert reminders.load_reminders(tmp_path)[0].priority == reminders.PRIORITY_NORMAL


# -- the sound (7.4, 7.8) ---------------------------------------------------------


def test_the_reminder_sound_is_its_own_event() -> None:
    """Tellable from a download finishing without waiting for the words."""
    from quill.core.sound_events import SoundEvent

    assert SoundEvent.RADIO_REMINDER == "radio_reminder"
    assert SoundEvent.RADIO_REMINDER != SoundEvent.CAST_DOWNLOAD_COMPLETE


def test_the_bundled_pack_actually_ships_the_sound() -> None:
    """An event with no file is an event that plays nothing, silently."""
    import json
    from pathlib import Path

    pack = Path(__file__).resolve().parents[3] / "quill" / "assets" / "sound_packs" / "ink"
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    wav = manifest["events"].get("radio_reminder")

    assert wav, "the manifest has no entry for the reminder"
    assert (pack / wav).is_file(), "the manifest names a file that is not there"


def test_the_reminder_sound_can_be_turned_off_on_its_own(tmp_path) -> None:
    """Separate from the global per-event list: somebody who has turned most
    earcons off has probably not meant to silence the one thing they asked to
    be interrupted by."""
    from quill.core.radio.history import RadioHistory
    from quill.core.radio.history_store import load_history, save_history

    history = RadioHistory()
    assert history.reminder_sound is True

    history.reminder_sound = False
    history.reminder_default_lead_seconds = 1800
    save_history(tmp_path, history)

    back = load_history(tmp_path)
    assert back.reminder_sound is False
    assert back.reminder_default_lead_seconds == 1800


def test_an_older_history_file_keeps_the_sound_on(tmp_path) -> None:
    import json

    (tmp_path / "radio_history.json").write_text(json.dumps({}), encoding="utf-8")
    from quill.core.radio.history_store import load_history

    history = load_history(tmp_path)
    assert history.reminder_sound is True
    assert history.reminder_default_lead_seconds == 900


@pytest.mark.parametrize("seconds", [offered for offered, _label in reminders.LEAD_CHOICES])
def test_every_offered_lead_time_can_be_a_default(seconds: int) -> None:
    from quill.apps.radio_preferences import _lead_index

    assert reminders.LEAD_CHOICES[_lead_index(seconds)][0] == seconds
