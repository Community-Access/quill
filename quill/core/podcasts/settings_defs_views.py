"""Catalogue entries for how the library and the Inbox are laid out.

Rich library views (Jeff, 2026-10-03): folders first, folders only, podcasts
without folders, or everything together; how folders are ordered and whether
they open; what the counts beside each row say; and, for the Inbox, whether it
is one long list or folders first and then the episodes not in any folder.

Stored by id in the library's shared defaults (no dataclass field), so the
Preferences rows, settings search and the View menu all read the one value
through :mod:`quill.core.podcasts.library_view`.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from quill.core.podcasts.settings_types import (
    CATEGORY_CURATION,
    KIND_BOOL,
    KIND_CHOICE,
    LEVEL_GLOBAL,
    SettingDef,
    choices,
    define,
)

LIBRARY_LAYOUTS = (
    ("folders_first", "Folders first, then podcasts"),
    ("folders_only", "Folders only"),
    ("podcasts_only", "Podcasts only, without folders"),
    ("mixed", "Folders and podcasts together, by name"),
)
FOLDER_SORTS = (
    ("custom", "My own order"),
    ("name_az", "Name, A to Z"),
    ("name_za", "Name, Z to A"),
    ("most_unheard", "Most unheard first"),
    ("most_podcasts", "Most podcasts first"),
)
FOLDERS_OPEN = (
    ("open", "Open, showing their podcasts"),
    ("closed", "Closed, until you open one"),
)
LIBRARY_COUNTS = (
    ("unheard", "Unheard episodes"),
    ("podcasts", "Podcasts in each folder"),
    ("both", "Both"),
    ("none", "No counts"),
)
INBOX_LAYOUTS = (
    ("episodes", "Every episode in one list"),
    ("folders_first", "Folders first, then episodes"),
    ("folders_only", "Folders only"),
)

SETTINGS: tuple[SettingDef, ...] = (
    define(
        "library_layout",
        "Show the library as:",
        "How the Podcasts place is laid out. Folders first lists your folders and "
        "then the podcasts in no folder. Folders only shows just the folders, with "
        "one more for podcasts in no folder, so a long library is short to read. "
        "Podcasts only leaves folders out and lists every podcast. Together mixes "
        "folders and podcasts in one order, by name. No podcast is ever hidden.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="folders_first",
        choices=choices(*LIBRARY_LAYOUTS),
        aliases=("library", "layout", "view", "folders"),
    ),
    define(
        "folder_sort_mode",
        "Sort folders by:",
        "The order your folders are listed in, in the library and the Inbox. My own "
        "order is the one you set with Move Up and Move Down. It changes the order "
        "only; no folder is hidden.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="custom",
        choices=choices(*FOLDER_SORTS),
        aliases=("folders", "sort", "order"),
    ),
    define(
        "library_folders_open",
        "Folders in the library start:",
        "Whether each folder in the library is open, showing its podcasts, or closed "
        "until you open it with the Right arrow. Nothing in a closed folder is "
        "hidden; it is one arrow away.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="open",
        choices=choices(*FOLDERS_OPEN),
        aliases=("folders", "expand", "collapse"),
    ),
    define(
        "library_counts",
        "Counts in the library say:",
        "What the number beside each folder and podcast tells you: how many episodes "
        "are unheard, how many podcasts a folder holds, both, or nothing at all.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="both",
        choices=choices(*LIBRARY_COUNTS),
        aliases=("unheard", "count", "number"),
    ),
    define(
        "library_hide_empty_folders",
        "Leave out folders with nothing in them",
        "Leaves empty folders out of the library. They are still there, and come "
        "back the moment a podcast is filed in one.",
        kind=KIND_BOOL,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default=False,
        aliases=("folders", "empty"),
    ),
    define(
        "inbox_layout",
        "Show the Inbox as:",
        "Every episode in one list, or your folders first and then the episodes from "
        "podcasts in no folder. Enter on a folder shows just its episodes, and "
        "Backspace comes back. Folders only lists just the folders.",
        kind=KIND_CHOICE,
        category=CATEGORY_CURATION,
        levels=(LEVEL_GLOBAL,),
        default="episodes",
        choices=choices(*INBOX_LAYOUTS),
        aliases=("inbox", "folders", "layout", "view"),
    ),
)

__all__ = [
    "FOLDERS_OPEN",
    "FOLDER_SORTS",
    "INBOX_LAYOUTS",
    "LIBRARY_COUNTS",
    "LIBRARY_LAYOUTS",
    "SETTINGS",
]
