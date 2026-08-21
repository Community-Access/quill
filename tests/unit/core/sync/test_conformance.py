"""Conformance: two device files in, one merged result out.

The usual fate of an informal interchange format is that two implementations
drift until somebody's listening position is wrong, and that is the kind of bug
that takes months to attribute. A fixture pair in both repositories means a
change that breaks the other app fails a test rather than a user.

The fixtures under ``fixtures/`` are plain JSON on purpose: another
implementation, in another language, can read exactly these files and check
exactly this result without depending on anything QUILL owns. Adding a case is
adding a JSON pair -- please do, in either repository.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.sync.listening_places import DeviceFile, merge_records, remote_view

FIXTURES = Path(__file__).parent / "fixtures"


def _device(name: str) -> DeviceFile:
    parsed = DeviceFile.from_dict(json.loads((FIXTURES / name).read_text(encoding="utf-8")))
    assert parsed is not None, f"{name} did not parse as a {DeviceFile.__name__}"
    return parsed


def _expected() -> dict:
    return json.loads((FIXTURES / "expected-merge.json").read_text(encoding="utf-8"))


def test_the_fixture_merge_is_what_the_spec_says() -> None:
    desktop = _device("device-desktop.json")
    phone = _device("device-phone.json")

    local = {record.id: record for record in desktop.records}
    merged, disagreements = merge_records(local, remote_view([phone]))

    expected = _expected()
    assert set(merged) == set(expected["merged"])
    for entity_id, row in expected["merged"].items():
        got = merged[entity_id]
        assert got.position_ms == row["position_ms"], entity_id
        assert got.played == row["played"], entity_id
        assert got.updated_at == row["updated_at"], entity_id


def test_the_fixture_disagreements_are_what_the_spec_says() -> None:
    desktop = _device("device-desktop.json")
    phone = _device("device-phone.json")
    local = {record.id: record for record in desktop.records}
    _, disagreements = merge_records(local, remote_view([phone]))

    expected = _expected()["disagreements"]
    assert len(disagreements) == len(expected)
    for got, row in zip(disagreements, expected, strict=True):
        assert got.id == row["id"]
        assert got.local_ms == row["local_ms"]
        assert got.remote_ms == row["remote_ms"]


def test_a_finished_episode_beats_a_stale_position() -> None:
    """played true with position 0 is a real state, not an empty one."""
    expected = _expected()["merged"]
    finished = [row for row in expected.values() if row["played"]]
    assert finished, "the fixture should contain a finished episode"
    assert all(row["position_ms"] == 0 for row in finished)


def test_a_file_record_travels_alongside_the_episodes() -> None:
    """One folder, one mailbox: podcast places and book places in one file."""
    assert any(key.startswith("file:") for key in _expected()["merged"])
