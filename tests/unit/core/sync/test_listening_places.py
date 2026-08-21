"""The plain file another app reads: identity, one writer, last-write-wins.

Cases follow the ``listening-places/1`` spec sections. The ones that matter most
are the three that rule out a failure mode rather than implementing a feature:
identity is content-derived so two platforms agree, one device never writes
another's file, and an unchanged state does not re-upload.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.sync import listening_places as lp


def _record(entity_id: str, position_ms: int, updated_at: str, **kwargs: object) -> lp.PlaceRecord:
    return lp.PlaceRecord(id=entity_id, position_ms=position_ms, updated_at=updated_at, **kwargs)


# -- identity (6.3) ----------------------------------------------------------


def test_an_episode_is_keyed_on_its_guid_alone() -> None:
    """Two apps disagree about a feed URL far more often than about a GUID."""
    through_feedburner = lp.episode_id("tag:example.com,2026:ep214")
    through_the_host = lp.episode_id("tag:example.com,2026:ep214")
    assert through_feedburner == through_the_host
    assert through_feedburner.startswith("episode:")
    assert len(through_feedburner) == len("episode:") + 16


def test_a_feed_with_no_guid_falls_back_to_its_enclosure() -> None:
    assert lp.episode_id("", "https://cdn.example.com/ep214.mp3").startswith("episode:")
    assert lp.episode_id("", "") == ""


def test_the_id_does_not_spell_out_what_somebody_listens_to() -> None:
    """A shared Dropbox folder must not list every podcast in readable form."""
    assert "example.com" not in lp.episode_id("https://example.com/embarrassing-show/ep1")


def test_a_local_file_gets_the_same_id_on_any_platform(tmp_path: Path) -> None:
    audio = tmp_path / "book.mp3"
    audio.write_bytes(b"a" * 5000)
    first = lp.file_id(audio)
    moved = tmp_path / "somewhere-else" / "renamed.mp3"
    moved.parent.mkdir()
    moved.write_bytes(b"a" * 5000)
    assert first == lp.file_id(moved) != "file:"


def test_a_missing_file_has_no_identity(tmp_path: Path) -> None:
    assert lp.file_id(tmp_path / "gone.mp3") == ""


def test_the_stream_namespace_is_reserved() -> None:
    assert lp.stream_id("https://Stream.example/live").startswith("stream:")
    assert lp.stream_id("https://stream.example/LIVE") != lp.stream_id("https://stream.example/x")


# -- the file (6.1, 6.2) -----------------------------------------------------


def test_a_device_writes_its_own_file_and_a_readme(tmp_path: Path) -> None:
    written = lp.write_device_file(
        tmp_path,
        device_id="1f4c8a2e",
        device_label="Studio PC",
        app="quill-cast/1.1.0",
        records=[_record("episode:aaaa", 2_412_000, "2026-08-20T13:58:02Z", label="Ep 214")],
    )
    assert written is True
    target = tmp_path / lp.FOLDER_NAME / "devices" / "1f4c8a2e.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["format"] == lp.FORMAT_ID
    assert payload["device"] == "1f4c8a2e"
    assert payload["records"][0]["position_ms"] == 2_412_000
    assert payload["records"][0]["kind"] == "episode"
    assert (tmp_path / lp.FOLDER_NAME / "README.txt").is_file()


def test_an_unchanged_state_is_not_written_again(tmp_path: Path) -> None:
    """A machine left open all day must not re-upload an identical file (6.4)."""
    records = [_record("episode:aaaa", 100_000, "2026-08-20T13:58:02Z")]
    assert lp.write_device_file(
        tmp_path, device_id="1f4c8a2e", device_label="PC", app="a", records=records
    )
    assert not lp.write_device_file(
        tmp_path, device_id="1f4c8a2e", device_label="PC", app="a", records=records
    )
    moved = [_record("episode:aaaa", 200_000, "2026-08-20T14:10:00Z")]
    assert lp.write_device_file(
        tmp_path, device_id="1f4c8a2e", device_label="PC", app="a", records=moved
    )


def test_labels_can_be_left_out(tmp_path: Path) -> None:
    lp.write_device_file(
        tmp_path,
        device_id="1f4c8a2e",
        device_label="PC",
        app="a",
        records=[_record("episode:aaaa", 1, "2026-08-20T13:58:02Z", label="A private show")],
        include_labels=False,
    )
    text = (tmp_path / lp.FOLDER_NAME / "devices" / "1f4c8a2e.json").read_text(encoding="utf-8")
    assert "A private show" not in text


def test_a_device_never_reads_its_own_file(tmp_path: Path) -> None:
    """One writer per file is what stops a cloud drive making a conflicted copy."""
    lp.write_device_file(
        tmp_path,
        device_id="mine0001",
        device_label="Mine",
        app="a",
        records=[_record("episode:aaaa", 1, "2026-08-20T13:58:02Z")],
    )
    lp.write_device_file(
        tmp_path,
        device_id="their001",
        device_label="Theirs",
        app="b",
        records=[_record("episode:bbbb", 2, "2026-08-20T13:59:02Z")],
    )
    others = lp.read_other_devices(tmp_path, "mine0001")
    assert [device.device for device in others] == ["their001"]


def test_an_unreadable_file_costs_only_itself(tmp_path: Path) -> None:
    folder = lp.devices_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / "broken00.json").write_text("{ not json", encoding="utf-8")
    (folder / "future00.json").write_text(
        json.dumps({"format": "listening-places/9", "records": []}), encoding="utf-8"
    )
    (folder / "good0001.json").write_text(
        json.dumps({
            "format": lp.FORMAT_ID,
            "device": "good0001",
            "records": [
                {"id": "episode:aaaa", "position_ms": 5, "updated_at": "2026-01-01T00:00:00Z"}
            ],
        }),
        encoding="utf-8",
    )
    others = lp.read_other_devices(tmp_path, "mine0001")
    assert [device.device for device in others] == ["good0001"]


def test_a_folder_that_is_not_there_reads_as_nothing(tmp_path: Path) -> None:
    assert lp.read_other_devices(tmp_path / "gone", "mine0001") == []


def test_a_tombstone_carries_nothing_else() -> None:
    row = lp.PlaceRecord(id="episode:aaaa", deleted=True, updated_at="2026-01-01T00:00:00Z")
    assert row.to_dict() == {
        "id": "episode:aaaa",
        "deleted": True,
        "updated_at": "2026-01-01T00:00:00Z",
    }


# -- merging (6.4, 6.5) ------------------------------------------------------


def test_last_write_wins_not_furthest_position() -> None:
    """Jumping back twenty minutes on purpose must not be undone by a merge."""
    local = {"episode:aaaa": _record("episode:aaaa", 3_000_000, "2026-08-20T15:30:00Z")}
    remote = {"episode:aaaa": _record("episode:aaaa", 600_000, "2026-08-20T14:00:00Z")}
    merged, _ = lp.merge_records(local, remote)
    assert merged["episode:aaaa"].position_ms == 3_000_000


def test_the_newer_record_is_applied() -> None:
    local = {"episode:aaaa": _record("episode:aaaa", 2_412_000, "2026-08-20T13:58:02Z")}
    remote = {"episode:aaaa": _record("episode:aaaa", 3_120_000, "2026-08-20T15:30:44Z")}
    merged, disagreements = lp.merge_records(local, remote)
    assert merged["episode:aaaa"].position_ms == 3_120_000
    assert len(disagreements) == 1
    said = disagreements[0].spoken()
    assert "40 minutes" in said and "52 minutes" in said


def test_a_small_difference_is_not_worth_mentioning() -> None:
    local = {"episode:aaaa": _record("episode:aaaa", 600_000, "2026-08-20T13:00:00Z")}
    remote = {"episode:aaaa": _record("episode:aaaa", 608_000, "2026-08-20T14:00:00Z")}
    _, disagreements = lp.merge_records(local, remote)
    assert disagreements == []


def test_something_only_the_other_device_knows_arrives() -> None:
    merged, _ = lp.merge_records(
        {}, {"episode:bbbb": _record("episode:bbbb", 5, "2026-08-20T14:00:00Z")}
    )
    assert "episode:bbbb" in merged


def test_the_newest_across_three_devices_wins() -> None:
    files = [
        lp.DeviceFile(device="a", records=[_record("episode:x", 1, "2026-08-01T00:00:00Z")]),
        lp.DeviceFile(device="b", records=[_record("episode:x", 2, "2026-08-03T00:00:00Z")]),
        lp.DeviceFile(device="c", records=[_record("episode:x", 3, "2026-08-02T00:00:00Z")]),
    ]
    assert lp.remote_view(files)["episode:x"].position_ms == 2


def test_a_slow_clock_cannot_lose_to_its_own_stale_data() -> None:
    record = _record("episode:x", 900_000, "2026-08-20T12:00:00Z")
    guarded = lp.guard_clock_skew(record, "2026-08-20T14:00:00Z")
    assert guarded.updated_at == "2026-08-20T14:00:01Z"
    assert guarded.position_ms == 900_000
    # A record that is genuinely newer is left alone.
    fresh = _record("episode:x", 1, "2026-08-20T15:00:00Z")
    assert lp.guard_clock_skew(fresh, "2026-08-20T14:00:00Z") is fresh


def test_device_ids_are_random_and_not_a_name() -> None:
    first, second = lp.new_device_id(), lp.new_device_id()
    assert first != second
    assert lp.is_device_id(first)
    assert not lp.is_device_id("Jeffs-iPhone")
