"""Radio's column catalogue, and the promise each entry makes.

A column somebody can switch on and then hear nothing from is worse than one
that was never offered: they made a choice, the app agreed, and the row went on
saying the same thing. These tests hold the catalogue to what the fill sites can
actually produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.media.list_columns import ColumnLayouts
from quill.core.radio.list_columns import (
    FILE_NAME,
    SURFACE_LABELS,
    SURFACES,
    load_radio_column_layouts,
    save_radio_column_layouts,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

#: surface id -> the module whose fill site builds that surface's row values.
_FILL_SITES = {
    "radio.station_results": "quill/ui/radio/results_view.py",
    "radio.recordings": "quill/ui/radio/recordings_row_view.py",
}


@pytest.mark.parametrize("surface_id", sorted(SURFACES))
def test_every_surface_pins_exactly_one_column(surface_id: str) -> None:
    surface = SURFACES[surface_id]
    pinned = [column.id for column in surface.columns if column.pinned]
    assert len(pinned) == 1, f"{surface_id} must pin the column that names the row"


@pytest.mark.parametrize("surface_id", sorted(SURFACES))
def test_column_ids_are_unique_within_a_surface(surface_id: str) -> None:
    ids = [column.id for column in SURFACES[surface_id].columns]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("surface_id", sorted(SURFACES))
def test_every_column_has_a_sample_so_the_preview_is_complete(surface_id: str) -> None:
    surface = SURFACES[surface_id]
    missing = [column.id for column in surface.columns if not surface.sample.get(column.id)]
    assert missing == [], (
        f"{surface_id} offers {missing} with nothing in its sample row, so the "
        "Choose Columns preview would go quiet where the real row speaks."
    )


@pytest.mark.parametrize("surface_id", sorted(SURFACES))
def test_every_column_has_a_value_site(surface_id: str) -> None:
    """Every offered column is filled somewhere.

    Read from the fill site's source rather than by building a wx list: the
    check is "does this id appear as a key where the row is built", which is
    exactly what a reader would look for, and it needs no display.
    """
    source = (_REPO_ROOT / _FILL_SITES[surface_id]).read_text(encoding="utf-8")
    missing = [
        column.id for column in SURFACES[surface_id].columns if f'"{column.id}":' not in source
    ]
    assert missing == [], (
        f"{surface_id} offers {missing}, and {_FILL_SITES[surface_id]} never "
        "fills them -- a column somebody can switch on and hear nothing from."
    )


@pytest.mark.parametrize("surface_id", sorted(SURFACES))
def test_every_column_carries_a_description_for_the_dialog(surface_id: str) -> None:
    undescribed = [column.id for column in SURFACES[surface_id].columns if not column.description]
    assert undescribed == [], (
        f"{surface_id} offers {undescribed} with no description, so Choose "
        "Columns would list a name and say nothing about what it holds."
    )


def test_the_labels_list_covers_every_surface_exactly_once() -> None:
    labelled = [surface_id for surface_id, _label in SURFACE_LABELS]
    assert sorted(labelled) == sorted(SURFACES)
    assert len(labelled) == len(set(labelled))


def test_defaults_round_trip_through_radios_own_store(tmp_path: Path) -> None:
    layouts = ColumnLayouts.defaults(SURFACES)
    layouts.set_visible("radio.station_results", "country", False)
    save_radio_column_layouts(tmp_path, layouts)
    assert (tmp_path / FILE_NAME).is_file()
    read_back = load_radio_column_layouts(tmp_path)
    shown = [column.id for column in read_back.columns("radio.station_results")]
    assert "country" not in shown
    assert shown[0] == "name"
