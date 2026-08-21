"""List columns for Quill Radio: what each row says, and in what order.

Radio's report lists were built with the columns their author needed and no way
to change them, so every listener heard the same sentence on every row. Somebody
who browses by network heard the source last; somebody who never leaves one
country heard a country on all sixty thousand rows.

The machinery is shared (:mod:`quill.core.media.list_columns`); this module is
only the catalogue: which lists can be configured, what each one can offer, and
what a row of it reads like. Ids are the keys the dialogs fill their rows by, so
adding a column here means adding one value to a fill site -- and
``tests/unit/core/radio/test_radio_list_columns.py`` fails the build if a
catalogue column has no value site, because a column that is always empty is a
row that says nothing where the listener asked for something.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.media.list_columns import (
    ColumnDef,
    ColumnLayouts,
    SurfaceDef,
    load_column_layouts,
    save_column_layouts,
)

__all__ = [
    "FILE_NAME",
    "RECORDINGS",
    "STATION_RESULTS",
    "SURFACES",
    "SURFACE_LABELS",
    "load_radio_column_layouts",
    "save_radio_column_layouts",
]

#: Radio's own store. A separate file from Cast's for the reason its Quick
#: Actions store is separate: the two apps' surfaces and column ids have nothing
#: in common, and a shared file would mean each app's repair pass quietly
#: discarding the other's layout.
FILE_NAME = "radio_list_columns.json"

#: Find Stations results. The station's name is pinned: a search result with no
#: name is a row nobody can act on.
STATION_RESULTS = SurfaceDef(
    id="radio.station_results",
    label="Find Stations results",
    columns=(
        ColumnDef(
            "name",
            "Name",
            "The station's name, with its source and any playability warning.",
            width=240,
            pinned=True,
        ),
        ColumnDef("country", "Country", "Where the station broadcasts from.", width=120),
        ColumnDef("format", "Format", "Codec and bitrate, for example MP3 128k.", width=110),
        ColumnDef("source", "Source", "Which directory listed the station.", width=110),
        ColumnDef(
            "language",
            "Language",
            "The language the station broadcasts in, where the directory says.",
            width=110,
            default_visible=False,
        ),
        ColumnDef(
            "tags",
            "Genres",
            "The directory's own genre tags for the station.",
            width=180,
            default_visible=False,
        ),
        ColumnDef(
            "votes",
            "Popularity",
            "How many listeners voted for the station in the directory.",
            width=90,
            default_visible=False,
        ),
        ColumnDef(
            "bitrate",
            "Bitrate",
            "The bitrate on its own, for comparing quality at a glance.",
            width=80,
            default_visible=False,
        ),
    ),
    sample={
        "name": "KFI AM 640",
        "country": "United States",
        "format": "MP3 128k",
        "source": "Radio Browser",
        "language": "English",
        "tags": "news, talk",
        "votes": "1,204 votes",
        "bitrate": "128k",
    },
)

#: The Recordings window. The recording's name is pinned for the same reason.
RECORDINGS = SurfaceDef(
    id="radio.recordings",
    label="Recordings",
    columns=(
        ColumnDef(
            "name",
            "Name",
            "The recording's file name, or the station and programme it captures.",
            width=280,
            pinned=True,
        ),
        ColumnDef(
            "status",
            "Status",
            "Recording, Recorded, Scheduled, or Completed.",
            width=100,
        ),
        ColumnDef("size", "Size", "How much disk the file uses.", width=100),
        ColumnDef("when", "When", "When the recording ran, or is due to run.", width=220),
        ColumnDef(
            "length",
            "Length",
            "How long a capture was asked to run. Blank where the number is a "
            "disk-safety cap rather than a length somebody chose.",
            width=90,
            default_visible=False,
        ),
    ),
    sample={
        "name": "KFI - Morning Show",
        "status": "Recorded",
        "size": "48.2 MB",
        "when": "Today at 09:00",
        "length": "60 min",
    },
)

#: Every configurable Radio list, by id.
SURFACES: dict[str, SurfaceDef] = {
    STATION_RESULTS.id: STATION_RESULTS,
    RECORDINGS.id: RECORDINGS,
}

#: (surface id, label) in the order the configuration dialog offers them.
SURFACE_LABELS: tuple[tuple[str, str], ...] = (
    (STATION_RESULTS.id, STATION_RESULTS.label),
    (RECORDINGS.id, RECORDINGS.label),
)


def load_radio_column_layouts(data_dir: Path) -> ColumnLayouts:
    """Radio's saved column layouts, repaired against this build's catalogue."""
    return load_column_layouts(data_dir, file_name=FILE_NAME, catalogue=SURFACES)


def save_radio_column_layouts(data_dir: Path, layouts: ColumnLayouts) -> None:
    """Persist Radio's column layouts."""
    save_column_layouts(data_dir, layouts, file_name=FILE_NAME)
