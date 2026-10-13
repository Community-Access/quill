"""The shared file and every operation on it: by key, never by position."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from quill.core.lineups import ops
from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.model import HELD_ADDED, HELD_KEPT, LineupBook, Row
from quill.core.lineups.refs import KIND_STATION, ItemRef
from quill.core.lineups.rules import Keep, Rule
from quill.core.lineups.store import STALE_LOCK_SECONDS, LineupStore, LineupStoreError


def item(key: str) -> ItemFacts:
    return ItemFacts(ref=ItemRef(KIND_STATION, key), name=key)


def ref(key: str) -> ItemRef:
    return ItemRef(KIND_STATION, key)


def keys(book: LineupBook, lineup_id: str) -> list[str]:
    lineup = book.find(lineup_id)
    assert lineup is not None
    return [row.ref.key for row in lineup.rows]


@pytest.fixture
def store(tmp_path: Path) -> LineupStore:
    return LineupStore(tmp_path)


@pytest.fixture
def morning(store: LineupStore) -> str:
    _book, outcome = store.update(ops.create_lineup("Morning"))
    store.update(ops.add_items(outcome.lineup_id, [item(k) for k in "abcd"]))
    return outcome.lineup_id


# -- the file -------------------------------------------------------------------------


def test_a_missing_file_is_an_empty_book_and_round_trips(store: LineupStore, morning: str) -> None:
    assert LineupStore(store.path.parent).load().find(morning) is not None
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1 and raw["lineups"][0]["name"] == "Morning"
    assert not store.lock_path.exists()  # released after every write


def test_two_apps_writing_at_once_lose_nothing(tmp_path: Path) -> None:
    """Two stores (Radio and Cast) adding to one Lineup from two threads."""
    first = LineupStore(tmp_path)
    _book, outcome = first.update(ops.create_lineup("Shared"))
    lineup_id = outcome.lineup_id

    def writer(prefix: str) -> None:
        mine = LineupStore(tmp_path)
        for n in range(15):
            mine.update(ops.add_items(lineup_id, [item(f"{prefix}{n}")]))

    threads = [threading.Thread(target=writer, args=(p,)) for p in ("radio-", "cast-")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    found = set(keys(LineupStore(tmp_path).load(), lineup_id))
    assert found == {f"{p}{n}" for p in ("radio-", "cast-") for n in range(15)}


def test_an_abandoned_lock_does_not_wedge_the_app(store: LineupStore, morning: str) -> None:
    store.lock_path.write_text("12345", encoding="utf-8")
    old = time.time() - STALE_LOCK_SECONDS - 5
    os.utime(store.lock_path, (old, old))
    store.update(ops.rename_lineup(morning, "Breakfast"))
    assert store.load().find(morning).name == "Breakfast"  # type: ignore[union-attr]


def test_a_live_lock_held_too_long_is_a_coded_error_and_changes_nothing(
    store: LineupStore, morning: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.lineups import store as store_module

    monkeypatch.setattr(store_module, "LOCK_WAIT_SECONDS", 0.05)
    store.lock_path.write_text("other app", encoding="utf-8")
    with pytest.raises(LineupStoreError) as raised:
        store.update(ops.rename_lineup(morning, "Never"))
    assert raised.value.code == "QUILL-RADIO-LINEUP-STORE"
    store.lock_path.unlink()
    assert store.load().find(morning).name == "Morning"  # type: ignore[union-attr]


def test_a_file_from_a_newer_version_is_read_but_never_rewritten(store: LineupStore) -> None:
    store.path.write_text(json.dumps({"schema_version": 99, "lineups": []}), encoding="utf-8")
    before = store.path.read_text(encoding="utf-8")
    store.load()
    with pytest.raises(LineupStoreError):
        store.update(ops.create_lineup("x"))
    assert store.path.read_text(encoding="utf-8") == before


def test_a_corrupt_file_is_quarantined_not_overwritten(
    store: LineupStore, quill_data_dir: Path
) -> None:
    store.path.write_text("{not json", encoding="utf-8")
    assert store.load().lineups == ()
    assert store.path.read_text(encoding="utf-8") == "{not json"  # never overwritten on read


# -- operations by key -------------------------------------------------------------------


def test_names_are_unique_ignoring_case(store: LineupStore, morning: str) -> None:
    book, outcome = store.update(ops.create_lineup("morning"))
    assert book.find(outcome.lineup_id).name == "morning (2)"  # type: ignore[union-attr]


def test_moves_name_an_anchor_and_go_stale_when_it_has_left(
    store: LineupStore, morning: str
) -> None:
    book, outcome = store.update(ops.move_rows(morning, [ref("d")], after=ref("a")))
    assert keys(book, morning) == ["a", "d", "b", "c"] and outcome.select == (ref("d"),)
    assert book.find(morning).row_for(ref("d")).moved  # type: ignore[union-attr]
    book, _ = store.update(ops.move_rows(morning, [ref("c")], to_top=True))
    assert keys(book, morning) == ["c", "a", "d", "b"]
    store.update(ops.remove_rows(morning, [ref("b")]))
    book, outcome = store.update(ops.move_rows(morning, [ref("a")], after=ref("b")))
    assert outcome.stale and keys(book, morning) == ["c", "a", "d"]


def test_remove_goes_to_removed_items_and_selects_the_row_that_took_its_place(
    store: LineupStore, morning: str
) -> None:
    book, outcome = store.update(ops.remove_rows(morning, [ref("b")]))
    assert keys(book, morning) == ["a", "c", "d"] and outcome.select == (ref("c"),)
    assert [r.ref for r in book.find(morning).removed] == [ref("b")]  # type: ignore[union-attr]
    book, _ = store.update(ops.restore_removed(morning, [ref("b")]))
    lineup = book.find(morning)
    assert lineup is not None and lineup.row_for(ref("b")).held == HELD_KEPT  # type: ignore[union-attr]
    assert not lineup.removed


def test_adding_a_removed_item_by_hand_forgets_the_removal(
    store: LineupStore, morning: str
) -> None:
    store.update(ops.remove_rows(morning, [ref("b")]))
    book, _ = store.update(ops.add_items(morning, [item("b")]))
    assert not book.find(morning).removed  # type: ignore[union-attr]


def test_keep_toggles_and_a_hand_added_row_stays_added(store: LineupStore, morning: str) -> None:
    book, _ = store.update(ops.set_kept(morning, [ref("a")], True))
    assert book.find(morning).row_for(ref("a")).held == HELD_KEPT  # type: ignore[union-attr]
    book, _ = store.update(ops.set_kept(morning, [ref("a")], False))
    assert book.find(morning).row_for(ref("a")).held == HELD_ADDED  # type: ignore[union-attr]


def test_delete_then_restore_puts_the_lineup_back_where_it_was(
    store: LineupStore, morning: str
) -> None:
    store.update(ops.create_lineup("Evening"))
    _book, outcome = store.update(ops.delete_lineup(morning))
    assert outcome.deleted is not None and outcome.deleted_index == 0
    book, _ = store.update(ops.restore_lineup(outcome.deleted, outcome.deleted_index))
    assert [lineup.name for lineup in book.lineups] == ["Morning", "Evening"]


def test_duplicate_copies_rules_with_new_ids(store: LineupStore, morning: str) -> None:
    rule = Rule(id="r1", kind=KIND_STATION, keep=Keep())
    store.update(ops.set_rules(morning, [rule]))
    book, outcome = store.update(ops.duplicate_lineup(morning))
    copy = book.find(outcome.lineup_id)
    assert copy is not None and copy.name == "Morning (copy)"
    assert copy.rules[0].id != "r1" and keys(book, copy.id) == keys(book, morning)


def test_deleting_a_rule_keeps_or_lets_go_its_items(store: LineupStore, morning: str) -> None:
    def with_claim(book: LineupBook) -> tuple[LineupBook, ops.Outcome]:
        lineup = book.find(morning)
        assert lineup is not None
        claimed = Row(ref=ref("z"), name="z", claims={"r1": 1.0})
        rule = Rule(id="r1", kind=KIND_STATION)
        return book.replace_lineup(
            type(lineup)(**{**_as_dict(lineup), "rules": (rule,), "rows": (*lineup.rows, claimed)})
        ), ops.Outcome()

    store.update(with_claim)
    assert [r.ref.key for r in ops.items_of_rule(store.load().find(morning), "r1")] == ["z"]  # type: ignore[arg-type]
    book, _ = store.update(ops.set_rules(morning, [], keep_items_of_deleted=False))
    lineup = book.find(morning)
    assert lineup is not None and "z" not in keys(book, morning)
    assert lineup.recently_left[0].reason == "rule 1 was deleted"
    store.update(with_claim)
    book, _ = store.update(ops.set_rules(morning, [], keep_items_of_deleted=True))
    assert book.find(morning).row_for(ref("z")).held == HELD_KEPT  # type: ignore[union-attr]


def test_an_operation_on_a_lineup_the_other_app_deleted_is_stale(
    store: LineupStore, morning: str
) -> None:
    store.update(ops.delete_lineup(morning))
    _book, outcome = store.update(ops.add_items(morning, [item("x")]))
    assert outcome.stale


def _as_dict(lineup: object) -> dict[str, object]:
    return {name: getattr(lineup, name) for name in type(lineup).__dataclass_fields__}  # type: ignore[attr-defined]
