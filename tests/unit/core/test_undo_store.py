from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.undo_store import clear_undo_history, load_undo_history, save_undo_history


def test_save_and_load_undo_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    target.write_text("x", encoding="utf-8")
    save_undo_history(target, ["a", "b", "c"])
    assert load_undo_history(target) == ["a", "b", "c"]


def test_save_undo_history_honors_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    target.write_text("x", encoding="utf-8")
    save_undo_history(target, ["1", "2", "3", "4"], limit=2)
    assert load_undo_history(target) == ["3", "4"]


def test_clear_undo_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    target.write_text("x", encoding="utf-8")
    save_undo_history(target, ["one"])
    clear_undo_history(target)
    assert load_undo_history(target) == []


def test_load_missing_history_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "never-saved.md"
    assert load_undo_history(target) == []


def test_clear_missing_history_is_a_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "never-saved.md"
    # Clearing a history that was never written must not raise.
    clear_undo_history(target)
    assert load_undo_history(target) == []


def test_load_filters_non_string_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    # Persistence accepts only string snapshots; corrupt entries are dropped.
    save_undo_history(target, ["good", "also-good"])
    raw_path = next((Path(tmp_path) / "undo").glob("*.json"))
    raw_path.write_text('["keep", 5, null, "stay", true]', encoding="utf-8")
    assert load_undo_history(target) == ["keep", "stay"]


def test_load_non_list_payload_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    save_undo_history(target, ["seed"])
    raw_path = next((Path(tmp_path) / "undo").glob("*.json"))
    raw_path.write_text('{"not": "a list"}', encoding="utf-8")
    assert load_undo_history(target) == []


def test_save_returns_bounded_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    returned = save_undo_history(target, ["1", "2", "3", "4", "5"], limit=3)
    assert returned == ["3", "4", "5"]
    assert load_undo_history(target) == ["3", "4", "5"]


def test_save_limit_below_one_keeps_a_single_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    # A non-positive limit is coerced to keep the most recent entry, never zero.
    save_undo_history(target, ["old", "new"], limit=0)
    assert load_undo_history(target) == ["new"]


def test_history_survives_repeated_save_load_cycles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    # Simulate undo snapshots accumulating across edits, then a reload.
    save_undo_history(target, ["v1"])
    save_undo_history(target, ["v1", "v2"])
    save_undo_history(target, ["v1", "v2", "v3"])
    assert load_undo_history(target) == ["v1", "v2", "v3"]


def test_histories_for_distinct_paths_do_not_collide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    save_undo_history(first, ["a", "b"])
    save_undo_history(second, ["x", "y"])
    assert load_undo_history(first) == ["a", "b"]
    assert load_undo_history(second) == ["x", "y"]


# -- the size budget (x.md item 12) ------------------------------------------
#
# The count limit was never a bound on anything that matters. A hundred
# snapshots of a shopping list is nothing; a hundred snapshots of a 1 MB
# manuscript is 100 MB, held in memory *and* rewritten in full every few
# seconds while you type, because the whole history is one JSON file. The cost
# scaled with the document, which is exactly backwards.
#
# (x.md proposed a length-then-hash equality check instead. Measured, that is a
# pessimization: Python's string `==` already compares length first and returns
# in ~0 us when they differ, which is what a keystroke produces, while sha256 of
# a 1 MB document costs ~243 us against memcmp's ~34 us. The equality check was
# never the expensive part; the retained copies were.)


def test_history_is_bounded_by_total_size_not_only_count() -> None:
    from quill.core.undo_store import bound_history

    snapshots = ["x" * 400, "y" * 400, "z" * 400]
    assert bound_history(snapshots, limit=100, max_chars=1000) == ["y" * 400, "z" * 400]


def test_the_newest_snapshots_are_the_ones_kept() -> None:
    """Undo walks backwards from now, so the oldest are the ones you can
    afford to lose."""
    from quill.core.undo_store import bound_history

    kept = bound_history(["a" * 100, "b" * 100, "c" * 100], limit=100, max_chars=250)
    assert kept == ["b" * 100, "c" * 100]


def test_one_snapshot_over_budget_is_still_kept() -> None:
    """A history of nothing means Ctrl+Z does nothing at all, which is a worse
    answer than one large entry."""
    from quill.core.undo_store import bound_history

    assert bound_history(["x" * 5000], limit=100, max_chars=10) == ["x" * 5000]


def test_a_small_document_keeps_every_step() -> None:
    """The budget must not cost anything for the documents most people write."""
    from quill.core.undo_store import MAX_HISTORY_CHARS, bound_history

    snapshots = ["x" * 20_000 for _ in range(100)]
    assert len(bound_history(snapshots, limit=100, max_chars=MAX_HISTORY_CHARS)) == 100


def test_the_count_limit_still_applies_inside_the_budget() -> None:
    from quill.core.undo_store import bound_history

    assert bound_history(["1", "2", "3", "4"], limit=2, max_chars=1_000) == ["3", "4"]


def test_an_empty_history_stays_empty() -> None:
    from quill.core.undo_store import bound_history

    assert bound_history([], limit=100, max_chars=1000) == []


def test_saving_trims_to_the_budget_and_reports_what_it_wrote(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The return value is what keeps the editor's in-memory copy in step; a
    caller that ignored it would hold undo steps that vanish on reopen."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "note.md"
    target.write_text("x", encoding="utf-8")

    written = save_undo_history(target, ["a" * 400, "b" * 400, "c" * 400], max_chars=1000)

    assert written == ["b" * 400, "c" * 400]
    assert load_undo_history(target) == written, "disk and the reported value must agree"
