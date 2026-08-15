"""Resume positions: portable identity, honest merging, no lost places.

Resume already worked on one machine. These tests are about the two words that
qualify: *one machine*. The old key was ``f"{path.resolve()}|{size}"``, so the
same audiobook on a second computer -- or the same computer after the file
moved -- had a different key and no remembered place.

The properties worth defending:

* identity comes from the **contents**, so it survives a move, a rename, and a
  different operating system's idea of a path;
* merging is **last-write-wins on the timestamp**, not "keep the larger
  position", because deliberately jumping back must not be undone by a sync;
* an upgrade never loses anybody's place.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.media.positions import (
    CONFLICT_GAP_MS,
    MIN_RESUME_MS,
    ListeningPosition,
    PositionStore,
    media_identity,
    merge_positions,
)


def _book(tmp_path: Path, name: str = "book.mp3", *, body: bytes = b"") -> Path:
    path = tmp_path / name
    path.write_bytes(body or (b"HEAD" + b"\x00" * 4096 + b"TAIL"))
    return path


def _stamp(offset_minutes: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(minutes=offset_minutes)).isoformat()


# -- portable identity -------------------------------------------------------


def test_the_same_file_in_a_different_folder_is_the_same_recording(tmp_path: Path) -> None:
    """The whole point: your place follows the audiobook, not its path."""
    here = _book(tmp_path / "a", "book.mp3") if (tmp_path / "a").mkdir() or True else None
    there = tmp_path / "b"
    there.mkdir()
    moved = there / "renamed-entirely.mp3"
    moved.write_bytes(here.read_bytes())

    assert media_identity(here) == media_identity(moved)


def test_two_different_recordings_are_different(tmp_path: Path) -> None:
    """Your place in one narrator's reading says nothing about another's."""
    one = _book(tmp_path, "one.mp3", body=b"HEAD-A" + b"\x00" * 4096 + b"TAIL-A")
    two = _book(tmp_path, "two.mp3", body=b"HEAD-B" + b"\x00" * 4096 + b"TAIL-B")

    assert media_identity(one) != media_identity(two)


def test_files_of_the_same_length_but_different_audio_differ(tmp_path: Path) -> None:
    """Size alone would collide across a large library."""
    one = _book(tmp_path, "one.mp3", body=b"A" * 8192)
    two = _book(tmp_path, "two.mp3", body=b"B" * 8192)

    assert one.stat().st_size == two.stat().st_size
    assert media_identity(one) != media_identity(two)


def test_the_identity_is_stable_across_calls(tmp_path: Path) -> None:
    book = _book(tmp_path)
    assert media_identity(book) == media_identity(book)


def test_a_large_file_is_identified_without_reading_all_of_it(tmp_path: Path) -> None:
    """128 KB of reads, not 500 MB -- otherwise opening a book would stall."""
    big = tmp_path / "big.m4b"
    big.write_bytes(b"S" + b"\x00" * (400 * 1024) + b"E")
    reads: list[int] = []

    real_open = Path.open

    def counting_open(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        handle = real_open(self, *args, **kwargs)
        real_read = handle.read

        def read(size: int = -1) -> bytes:
            reads.append(size)
            return real_read(size)

        handle.read = read  # type: ignore[method-assign]
        return handle

    Path.open = counting_open  # type: ignore[method-assign]
    try:
        assert media_identity(big)
    finally:
        Path.open = real_open  # type: ignore[method-assign]

    assert reads and all(size <= 64 * 1024 for size in reads)


def test_an_unreadable_file_yields_no_identity(tmp_path: Path) -> None:
    """No identity means no saved position, never an exception."""
    assert media_identity(tmp_path / "not-here.mp3") == ""


# -- remembering and resuming ------------------------------------------------


def test_a_position_round_trips(tmp_path: Path) -> None:
    book = _book(tmp_path)
    store = PositionStore(tmp_path)

    store.remember(book, 5 * 60 * 1000)

    assert store.position_for(book) == 5 * 60 * 1000


def test_a_position_survives_the_file_moving(tmp_path: Path) -> None:
    book = _book(tmp_path)
    store = PositionStore(tmp_path)
    store.remember(book, 90_000)

    elsewhere = tmp_path / "moved"
    elsewhere.mkdir()
    moved = elsewhere / "different-name.mp3"
    moved.write_bytes(book.read_bytes())
    book.unlink()

    assert store.position_for(moved) == 90_000


def test_an_unknown_file_starts_at_the_beginning(tmp_path: Path) -> None:
    assert PositionStore(tmp_path).position_for(_book(tmp_path)) == 0


def test_barely_started_is_not_worth_resuming(tmp_path: Path) -> None:
    """ "Three seconds in" is the start; offering to resume there is a prompt
    the listener has to dismiss for no benefit."""
    book = _book(tmp_path)
    store = PositionStore(tmp_path)

    store.remember(book, MIN_RESUME_MS - 1)

    assert store.position_for(book) == 0


def test_starting_over_clears_a_previous_position(tmp_path: Path) -> None:
    book = _book(tmp_path)
    store = PositionStore(tmp_path)
    store.remember(book, 600_000)

    store.remember(book, 1_000)

    assert store.position_for(book) == 0


def test_forget_drops_the_position(tmp_path: Path) -> None:
    book = _book(tmp_path)
    store = PositionStore(tmp_path)
    store.remember(book, 600_000)

    store.forget(book)

    assert store.position_for(book) == 0


def test_a_corrupt_store_reads_as_no_positions(tmp_path: Path) -> None:
    (tmp_path / "listening_positions.json").write_text("{not json", encoding="utf-8")
    assert PositionStore(tmp_path).position_for(_book(tmp_path)) == 0


def test_remembering_records_the_length_and_a_readable_label(tmp_path: Path) -> None:
    book = _book(tmp_path, "The Hobbit - 01.mp3")
    store = PositionStore(tmp_path)

    store.remember(book, 120_000, duration_ms=3_600_000)
    record = store.get_record(media_identity(book))

    assert record is not None
    assert record["duration_ms"] == 3_600_000
    assert record["label"] == "The Hobbit - 01.mp3"
    assert record["updated_at"]


# -- the upgrade path --------------------------------------------------------


def test_a_position_saved_by_an_older_version_is_not_lost(tmp_path: Path) -> None:
    """The one failure this module exists to prevent: an upgrade silently
    resetting everybody's place."""
    import json

    book = _book(tmp_path)
    legacy_key = f"{book.resolve()}|{book.stat().st_size}"
    (tmp_path / "listening_positions.json").write_text(
        json.dumps({legacy_key: 450_000}), encoding="utf-8"
    )

    assert PositionStore(tmp_path).position_for(book) == 450_000


