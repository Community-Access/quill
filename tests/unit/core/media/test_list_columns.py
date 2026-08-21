"""The shared column machinery: order, hiding, repair, preview, persistence.

The rules under test are the ones the module docstring calls requirements: a
pinned column can never be hidden, a hidden column is absent rather than last,
and a layout from another build is repaired rather than obeyed.
"""

from __future__ import annotations

import json

import pytest

from quill.core.media.list_columns import (
    ColumnDef,
    ColumnLayouts,
    SurfaceDef,
    load_column_layouts,
    preview_row,
    repair_order,
    save_column_layouts,
)

_SURFACE = SurfaceDef(
    id="demo.rows",
    label="Demo rows",
    columns=(
        ColumnDef("name", "Name", "What it is called.", pinned=True),
        ColumnDef("country", "Country", "Where it is."),
        ColumnDef("format", "Format", "How it sounds."),
        ColumnDef("votes", "Popularity", "How many liked it.", default_visible=False),
    ),
    sample={
        "name": "KFI AM 640",
        "country": "United States",
        "format": "MP3 128k",
        "votes": "1,204 votes",
    },
)
_CATALOGUE = {_SURFACE.id: _SURFACE}


@pytest.fixture
def layouts() -> ColumnLayouts:
    return ColumnLayouts.defaults(_CATALOGUE)


def test_defaults_show_everything_marked_visible(layouts: ColumnLayouts) -> None:
    assert [column.id for column in layouts.columns("demo.rows")] == [
        "name",
        "country",
        "format",
    ]


def test_a_column_switched_off_by_default_is_offered_but_not_read(
    layouts: ColumnLayouts,
) -> None:
    shown = {column.id for column in layouts.columns("demo.rows")}
    offered = {column.id for column, _visible in layouts.all_columns("demo.rows")}
    assert "votes" not in shown
    assert "votes" in offered


def test_hiding_a_column_removes_it_from_the_row_entirely(layouts: ColumnLayouts) -> None:
    layouts.set_visible("demo.rows", "country", False)
    assert [column.id for column in layouts.columns("demo.rows")] == ["name", "format"]
    # Not merely moved to the end: a screen reader reads every column it is
    # given, so "last" would still be spoken.
    assert "country" not in layouts.preview("demo.rows")


def test_the_pinned_column_cannot_be_hidden_however_it_is_asked(
    layouts: ColumnLayouts,
) -> None:
    layouts.set_visible("demo.rows", "name", False)
    assert "name" in [column.id for column in layouts.columns("demo.rows")]


def test_a_hidden_column_keeps_its_place_and_comes_back_to_it(
    layouts: ColumnLayouts,
) -> None:
    layouts.set_visible("demo.rows", "country", False)
    layouts.set_visible("demo.rows", "country", True)
    assert [column.id for column in layouts.columns("demo.rows")] == [
        "name",
        "country",
        "format",
    ]


def test_the_preview_is_the_sentence_a_row_reads(layouts: ColumnLayouts) -> None:
    assert layouts.preview("demo.rows") == "KFI AM 640, United States, MP3 128k"
    layouts.set_visible("demo.rows", "country", False)
    assert layouts.preview("demo.rows") == "KFI AM 640, MP3 128k"


def test_the_preview_skips_a_column_the_sample_has_nothing_for() -> None:
    columns = [ColumnDef("a", "A"), ColumnDef("b", "B")]
    assert preview_row(columns, {"a": "one", "b": "  "}) == "one"


def test_an_unknown_column_in_a_saved_order_is_dropped() -> None:
    order = repair_order(_CATALOGUE, "demo.rows", ["format", "from_the_future", "name"])
    assert order == ["format", "name", "country", "votes"]


def test_a_column_missing_from_a_saved_order_is_appended_not_lost() -> None:
    order = repair_order(_CATALOGUE, "demo.rows", ["country"])
    assert order[0] == "country"
    assert set(order) == {"name", "country", "format", "votes"}


def test_a_saved_layout_that_would_hide_the_pinned_column_is_repaired() -> None:
    stored = {"demo.rows": {"order": ["name", "country"], "hidden": ["name", "country"]}}
    layouts = ColumnLayouts.from_dict(_CATALOGUE, stored)
    assert [column.id for column in layouts.columns("demo.rows")][0] == "name"


def test_an_unknown_surface_answers_empty_rather_than_raising(
    layouts: ColumnLayouts,
) -> None:
    assert layouts.columns("nobody.knows") == []
    assert layouts.preview("nobody.knows") == ""
    layouts.set_order("nobody.knows", ["x"])
    layouts.set_visible("nobody.knows", "x", False)


def test_reset_puts_a_surface_back_the_way_it_shipped(layouts: ColumnLayouts) -> None:
    layouts.set_order("demo.rows", ["votes", "format", "country", "name"])
    layouts.set_visible("demo.rows", "country", False)
    layouts.reset("demo.rows")
    assert [column.id for column in layouts.columns("demo.rows")] == [
        "name",
        "country",
        "format",
    ]


def test_a_copy_is_independent_so_cancel_can_mean_cancel(layouts: ColumnLayouts) -> None:
    editable = layouts.copy()
    editable.set_visible("demo.rows", "country", False)
    assert [column.id for column in layouts.columns("demo.rows")] == [
        "name",
        "country",
        "format",
    ]


def test_a_layout_round_trips_through_the_store(tmp_path) -> None:
    layouts = ColumnLayouts.defaults(_CATALOGUE)
    layouts.set_order("demo.rows", ["format", "name", "country", "votes"])
    layouts.set_visible("demo.rows", "country", False)
    save_column_layouts(tmp_path, layouts, file_name="demo.json")
    read_back = load_column_layouts(tmp_path, file_name="demo.json", catalogue=_CATALOGUE)
    assert [column.id for column in read_back.columns("demo.rows")] == ["format", "name"]


def test_an_absent_or_broken_store_reads_as_the_defaults(tmp_path) -> None:
    absent = load_column_layouts(tmp_path, file_name="nothing.json", catalogue=_CATALOGUE)
    assert [column.id for column in absent.columns("demo.rows")] == ["name", "country", "format"]
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    broken = load_column_layouts(tmp_path, file_name="broken.json", catalogue=_CATALOGUE)
    assert [column.id for column in broken.columns("demo.rows")] == ["name", "country", "format"]


def test_the_stored_file_is_readable_json_with_both_answers(tmp_path) -> None:
    layouts = ColumnLayouts.defaults(_CATALOGUE)
    save_column_layouts(tmp_path, layouts, file_name="demo.json")
    stored = json.loads((tmp_path / "demo.json").read_text(encoding="utf-8"))
    assert stored["demo.rows"]["order"] == ["name", "country", "format", "votes"]
    assert stored["demo.rows"]["hidden"] == ["votes"]
