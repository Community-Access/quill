"""The shared abbreviation library's v2 schema.

The compatibility promise is the point: QUILL and Quill Inkwell read and write
one file, and a build of either that predates v2 must keep working.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.abbreviations import (
    SCHEMA_VERSION,
    Abbreviation,
    AbbreviationLibrary,
    categories,
    load_abbreviation_library,
    quick_insert_order,
    record_use,
    save_abbreviation_library,
    try_expand,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "abbreviations.json").write_text(json.dumps(payload), encoding="utf-8")


def test_v1_file_loads_with_v2_defaults(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "version": 1,
            "abbreviations": [{"id": "a", "abbreviation": "btw", "expansion": "by the way"}],
        },
    )
    library = load_abbreviation_library(tmp_path)
    entry = library.abbreviations[0]
    assert entry.category == ""
    assert entry.triggers == "both"
    assert entry.speak_mode == "silent"
    assert entry.sound == "inherit"
    assert entry.trailing_space is False
    assert entry.usage_count == 0


def test_v2_round_trip_preserves_every_setting(tmp_path: Path) -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[
            Abbreviation(
                id="a",
                abbreviation="addr",
                expansion="12 High Street",
                category="Personal",
                speak_mode="expansion",
                sound="off",
                trailing_space=True,
                triggers="punctuation",
                usage_count=7,
                last_used="2026-08-11T00:00:00+00:00",
            )
        ],
    )
    save_abbreviation_library(library, tmp_path)
    reloaded = load_abbreviation_library(tmp_path).abbreviations[0]
    assert reloaded.category == "Personal"
    assert reloaded.speak_mode == "expansion"
    assert reloaded.sound == "off"
    assert reloaded.trailing_space is True
    assert reloaded.triggers == "punctuation"
    assert reloaded.usage_count == 7


def test_saving_stamps_the_current_schema_version(tmp_path: Path) -> None:
    save_abbreviation_library(AbbreviationLibrary(version=1, abbreviations=[]), tmp_path)
    raw = json.loads((tmp_path / "abbreviations.json").read_text(encoding="utf-8"))
    assert raw["version"] == SCHEMA_VERSION


def test_unknown_setting_values_degrade_to_the_safe_default(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "version": 2,
            "abbreviations": [
                {
                    "id": "a",
                    "abbreviation": "btw",
                    "expansion": "by the way",
                    "triggers": "whenever-it-feels-like-it",
                    "speak_mode": "shout",
                    "sound": "maybe",
                }
            ],
        },
    )
    entry = load_abbreviation_library(tmp_path).abbreviations[0]
    assert entry.triggers == "both"
    assert entry.speak_mode == "silent"
    assert entry.sound == "inherit"


def test_editor_expansion_honours_the_trigger_mode() -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[
            Abbreviation(id="a", abbreviation="btw", expansion="by the way", triggers="space")
        ],
    )
    assert try_expand("btw ", 4, library) is not None
    assert try_expand("btw.", 4, library) is None


def test_editor_expansion_reports_trailing_space_after_punctuation_only() -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[
            Abbreviation(id="a", abbreviation="co", expansion="Company", trailing_space=True)
        ],
    )
    punctuation = try_expand("co,", 3, library)
    space = try_expand("co ", 3, library)
    assert punctuation is not None and punctuation.trailing_space is True
    assert space is not None and space.trailing_space is False


def test_quick_insert_order_is_most_used_then_alphabetical() -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[
            Abbreviation(id="1", abbreviation="zed", expansion="z", usage_count=5),
            Abbreviation(id="2", abbreviation="alpha", expansion="a"),
            Abbreviation(id="3", abbreviation="beta", expansion="b"),
            Abbreviation(id="4", abbreviation="off", expansion="o", enabled=False),
        ],
    )
    assert [a.abbreviation for a in quick_insert_order(library)] == ["zed", "alpha", "beta"]


def test_manual_entries_are_offered_in_quick_insert() -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[
            Abbreviation(id="1", abbreviation="nda", expansion="long", triggers="manual")
        ],
    )
    assert [a.abbreviation for a in quick_insert_order(library)] == ["nda"]


def test_record_use_counts_and_timestamps() -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[Abbreviation(id="1", abbreviation="btw", expansion="by the way")],
    )
    record_use(library, "1")
    entry = library.abbreviations[0]
    assert entry.usage_count == 1
    assert entry.last_used


def test_categories_lists_each_once_in_first_seen_order() -> None:
    library = AbbreviationLibrary(
        version=SCHEMA_VERSION,
        abbreviations=[
            Abbreviation(id="1", abbreviation="a", expansion="a", category="Work"),
            Abbreviation(id="2", abbreviation="b", expansion="b", category=""),
            Abbreviation(id="3", abbreviation="c", expansion="c", category="Work"),
        ],
    )
    assert categories(library) == ["Work", ""]