def test_the_next_save_refiles_a_legacy_entry_portably(tmp_path: Path) -> None:
    import json

    book = _book(tmp_path)
    legacy_key = f"{book.resolve()}|{book.stat().st_size}"
    (tmp_path / "listening_positions.json").write_text(
        json.dumps({legacy_key: 450_000}), encoding="utf-8"
    )
    store = PositionStore(tmp_path)

    store.remember(book, 500_000)
    raw = json.loads((tmp_path / "listening_positions.json").read_text(encoding="utf-8"))

    assert legacy_key not in raw
    assert media_identity(book) in raw
    assert store.position_for(book) == 500_000


def test_the_long_standing_wrapper_still_works(tmp_path: Path) -> None:
    """speech/listening_positions.py is what the players actually call."""
    from quill.core.speech.listening_positions import load_position_ms, save_position_ms

    book = _book(tmp_path)
    save_position_ms(tmp_path, book, 300_000)

    assert load_position_ms(tmp_path, book) == 300_000


# -- merging across machines -------------------------------------------------


def _record(position_ms: int, when: str, media_id: str = "m1") -> dict:
    return ListeningPosition(
        media_id=media_id, position_ms=position_ms, updated_at=when, label="A Book"
    ).to_dict()


def test_the_most_recent_position_wins_not_the_furthest() -> None:
    """The decision this module turns on. Jump back twenty minutes to re-hear
    something, then open the book on your laptop: the furthest position is
    exactly the wrong answer."""
    older_but_further = _record(60 * 60 * 1000, _stamp(-10))
    newer_but_earlier = _record(40 * 60 * 1000, _stamp(0))

    merged, _conflicts = merge_positions(older_but_further, newer_but_earlier)

    assert merged["position_ms"] == 40 * 60 * 1000


