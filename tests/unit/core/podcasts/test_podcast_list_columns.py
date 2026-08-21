"""Cast's column catalogue, held to the same promise Radio's is.

See ``tests/unit/core/radio/test_radio_list_columns.py`` for why: a column
somebody can switch on and then hear nothing from is worse than one that was
never offered.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.media.list_columns import ColumnLayouts
from quill.core.podcasts.list_columns import (
    FILE_NAME,
    SURFACE_LABELS,
    SURFACES,
    load_podcast_column_layouts,
    save_podcast_column_layouts,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

#: surface id -> the module whose fill site builds that surface's row values.
_FILL_SITES = {
    "cast.episodes": "quill/ui/podcasts/manager_row_view.py",
    "cast.downloads": "quill/ui/podcasts/downloads_dialog.py",
    "cast.directory_results": "quill/ui/podcasts/add_podcast_dialog.py",
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
    assert undescribed == []


def test_the_labels_list_covers_every_surface_exactly_once() -> None:
    labelled = [surface_id for surface_id, _label in SURFACE_LABELS]
    assert sorted(labelled) == sorted(SURFACES)
    assert len(labelled) == len(set(labelled))


def test_cast_and_radio_do_not_share_a_store() -> None:
    """Two catalogues with nothing in common must not read one file.

    Each app's repair pass drops ids it does not know, so a shared file would
    mean each app quietly deleting the other's layout on every save.
    """
    from quill.core.radio.list_columns import FILE_NAME as RADIO_FILE_NAME

    assert FILE_NAME != RADIO_FILE_NAME


def test_defaults_round_trip_through_casts_own_store(tmp_path: Path) -> None:
    layouts = ColumnLayouts.defaults(SURFACES)
    layouts.set_visible("cast.episodes", "podcast", True)
    layouts.set_visible("cast.episodes", "published", False)
    save_podcast_column_layouts(tmp_path, layouts)
    assert (tmp_path / FILE_NAME).is_file()
    read_back = load_podcast_column_layouts(tmp_path)
    shown = [column.id for column in read_back.columns("cast.episodes")]
    assert "published" not in shown
    assert "podcast" in shown
    assert shown[0] == "title"
