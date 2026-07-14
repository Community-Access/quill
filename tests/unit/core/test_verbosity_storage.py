"""Tests for verbosity custom-data storage (§35)."""

from __future__ import annotations

from pathlib import Path

from quill.core.verbosity.storage import (
    VerbosityCustomData,
    load_custom,
    save_custom,
    verbosity_custom_path,
)


def _data() -> VerbosityCustomData:
    return VerbosityCustomData(
        templates={"Concise": "{line}"},
        per_verb_overrides={"nav.next_line": "L{line}"},
        per_chord_overrides={"ctrl+s": "save"},
        data_order={"nav.next_line": ["line", "text"]},
        mastery={"enabled": True},
        feedback={"too_much": {"doc.save": 2}},
    )


def test_path_is_under_app_data() -> None:
    assert verbosity_custom_path().name == "verbosity_custom.json"


def test_missing_file_loads_empty_no_error(tmp_path: Path) -> None:
    result = load_custom(tmp_path / "verbosity_custom.json")
    assert result.ok
    assert result.data == VerbosityCustomData()


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "verbosity_custom.json"
    save_custom(_data(), target)
    loaded = load_custom(target)
    assert loaded.ok
    assert loaded.data == _data()


def test_atomic_write_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "verbosity_custom.json"
    save_custom(_data(), target)
    leftovers = [p for p in tmp_path.iterdir() if p.name != "verbosity_custom.json"]
    assert leftovers == []


def test_corrupt_file_loads_empty_with_error(tmp_path: Path) -> None:
    target = tmp_path / "verbosity_custom.json"
    target.write_text("{ this is not valid json", encoding="utf-8")
    result = load_custom(target)
    assert not result.ok
    assert result.error is not None
    assert result.data == VerbosityCustomData()


def test_non_object_json_is_an_error(tmp_path: Path) -> None:
    target = tmp_path / "verbosity_custom.json"
    target.write_text("[1, 2, 3]", encoding="utf-8")
    result = load_custom(target)
    assert not result.ok
    assert result.data == VerbosityCustomData()


def test_data_dict_round_trip() -> None:
    assert VerbosityCustomData.from_dict(_data().to_dict()) == _data()
