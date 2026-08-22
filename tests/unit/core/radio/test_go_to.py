"""Go To: ten positions, and a numbering that does not move.

The stability *is* the feature. Ctrl+1..9 already lists open windows and already
renumbers as they open and close, so position can never become memory there.
These tests defend the one property that makes a second list worth having.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.radio import go_to


def test_ten_positions_numbered_one_to_nine_then_zero() -> None:
    assert go_to.MAX_ENTRIES == 10
    assert go_to.position_key(0) == "1"
    assert go_to.position_key(8) == "9"
    assert go_to.position_key(9) == "0"
    assert go_to.position_key(10) == ""


def test_the_default_fills_all_ten() -> None:
    layout = go_to.default_layout()
    assert len(layout.order) == go_to.MAX_ENTRIES
    assert layout.order[0] == "favorites"
    assert layout.order[9] == "preferences"


def test_a_destination_added_later_lands_in_the_pool_not_the_menu() -> None:
    """The whole promise: a numbering you have learned survives an upgrade.

    A new destination is pooled by derivation, not by migration -- there is no
    code path that can insert one into somebody's menu.
    """
    saved = go_to.GoToLayout(order=["favorites", "browse"])
    repaired = go_to.repair(saved)
    assert repaired.order == ["favorites", "browse"]
    assert "recordings" in repaired.available_ids()
    assert "preferences" in repaired.available_ids()


def test_an_unknown_id_in_a_saved_layout_is_dropped_not_fatal() -> None:
    """A layout naming a destination we have since removed must degrade to a
    working menu, never to no app."""
    saved = go_to.GoToLayout(order=["favorites", "a_destination_we_removed", "browse"])
    assert go_to.repair(saved).order == ["favorites", "browse"]


def test_a_duplicated_id_is_collapsed() -> None:
    saved = go_to.GoToLayout(order=["favorites", "favorites", "browse"])
    assert go_to.repair(saved).order == ["favorites", "browse"]


def test_an_emptied_layout_falls_back_to_the_default_rather_than_nothing() -> None:
    assert go_to.repair(go_to.GoToLayout(order=[])).order == list(go_to.DEFAULT_ORDER)


def test_a_layout_longer_than_the_number_row_is_capped() -> None:
    every = [d.id for d in go_to.DESTINATIONS]
    assert len(every) > go_to.MAX_ENTRIES
    assert len(go_to.repair(go_to.GoToLayout(order=every)).order) == go_to.MAX_ENTRIES


def test_the_menu_refuses_an_eleventh_entry_with_a_reason() -> None:
    """A sentence, not a disabled button: a control that says only no has to be
    guessed at."""
    refusal = go_to.refusal_for_adding(go_to.default_layout())
    assert refusal
    assert "ten" in refusal.lower()
    assert refusal.endswith(".")
    assert not go_to.refusal_for_adding(go_to.GoToLayout(order=["favorites"]))


def test_the_menu_refuses_to_be_emptied() -> None:
    one = go_to.GoToLayout(order=["favorites"])
    refusal = go_to.refusal_for_removing(one, "favorites")
    assert refusal and refusal.endswith(".")
    two = go_to.GoToLayout(order=["favorites", "browse"])
    assert not go_to.refusal_for_removing(two, "favorites")


def test_every_destination_names_a_distinct_id_and_a_handler() -> None:
    ids = [d.id for d in go_to.DESTINATIONS]
    assert len(ids) == len(set(ids)), "two destinations share an id"
    for d in go_to.DESTINATIONS:
        assert d.opens, f"{d.id} names no handler"
        assert d.title, f"{d.id} has no title"


def test_the_rows_that_advertise_a_key_advertise_a_real_one() -> None:
    """The popup teaches: a row showing a key somebody cannot press teaches the
    wrong thing, which is worse than showing none."""
    for d in go_to.DESTINATIONS:
        if d.key:
            assert d.key.startswith(("Ctrl", "Alt", "Shift", "F")), d.key


def test_a_layout_round_trips_through_disk(tmp_path: Path) -> None:
    layout = go_to.GoToLayout(order=["browse", "favorites", "player"])
    go_to.save_layout(tmp_path, layout)
    assert go_to.load_layout(tmp_path).order == ["browse", "favorites", "player"]


def test_a_missing_file_reads_as_the_default(tmp_path: Path) -> None:
    assert go_to.load_layout(tmp_path).order == list(go_to.DEFAULT_ORDER)


def test_a_corrupt_file_reads_as_the_default(tmp_path: Path) -> None:
    (tmp_path / "radio-go-to.json").write_text("{ not json", encoding="utf-8")
    assert go_to.load_layout(tmp_path).order == list(go_to.DEFAULT_ORDER)


def test_saving_repairs_rather_than_writing_something_unloadable(tmp_path: Path) -> None:
    go_to.save_layout(tmp_path, go_to.GoToLayout(order=["favorites", "nonsense", "favorites"]))
    assert go_to.load_layout(tmp_path).order == ["favorites"]


# -- the startup preference ----------------------------------------------------


def test_open_browse_at_startup_defaults_off_and_round_trips(tmp_path: Path) -> None:
    """Deliberately one checkbox, not a "which window opens" picker: a setting
    that changes where you land is expensive for somebody driving by keyboard."""
    from quill.core.radio import history as radio_history

    fresh = radio_history.RadioHistory()
    assert fresh.open_browse_at_startup is False
    fresh.open_browse_at_startup = True
    radio_history.save_history(tmp_path, fresh)
    assert radio_history.load_history(tmp_path).open_browse_at_startup is True


def test_browse_opens_over_the_main_window_not_instead_of_it() -> None:
    """Closing Browse has to leave you somewhere real rather than nowhere."""
    # parents[4], not [3]: this file is four directories deep under the repo
    # root (tests/unit/core/radio), one deeper than tests/unit/ui.
    radio = (Path(__file__).resolve().parents[4] / "quill" / "apps" / "radio.py").read_text(
        encoding="utf-8"
    )
    assert "if self._radio_history.open_browse_at_startup:" in radio
    assert "wx.CallAfter(self.open_browse_stations)" in radio
