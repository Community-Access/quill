"""What QuillLite can be, and what it is by default.

QuillLite stays small by being *switchable*, not by being poor. Somebody who
wants Notepad can turn the Format menu off and never see rich text again;
somebody who wants WordPad-with-tools can turn everything on. The mechanism is
QUILL's own :mod:`quill.core.app_features`, the same one Radio and Cast use for
their menus, and the dialog is the shared
:class:`~quill.ui.app_features_dialog.AppFeaturesDialog`.

Two rules, and the second is the one that needed adding.

**Everything unknown is on.** ``AppFeatureSettings`` stores only what a user
explicitly turned *off*, so an area added in a later version is enabled for
everyone who never said otherwise. That is the right default for a feature
somebody would miss.

**Except the ones that start off.** :data:`DEFAULT_OFF` is the small set that
would be *wrong* on by default rather than merely unused -- autocorrect
rewriting a config file's quotes, backups quietly filling a folder, a second
"go to" front door before anyone asked for one. They are seeded as disabled on
first run and are otherwise ordinary areas: one checkbox each, in the same
dialog, discoverable rather than hidden. A feature nobody can find is a feature
that does not exist, so the answer is a checklist, not a config file.

wx-free. The areas are data; honouring them is the menu builder's job.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.app_features import (
    AppArea,
    AppFeatureSettings,
    load_app_features,
    save_app_features,
)

__all__ = [
    "AREAS",
    "APP_ID",
    "DEFAULT_OFF",
    "area_ids",
    "load_features",
    "save_features",
]

#: The key this app's areas are stored under. Shared store, keyed per app, so
#: turning the Format menu off here can never touch Quill Radio.
APP_ID = "quilllite"

AREAS: tuple[AppArea, ...] = (
    AppArea(
        "rich_text",
        "Rich text and the Format menu",
        "Bold, italic, headings, alignment, bullets and line spacing. Turn this "
        "off to make QuillLite a plain text editor and nothing else.",
    ),
    AppArea(
        "headings",
        "Heading navigation",
        "Move between headings, and list every heading in the document. Rich "
        "text only; it goes with the Format menu.",
    ),
    AppArea(
        "bookmarks",
        "Bookmarks",
        "Nine numbered places you can jump back to, and the list that shows them.",
    ),
    AppArea(
        "tools",
        "The Tools menu",
        "Sort lines, remove blanks and duplicates, trim trailing spaces, change "
        "case, and choose the encoding and line endings a file saves with.",
    ),
    AppArea(
        "clipboard",
        "Copy Tray and the clip library",
        "Numbered clipboard slots, a collector that gathers several copies into "
        "one, and a rolling history of everything you have copied. Paste as "
        "plain text stays available either way.",
    ),
    AppArea(
        "printing",
        "Printing",
        "Page Setup and Print.",
    ),
    AppArea(
        "abbreviations",
        "Abbreviations",
        "Type a short form and a space, and get the long one. Uses QuillLite's "
        "own list unless you ask it to share QUILL's in Preferences.",
    ),
    AppArea(
        "selection",
        "The Selection submenu",
        "Edit > Selection: mark and extend with F8, select a whole word, line, "
        "paragraph, sentence or block in one keystroke, grow and shrink a "
        "selection, and drop marks you can bounce back to. Select All keeps its "
        "own place in the Edit menu, so it is still here when this is off.",
    ),
    AppArea(
        "spelling",
        "Spell check",
        "Check spelling as you type, and review the whole document with F7. "
        "Uses QuillLite's own dictionary of taught words unless you ask it to "
        "share QUILL's in Preferences. Stays quiet in source and configuration "
        "files, where every identifier would be a false alarm.",
    ),
    AppArea(
        "autoformat",
        "Autocorrect while typing",
        "Curly quotes, em dashes, and a capital at the start of a sentence. "
        "Welcome in prose and actively wrong in a configuration file, which is "
        "why it starts switched off.",
    ),
    AppArea(
        "backups",
        "Timestamped backups",
        "Keep a dated copy of each file every time you save it, separate from "
        "the recovery of unsaved work. Reassuring, and it fills a folder, which "
        "is why it starts switched off.",
    ),
    AppArea(
        "go_to_anything",
        "Go To Anything",
        "One box that searches commands, headings and bookmarks together. The "
        "Command Palette, the headings list and the bookmark list each already "
        "do their own part of this, so it starts switched off.",
    ),
)

#: Areas that start disabled. Everything else starts enabled, because
#: AppFeatureSettings stores only explicit "off".
DEFAULT_OFF: frozenset[str] = frozenset({"autoformat", "backups", "go_to_anything"})

#: Written into the store the first time so the seeding happens exactly once. A
#: user who turns autocorrect *on* must not have it turned off again next launch.
_SEEDED_MARKER = "_seeded"


def area_ids() -> frozenset[str]:
    """Every area id, for a test that the command table names only real ones."""
    return frozenset(area.id for area in AREAS)


def load_features(data_dir: Path) -> AppFeatureSettings:
    """This app's area settings, seeding the default-off set on first run.

    The marker is stored as a disabled "area" that no menu ever asks about, so
    seeding happens once and a later change of mind sticks. Storing it in the
    same set rather than in a second file keeps the whole thing one small JSON
    object that a person can read.
    """
    settings = load_app_features(data_dir, APP_ID)
    if _SEEDED_MARKER not in settings.disabled:
        settings.disabled |= set(DEFAULT_OFF)
        settings.disabled.add(_SEEDED_MARKER)
        save_app_features(data_dir, settings)
    return settings


def save_features(data_dir: Path, settings: AppFeatureSettings) -> None:
    """Persist the settings, keeping the seeded marker whatever the dialog did."""
    settings.disabled.add(_SEEDED_MARKER)
    save_app_features(data_dir, settings)
