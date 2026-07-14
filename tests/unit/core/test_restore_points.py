"""Restore points: record, list, read, dedup, retention, and corruption safety."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core import restore_points as rp


@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))


def _doc(tmp_path: Path) -> Path:
    doc = tmp_path / "story.md"
    doc.write_text("x", encoding="utf-8")
    return doc


def test_record_and_list_round_trip(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    first = rp.record_restore_point(doc, "draft one")
    second = rp.record_restore_point(doc, "draft two, longer")
    assert first is not None and second is not None

    points = rp.list_restore_points(doc)
    assert [p.content_hash for p in points] == [second.content_hash, first.content_hash]
    assert points[0].word_count == 3
    assert rp.read_restore_point(doc, first.content_hash) == "draft one"
    assert rp.read_restore_point(doc, second.content_hash) == "draft two, longer"


def test_unchanged_content_is_not_recorded_twice(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    assert rp.record_restore_point(doc, "same text") is not None
    assert rp.record_restore_point(doc, "same text") is None
    assert len(rp.list_restore_points(doc)) == 1


def test_oversized_text_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rp, "MAX_TEXT_BYTES", 10)
    doc = _doc(tmp_path)
    assert rp.record_restore_point(doc, "far more than ten bytes") is None
    assert rp.list_restore_points(doc) == []


def test_missing_blob_reads_none_not_crash(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    point = rp.record_restore_point(doc, "text")
    assert point is not None
    blob = rp._doc_dir(doc) / "blobs" / f"{point.content_hash}.txt"
    blob.unlink()
    assert rp.read_restore_point(doc, point.content_hash) is None


def test_hash_argument_cannot_traverse_paths(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    assert rp.read_restore_point(doc, "../../secrets") is None
    assert rp.read_restore_point(doc, "") is None


def test_corrupt_index_degrades_to_empty(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    rp.record_restore_point(doc, "good")
    (rp._doc_dir(doc) / "index.json").write_text("{ not json", encoding="utf-8")
    assert rp.list_restore_points(doc) == []
    # And recording still works afterwards (fresh index).
    assert rp.record_restore_point(doc, "after corruption") is not None


def test_prune_keeps_minimum_and_recent(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    for i in range(8):
        assert rp.record_restore_point(doc, f"version {i}") is not None
    # All eight are recent (< 7 days): nothing is pruned.
    assert rp.prune_restore_points(doc, max_total_mb=200) == 0
    assert len(rp.list_restore_points(doc)) == 8


def test_prune_thins_old_versions_to_daily(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    # Fabricate 3 versions on one day two weeks ago, plus 6 recent ones.
    old_day = (datetime.now(UTC) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    for i in range(3):
        point = rp.record_restore_point(doc, f"old {i}")
        assert point is not None
    index_path = rp._doc_dir(doc) / "index.json"
    import json

    index = json.loads(index_path.read_text(encoding="utf-8"))
    for entry in index["entries"]:
        entry["saved_at"] = old_day
    index_path.write_text(json.dumps(index), encoding="utf-8")
    for i in range(6):
        assert rp.record_restore_point(doc, f"new {i}") is not None

    removed = rp.prune_restore_points(doc, max_total_mb=200)
    # The three same-day old versions thin to one; the six recent survive.
    assert removed == 2
    assert len(rp.list_restore_points(doc)) == 7


def test_prune_size_cap_never_removes_newest_five(tmp_path: Path) -> None:
    doc = _doc(tmp_path)
    big = "words " * 5000  # ~30 KB each
    for i in range(10):
        assert rp.record_restore_point(doc, big + str(i)) is not None
    # A zero-MB cap still keeps the protected minimum.
    rp.prune_restore_points(doc, max_total_mb=0)
    survivors = rp.list_restore_points(doc)
    assert len(survivors) == 5
    # Their blobs are readable and the pruned blobs are gone from disk.
    for point in survivors:
        assert rp.read_restore_point(doc, point.content_hash) is not None
    blob_dir = rp._doc_dir(doc) / "blobs"
    assert len(list(blob_dir.glob("*.txt"))) == 5
