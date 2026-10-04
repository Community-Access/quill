"""The recent-documents rules both editors keep their lists by."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from quill.core import recent_documents as rd
from quill.core.recent import load_pinned_recent_files, save_pinned_recent_files


def test_remember_moves_to_the_top_without_a_duplicate_and_honours_the_limit() -> None:
    paths = ["a.txt", "b.txt", "c.txt"]
    assert rd.remember(paths, "c.txt", 10) == ["c.txt", "a.txt", "b.txt"]
    assert rd.remember(paths, "d.txt", 2) == ["d.txt", "a.txt"]


def test_two_spellings_of_one_file_are_one_row() -> None:
    assert rd.same_file("Docs/./Notes.txt", os.path.join("Docs", "Notes.txt"))
    assert rd.remember(["Docs/Notes.txt"], os.path.join("Docs", "Notes.txt"), 10) == [
        os.path.join("Docs", "Notes.txt")
    ]


def test_the_limit_is_clamped_to_one_through_fifty() -> None:
    assert rd.clamp_limit(0) == 1
    assert rd.clamp_limit(500) == 50
    assert rd.clamp_limit("12") == 12
    assert rd.clamp_limit("lots") == rd.DEFAULT_LIMIT
    assert rd.clamp_limit(None) == rd.DEFAULT_LIMIT


def test_pins_come_first_and_nothing_is_shown_twice() -> None:
    recent = ["new.txt", "pinned.txt", "old.txt"]
    pinned = ["pinned.txt", "kept-forever.txt"]
    assert rd.ordered(recent, pinned) == ["pinned.txt", "kept-forever.txt", "new.txt", "old.txt"]


def test_toggle_pin_pins_then_unpins() -> None:
    pinned, now = rd.toggle_pin([], "a.txt")
    assert (pinned, now) == (["a.txt"], True)
    pinned, now = rd.toggle_pin(pinned, "a.txt")
    assert (pinned, now) == ([], False)


def test_clear_leaves_pinned_documents_alone() -> None:
    assert rd.clear_unpinned(["a.txt", "b.txt", "c.txt"], ["b.txt"]) == ["b.txt"]
    assert rd.describe_cleared(2, 1) == "Cleared 2 recent documents. 1 pinned document stays."
    assert rd.describe_cleared(1, 0) == "Cleared 1 recent document."


def test_rows_say_pinned_and_not_found(tmp_path: Path) -> None:
    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    gone = tmp_path / "gone.txt"
    rows = rd.entries([str(here), str(gone)], [str(gone)])
    assert [row.name for row in rows] == ["gone.txt", "here.txt"]
    assert rows[0].label == f"gone.txt, in {tmp_path}, pinned, not found"
    assert rows[1].label == f"here.txt, in {tmp_path}"


def test_menu_rows_number_the_first_nine_only() -> None:
    first = rd.menu_label(1, "C:/Docs/a.txt", pinned=True)
    assert first.startswith("&1 a.txt  (")
    assert first.endswith(", pinned\tAlt+Shift+1")
    assert "\t" not in rd.menu_label(10, "C:/Docs/a.txt")


def test_the_menu_skips_only_what_is_certainly_gone() -> None:
    shown = rd.menu_paths(["a", "b", "c"], ["c"], gone=lambda path: path == "b")
    assert shown == ["c", "a"]


def test_drop_missing_keeps_files_it_cannot_prove_are_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.recent as recent_module

    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    gone = tmp_path / "gone.txt"
    monkeypatch.setattr(recent_module, "_is_fixed_drive", lambda _p: True)
    assert rd.drop_missing([str(here), str(gone)]) == [str(here)]
    monkeypatch.setattr(recent_module, "_is_fixed_drive", lambda _p: False)
    assert rd.drop_missing([str(here), str(gone)]) == [str(here), str(gone)]


def test_quill_keeps_its_pins_beside_recent_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert load_pinned_recent_files() == []
    save_pinned_recent_files([str(tmp_path / "a.txt")])
    assert load_pinned_recent_files() == [str(tmp_path / "a.txt")]
    assert (tmp_path / "recent-pinned.json").is_file()
