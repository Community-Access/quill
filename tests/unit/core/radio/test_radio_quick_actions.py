"""Quick Actions in Quill Radio: the catalogue, and the order it produces.

The load-bearing case is the first one. A Quick Actions entry whose id no row
menu ever builds is an action a listener can put first and then never reach --
a preference that silently does nothing. So the catalogue is checked against
``row_actions``' own id constants rather than trusted.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.quick_actions import DIRECT_KEY_COUNT, QuickActionOrders
from quill.core.radio import quick_actions as qa
from quill.core.radio import row_actions


def _row_action_ids() -> set[str]:
    """Every id the row menus can build, from the module that builds them."""
    ids: set[str] = set()
    for name in dir(row_actions):
        if name.isupper():
            value = getattr(row_actions, name)
            if isinstance(value, str) and value:
                ids.add(value)
    from quill.core.radio.cast_handoff import CAST_HANDOFFS

    ids.update(action_id for action_id, _label in CAST_HANDOFFS)
    return ids


def test_every_station_and_node_action_is_one_a_row_can_actually_build() -> None:
    known = _row_action_ids()
    offered = {action.id for action in (*qa.STATION_ACTIONS, *qa.BROWSE_NODE_ACTIONS)}
    unreachable = sorted(offered - known)
    assert not unreachable, (
        f"Quick Actions offers ids no row menu builds: {unreachable}. "
        "A listener could put one first and never reach it."
    )


def test_recording_actions_are_their_own_surface() -> None:
    """The Recordings window has buttons, not row_actions ids -- and says so."""
    assert all(action.id.startswith("recording.") for action in qa.RECORDING_ACTIONS)


def test_every_action_has_words_a_listener_can_act_on() -> None:
    for context, actions in qa.CONTEXTS.items():
        for action in actions:
            assert action.label, f"{context}/{action.id} has no label"
            assert action.description.endswith("."), f"{context}/{action.id}"


def test_the_contexts_and_their_labels_agree() -> None:
    assert {cid for cid, _label in qa.CONTEXT_LABELS} == set(qa.CONTEXTS)


def test_the_shipped_station_default_is_still_play() -> None:
    """An upgrade must not move somebody's default action out from under them."""
    orders = QuickActionOrders.defaults(qa.CONTEXTS)
    assert orders.default_action("station") == row_actions.PLAY


def test_nine_direct_keys_in_both_apps() -> None:
    from quill.core.podcasts.quick_actions import DIRECT_KEY_COUNT as cast_count

    assert DIRECT_KEY_COUNT == cast_count == 9


# -- ordering ----------------------------------------------------------------


class _Row:
    def __init__(self, action_id: str) -> None:
        self.id = action_id
        self.label = action_id


def test_the_preference_reorders_what_a_row_offers() -> None:
    orders = QuickActionOrders.defaults(qa.CONTEXTS)
    orders.set_order("station", ["details", "play"])
    rows = [_Row("play"), _Row("copy.link"), _Row("details")]
    assert [row.id for row in qa.apply_order(rows, orders, "station")][:2] == [
        "details",
        "play",
    ]


def test_the_preference_cannot_add_an_action_to_a_row() -> None:
    """A live stream offers no Download however high somebody ranks it."""
    orders = QuickActionOrders.defaults(qa.CONTEXTS)
    orders.set_order("station", ["download", "play"])
    rows = [_Row("play"), _Row("details")]
    assert [row.id for row in qa.apply_order(rows, orders, "station")] == ["play", "details"]


def test_an_action_with_no_preference_entry_stays_reachable() -> None:
    orders = QuickActionOrders.defaults(qa.CONTEXTS)
    rows = [_Row("play"), _Row("something.new"), _Row("details")]
    ordered = [row.id for row in qa.apply_order(rows, orders, "station")]
    assert "something.new" in ordered
    assert ordered[-1] == "something.new"


def test_no_preference_leaves_the_row_exactly_as_built() -> None:
    rows = [_Row("details"), _Row("play")]
    assert qa.apply_order(rows, None, "station") == rows


# -- the store ---------------------------------------------------------------


def test_the_order_round_trips_through_disk(tmp_path: Path) -> None:
    orders = qa.load_radio_quick_actions(tmp_path)
    orders.set_order("station", ["details", "play"])
    qa.save_radio_quick_actions(tmp_path, orders)

    restored = qa.load_radio_quick_actions(tmp_path)
    assert restored.order("station")[:2] == ["details", "play"]
    assert restored.default_action("station") == "details"


def test_radio_and_cast_keep_separate_stores(tmp_path: Path) -> None:
    """One file would mean each app's repair pass discarding the other's list."""
    from quill.core.podcasts.quick_actions import _FILE_NAME as cast_file

    assert qa.FILE_NAME != cast_file


def test_a_missing_file_reads_as_the_shipped_order(tmp_path: Path) -> None:
    orders = qa.load_radio_quick_actions(tmp_path)
    assert orders.order("station") == [action.id for action in qa.STATION_ACTIONS]


def test_an_order_naming_an_action_this_build_lost_is_repaired(tmp_path: Path) -> None:
    (tmp_path / qa.FILE_NAME).write_text(
        '{"station": ["station.teleport", "details"]}', encoding="utf-8"
    )
    orders = qa.load_radio_quick_actions(tmp_path)
    order = orders.order("station")
    assert "station.teleport" not in order
    assert order[0] == "details"
    # And everything this build does have is still in the list.
    assert set(order) == {action.id for action in qa.STATION_ACTIONS}
