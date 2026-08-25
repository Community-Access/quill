"""What the main Quill Radio window shows (main_view).

Reported 2026-08-24: "the favorites and browse window are showing, shouldn't
favorites be hidden unless called upon?" -- and then, exactly: "shouldn't we be
able to show any of the windows in the main frame of the app with a menu bar
based on the selection in settings?"

The old setting opened a *second* window at launch, so choosing Browse gave you
two windows and put the menu bar on the one you did not want. The choice is now
about what the main window itself shows, which is what these pin: the ids are
stable, an unreadable one can never leave the main window empty, and an upgrade
neither takes away a surface somebody chose nor adds one they did not.
"""

from __future__ import annotations

from quill.core.radio import main_view


def test_favorites_is_the_default_and_the_first_row() -> None:
    """A listener who never opens Preferences must not notice this exists."""
    assert main_view.MAIN_VIEWS[0][0] == main_view.FAVORITES
    assert main_view.normalize(None) == main_view.FAVORITES


def test_every_view_has_a_label_and_a_description() -> None:
    """A picker whose options are five nouns makes somebody try all five."""
    for view_id, label in main_view.MAIN_VIEWS:
        assert label
        assert main_view.description(view_id), view_id


def test_an_unreadable_setting_falls_back_to_favorites() -> None:
    """An empty main window is the one state a listener cannot leave by keyboard."""
    for junk in ("brwose", "", 7, None, {"browse": True}):
        assert main_view.normalize(junk) == main_view.FAVORITES


def test_index_and_id_round_trip_for_every_view() -> None:
    for position, (view_id, _label) in enumerate(main_view.MAIN_VIEWS):
        assert main_view.index_of(view_id) == position
        assert main_view.from_index(position) == view_id


def test_an_out_of_range_selection_is_favorites_rather_than_an_error() -> None:
    """Total for a wx selection, including the -1 an empty control reports."""
    for position in (-1, 99, None, "2"):
        assert main_view.from_index(position) == main_view.FAVORITES


# -- migration -------------------------------------------------------------------


def test_choosing_browse_at_startup_becomes_a_main_window_showing_browse() -> None:
    """Somebody who asked to launch into Browse wanted to *be* in Browse."""
    assert main_view.migrate_from_startup_window("browse") == "browse"


def test_no_startup_window_means_the_favorites_tree() -> None:
    assert main_view.migrate_from_startup_window("") == main_view.FAVORITES


def test_the_old_manage_favorites_choice_lands_on_the_favorites_tree() -> None:
    """Their main window showed the favorites tree either way."""
    assert main_view.migrate_from_startup_window("favorites") == main_view.FAVORITES


def test_an_unreadable_old_choice_does_not_invent_a_surface() -> None:
    assert main_view.migrate_from_startup_window("something else") == main_view.FAVORITES
    assert main_view.migrate_from_startup_window(None) == main_view.FAVORITES


def test_the_announcement_says_which_view_and_what_it_is() -> None:
    said = main_view.announcement("browse")

    assert "Browse Stations" in said
    assert "ACB Media" in said, "the description has to come with the name"
