"""Options a source declares, and the two that use them.

``radio2.md`` part VII: the source declares, the host renders, and adding an
option is a tuple rather than a dialog. What is pinned here is that contract --
the declaration, the cleaning on the way in and out, and the two places a
declared value actually changes what a listener sees.
"""

from __future__ import annotations

import json

import pytest

from quill.core.radio import radio_paradise as rp
from quill.core.radio import shoutcast, source_options


@pytest.fixture(autouse=True)
def _clean_slate() -> None:
    source_options.set_current({})
    yield
    source_options.set_current({})


# --- the contract -------------------------------------------------------------


def test_a_source_with_no_options_says_so_rather_than_guessing() -> None:
    assert source_options.options_for("tunein") == ()
    assert source_options.options_for("") == ()
    assert source_options.options_for(None) == ()


def test_an_unset_option_reads_as_its_default() -> None:
    assert source_options.value({}, "radioparadise_quality") == "320"
    assert source_options.chosen("shoutcast_show") == "all"


def test_an_illegal_value_reads_as_the_default_rather_than_as_itself() -> None:
    """A profile edited by hand, or an option whose choices changed."""
    assert source_options.value({"shoutcast_show": "banana"}, "shoutcast_show") == "all"


def test_unknown_keys_are_dropped_on_the_way_in() -> None:
    cleaned = source_options.normalize({"shoutcast_show": "live", "gone": "x"})
    assert cleaned == {"shoutcast_show": "live"}


def test_setting_one_option_leaves_the_others_alone() -> None:
    stored = source_options.with_value({"shoutcast_show": "live"}, "radioparadise_quality", "flac")
    assert stored == {"shoutcast_show": "live", "radioparadise_quality": "flac"}


def test_a_choice_reads_back_in_words() -> None:
    stored = {"radioparadise_quality": "flac"}
    assert "FLAC" in source_options.describe("radioparadise_quality", stored)


def test_every_declared_option_is_reachable_from_its_source() -> None:
    for source_id, options in source_options.OPTIONS_BY_SOURCE.items():
        assert options, f"{source_id} declares an empty tuple"
        for option in options:
            assert source_options.option(option.key) is option


# --- what the options actually do ---------------------------------------------

_LIST_CHAN = json.dumps([
    {"chan": "0", "title": "The Main Mix", "slug": "main-mix", "current_listeners": "10"}
])


def test_the_chosen_quality_is_the_row_enter_lands_on() -> None:
    source_options.set_current({"radioparadise_quality": "flac"})
    rows = rp.parse_channels(_LIST_CHAN, preferred_quality="flac")
    assert rows[0].codec == "FLAC"
    # ...and nothing is hidden by choosing: all six qualities are still listed
    # (twice over here, because Radio 2050 rides along -- the API omits it and
    # this module adds it back).
    main_mix = [row for row in rows if row.name.startswith("The Main Mix")]
    assert len(main_mix) == 6


def test_the_default_quality_is_the_best_lossy_one() -> None:
    rows = rp.parse_channels(_LIST_CHAN)
    assert rows[0].name.endswith("(320k AAC)")


def test_an_unknown_quality_leaves_the_order_alone() -> None:
    assert rp.qualities_in_order("banana") == rp.QUALITIES
    assert rp.qualities_in_order("") == rp.QUALITIES


_SHOUTCAST_JSON = json.dumps([
    {"ID": 1, "Name": "Live One", "Format": "audio/mpeg", "Listeners": 400},
    {"ID": 2, "Name": "Parked", "Format": "audio/mpeg", "Listeners": 0},
])


def test_shoutcast_shows_everything_by_default() -> None:
    """ "The directory lists it" is the honest default."""
    assert len(shoutcast.parse_stations(_SHOUTCAST_JSON)) == 2


def test_shoutcast_can_be_asked_for_only_the_stations_on_the_air() -> None:
    source_options.set_current({"shoutcast_show": "live"})
    rows = shoutcast.parse_stations(_SHOUTCAST_JSON)
    assert [row.name for row in rows] == ["Live One"]


def test_the_values_in_force_survive_a_round_trip_through_the_store(tmp_path) -> None:
    from quill.core.radio import (
        history,  # noqa: F401 - import order, see history.py
        history_store,
    )

    record = history_store.load_history(tmp_path)
    record.source_options = {"shoutcast_show": "live"}
    history_store.save_history(tmp_path, record)

    source_options.set_current({})
    reloaded = history_store.load_history(tmp_path)

    assert reloaded.source_options == {"shoutcast_show": "live"}
    # Loading also puts them in force, because the source clients have no route
    # to this record and read the values from the module.
    assert source_options.chosen("shoutcast_show") == "live"


def test_a_junk_profile_cannot_poison_the_values_in_force(tmp_path) -> None:
    import json as _json

    from quill.core.radio import (
        history,  # noqa: F401
        history_store,
    )

    (tmp_path / history_store._FILE_NAME).write_text(
        _json.dumps({"source_options": {"shoutcast_show": 5, "nonsense": "x"}}), encoding="utf-8"
    )

    record = history_store.load_history(tmp_path)

    assert record.source_options == {}
    assert source_options.chosen("shoutcast_show") == "all"


def test_the_menu_offers_options_only_where_a_source_declares_them() -> None:
    from quill.core.radio import row_actions
    from quill.core.radio.row_state import FolderState

    with_options = [
        action.id
        for action in row_actions.folder_actions(
            "radioparadise", FolderState(root_source=True, has_options=True)
        )
    ]
    without = [
        action.id for action in row_actions.folder_actions("tunein", FolderState(root_source=True))
    ]
    assert row_actions.SOURCE_OPTIONS in with_options
    assert row_actions.SOURCE_OPTIONS not in without