def test_a_local_position_wins_when_it_is_the_newer_one() -> None:
    merged, _ = merge_positions(_record(900_000, _stamp(0)), _record(100_000, _stamp(-30)))
    assert merged["position_ms"] == 900_000


def test_a_new_entity_is_taken_as_is() -> None:
    remote = _record(120_000, _stamp())
    merged, conflicts = merge_positions(None, remote)
    assert merged == remote
    assert conflicts == []


def test_a_meaningful_disagreement_is_reported() -> None:
    """Two devices an hour apart is worth telling somebody about."""
    _merged, conflicts = merge_positions(
        _record(10 * 60 * 1000, _stamp(-5)), _record(70 * 60 * 1000, _stamp(0))
    )

    assert len(conflicts) == 1
    assert conflicts[0].field == "position_ms"
    assert "most recent" in conflicts[0].message


def test_a_trivial_disagreement_is_not_worth_mentioning() -> None:
    """A few seconds apart is the same place; reporting it is noise."""
    _merged, conflicts = merge_positions(
        _record(600_000, _stamp(-5)), _record(600_000 + CONFLICT_GAP_MS - 1, _stamp(0))
    )
    assert conflicts == []


def test_a_conflict_speaks_its_positions_as_words() -> None:
    """A screen reader reads this aloud; "70:00" is not a duration."""
    _merged, conflicts = merge_positions(
        _record(10 * 60 * 1000, _stamp(-5)), _record(70 * 60 * 1000, _stamp(0))
    )
    assert "minute" in conflicts[0].local
    assert ":" not in conflicts[0].remote


def test_a_missing_timestamp_resolves_to_the_remote() -> None:
    """Matches default_merge, so incomplete data behaves predictably."""
    merged, _ = merge_positions(_record(500_000, ""), _record(100_000, ""))
    assert merged["position_ms"] == 100_000


# -- the QuillSync RecordStore contract --------------------------------------


def test_the_store_satisfies_the_record_store_protocol(tmp_path: Path) -> None:
    from quill.core.sync.protocol import RecordStore

    assert isinstance(PositionStore(tmp_path), RecordStore)


def test_records_put_by_sync_are_immediately_what_resumes(tmp_path: Path) -> None:
    """The point of one file rather than two: a position that arrived from
    another machine is the position the player uses."""
    book = _book(tmp_path)
    store = PositionStore(tmp_path)

    store.put_record(media_identity(book), _record(777_000, _stamp(), media_identity(book)))

    assert store.position_for(book) == 777_000


def test_delete_record_removes_it(tmp_path: Path) -> None:
    book = _book(tmp_path)
    store = PositionStore(tmp_path)
    store.remember(book, 300_000)

    store.delete_record(media_identity(book))

    assert store.get_record(media_identity(book)) is None


def test_entity_ids_lists_what_there_is_to_push(tmp_path: Path) -> None:
    store = PositionStore(tmp_path)
    one = _book(tmp_path, "one.mp3", body=b"ONE" + b"\x00" * 4096)
    two = _book(tmp_path, "two.mp3", body=b"TWO" + b"\x00" * 4096)
    store.remember(one, 100_000)
    store.remember(two, 200_000)

    assert sorted(store.entity_ids()) == sorted([media_identity(one), media_identity(two)])


@pytest.mark.parametrize("bad", [None, "text", 42, {"no_media_id": 1}])
def test_a_junk_record_is_ignored_rather_than_crashing(bad: object) -> None:
    assert ListeningPosition.from_dict(bad) is None
