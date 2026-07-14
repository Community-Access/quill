from __future__ import annotations

from quill.core.story.fields import FieldRow, build_rows, collect_fields
from quill.core.story.model import ElementKind


def test_character_rows_are_schema_then_tags() -> None:
    rows = build_rows(ElementKind.CHARACTER, {})
    assert [r.key for r in rows] == ["role", "goal", "motivation", "arc", "tags"]
    assert rows[0] == FieldRow(key="role", label="Role", value="", is_list=False)
    assert rows[-1].is_list is True  # tags


def test_rows_fill_values_from_stored() -> None:
    stored = {"type": "character", "goal": "Reclaim her name", "tags": ["pov", "act-one"]}
    rows = {r.key: r for r in build_rows(ElementKind.CHARACTER, stored)}
    assert rows["goal"].value == "Reclaim her name"
    assert rows["tags"].value == "pov, act-one"
    assert rows["role"].value == ""


def test_unknown_stored_keys_are_preserved_as_rows() -> None:
    rows = build_rows(ElementKind.PLOT, {"status": "unresolved", "mood": "tense"})
    keys = [r.key for r in rows]
    assert keys == ["status", "mood", "tags"]
    assert next(r for r in rows if r.key == "mood").label == "mood"


def test_collect_drops_empty_keeps_filled_and_splits_tags() -> None:
    result = collect_fields(
        ElementKind.CHARACTER,
        {"type": "character"},
        {"role": "protagonist", "goal": "", "tags": "pov, , act-one"},
    )
    assert result == {"type": "character", "role": "protagonist", "tags": ["pov", "act-one"]}


def test_collect_preserves_type_and_unknown_keys() -> None:
    result = collect_fields(
        ElementKind.PLOT,
        {"type": "plot", "mood": "tense"},
        {"status": "resolved", "mood": "calm"},
    )
    assert result["type"] == "plot"
    assert result["status"] == "resolved"
    assert result["mood"] == "calm"


def test_collect_round_trips_with_row_values() -> None:
    stored = {"type": "character", "role": "protagonist", "arc": "grows", "tags": ["a", "b"]}
    edits = {r.key: r.value for r in build_rows(ElementKind.CHARACTER, stored)}
    assert collect_fields(ElementKind.CHARACTER, stored, edits) == stored
