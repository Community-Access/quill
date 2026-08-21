"""List columns for QUILL Cast: what each row says, and in what order.

The counterpart to :mod:`quill.core.radio.list_columns`, on the same shared
machinery (:mod:`quill.core.media.list_columns`) and for the same reason: an
episode list is read column by column, so whoever chose the columns chose the
sentence every episode speaks. Somebody who queues by length wants the duration
early; somebody who works through one show at a time does not want its name
repeated two hundred times.

Ids are the keys the dialogs fill their rows by, and
``tests/unit/core/podcasts/test_podcast_list_columns.py`` fails the build if a
catalogue column has no value site.

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
    "DIRECTORY_RESULTS",
    "DOWNLOADS",
    "EPISODES",
    "FILE_NAME",
    "SURFACES",
    "SURFACE_LABELS",
    "load_podcast_column_layouts",
    "save_podcast_column_layouts",
]

#: Cast's own store, separate from Radio's -- see the note on Radio's.
FILE_NAME = "podcast_list_columns.json"

#: The episode list. The title is pinned: an episode row with no title is a row
#: nobody can choose between.
EPISODES = SurfaceDef(
    id="cast.episodes",
    label="Episodes",
    columns=(
        ColumnDef(
            "title",
            "Title",
            "The episode's own title.",
            width=280,
            pinned=True,
        ),
        ColumnDef("published", "Published", "The date the episode was published.", width=110),
        ColumnDef("duration", "Duration", "How long the episode runs.", width=80),
        ColumnDef(
            "status",
            "Status",
            "New, played, downloaded, or how far through you are.",
            width=130,
        ),
        ColumnDef(
            "podcast",
            "Podcast",
            "The show the episode belongs to. Worth showing in a list that "
            "spans several shows, and noise in a list of one.",
            width=180,
            default_visible=False,
        ),
        ColumnDef(
            "remaining",
            "Time Left",
            "How much of the episode you have not heard yet.",
            width=90,
            default_visible=False,
        ),
        ColumnDef(
            "downloaded",
            "Downloaded",
            "Whether the audio is on this computer or streams.",
            width=100,
            default_visible=False,
        ),
    ),
    sample={
        "title": "The One About Chapters",
        "published": "2026-08-14",
        "duration": "58 min",
        "status": "Played",
        "podcast": "The Earshot Show",
        "remaining": "12 min left",
        "downloaded": "Downloaded",
    },
)

#: The Downloads window.
DOWNLOADS = SurfaceDef(
    id="cast.downloads",
    label="Downloads",
    columns=(
        ColumnDef(
            "podcast",
            "Podcast",
            "The show whose downloads the row totals.",
            width=300,
            pinned=True,
        ),
        ColumnDef("files", "Files", "How many episode files are on disk.", width=80),
        ColumnDef("size", "Size", "How much disk the show's downloads use.", width=110),
    ),
    sample={
        "podcast": "The Earshot Show",
        "files": "12",
        "size": "486 MB",
    },
)

#: Add Podcast search results.
DIRECTORY_RESULTS = SurfaceDef(
    id="cast.directory_results",
    label="Add Podcast search results",
    columns=(
        ColumnDef(
            "title",
            "Title",
            "The show's name.",
            width=320,
            pinned=True,
        ),
        ColumnDef(
            "artist",
            "Artist/Network",
            "Who publishes the show.",
            width=220,
        ),
        ColumnDef(
            "feed",
            "Feed Address",
            "The show's feed address -- what tells two shows with the same name apart.",
            width=260,
            default_visible=False,
        ),
    ),
    sample={
        "title": "The Earshot Show",
        "artist": "Earshot Media",
        "feed": "https://example.com/earshot.xml",
    },
)

#: Every configurable Cast list, by id.
SURFACES: dict[str, SurfaceDef] = {
    EPISODES.id: EPISODES,
    DOWNLOADS.id: DOWNLOADS,
    DIRECTORY_RESULTS.id: DIRECTORY_RESULTS,
}

#: (surface id, label) in the order the configuration dialog offers them.
SURFACE_LABELS: tuple[tuple[str, str], ...] = (
    (EPISODES.id, EPISODES.label),
    (DOWNLOADS.id, DOWNLOADS.label),
    (DIRECTORY_RESULTS.id, DIRECTORY_RESULTS.label),
)


def load_podcast_column_layouts(data_dir: Path) -> ColumnLayouts:
    """Cast's saved column layouts, repaired against this build's catalogue."""
    return load_column_layouts(data_dir, file_name=FILE_NAME, catalogue=SURFACES)


def save_podcast_column_layouts(data_dir: Path, layouts: ColumnLayouts) -> None:
    """Persist Cast's column layouts."""
    save_column_layouts(data_dir, layouts, file_name=FILE_NAME)
