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

**The areas stay coarse, and the dialog got a search box and profiles instead.**
That was the open question and this is the answer. An area here is a whole menu
or submenu that can be removed cleanly (``MENU_AREA`` in
:mod:`quill.core.lite.commands`), so splitting one changes what an area *is*
rather than how many there are -- and what a listener actually complained about
was not the granularity but having to *walk* the list. So the list is filtered
by typing (:class:`~quill.ui.app_features_dialog.AppFeaturesDialog`), and
:data:`PROFILES` is there for somebody who wants to say "the small one" rather
than tick eighteen boxes. Where the coarseness genuinely *hid* something --
Matches, Back/Forward, the Command Palette, Describe Character and text size all
belonged to no area at all -- the answer was more areas, not finer ones.

wx-free. The areas are data; honouring them is the menu builder's job.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.app_features import (
    AppArea,
    AppFeatureSettings,
    AppProfile,
    load_app_features,
    save_app_features,
)

__all__ = [
    "AREAS",
    "APP_ID",
    "DEFAULT_OFF",
    "PROFILES",
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
        "markup",
        "Markdown and HTML",
        "Insert > Markdown Tag and Insert > HTML Tag, and Format > Document "
        "Language. With this on, Bold, Italic, Underline and the heading keys "
        "write markup in a .md or .html file instead of refusing -- two "
        "asterisks, or a <strong>. Turn it off to keep those keys meaning rich "
        "text and nothing else. The caret still says what list you are in "
        "either way: that is a separate switch, on Ctrl+Alt+F5.",
    ),
    AppArea(
        "bookmarks",
        "Bookmarks",
        "Nine numbered places you can jump back to, and the list that shows them.",
    ),
    AppArea(
        "tools",
        "Line tools and change case",
        "Edit > Lines: move, duplicate, join and delete whole lines, sort and "
        "reverse and number them, remove blanks and duplicates, trim trailing "
        "spaces, and Tools > Change Case. Indenting stays either way -- an "
        "editor that cannot indent is broken rather than small, and so is one "
        "that cannot choose an encoding, which is why File Encoding and Line "
        "Endings stays too.",
    ),
    AppArea(
        "clipboard",
        "Copy Tray and the clip library",
        "Edit > Clipboard: numbered clipboard slots, a collector that gathers "
        "several copies into one, and a rolling history of everything you have "
        "copied. Cut, Copy, Paste and Paste Text Only stay available either "
        "way.",
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
        "own list unless you ask it to share QUILL's in Preferences. This is "
        "the same switch as Tools > Expand Abbreviations (Alt+Shift+A), which "
        "is the quick way to reach it while you are typing.",
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
        "Tools > Spelling: check as you type, and review the whole document "
        "with F7. "
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
    AppArea(
        "matches",
        "The Matches submenu",
        "Edit > Matches: list every occurrence of what you searched for in one "
        "window, and count them. Find, Find Next and Replace stay available "
        "either way -- this is the part that answers 'how many' and 'where "
        "else' rather than 'take me to the next one'.",
    ),
    AppArea(
        "history",
        "Go Back and Go Forward",
        "A trail of the places you jumped from, so Go Back returns you after a "
        "heading jump, a bookmark or a Go To Line. Notepad has no such thing; "
        "it is here because a listener cannot glance back at where they were.",
    ),
    AppArea(
        "command_palette",
        "The Command Palette",
        "Ctrl+Shift+P: type part of a command's name and run it without finding "
        "it in a menu. Every command it lists is in a menu as well, so this is "
        "a faster front door rather than the only one.",
    ),
    AppArea(
        "character_info",
        "Describe Character",
        "Say what the character under the cursor is -- the difference between a "
        "hyphen, an en dash and a minus sign, or which of the several spaces "
        "this one is -- and a details window with its name and code point. A "
        "screen reader reads most of these identically, which is why the "
        "editor has to be able to tell you.",
    ),
    AppArea(
        "zoom",
        "Text size",
        "Make the text bigger or smaller, and reset it. This is the on-screen "
        "size only; it changes nothing about the file and nothing about what a "
        "screen reader says.",
    ),
)

#: Areas that start disabled. Everything else starts enabled, because
#: AppFeatureSettings stores only explicit "off".
DEFAULT_OFF: frozenset[str] = frozenset({"autoformat", "backups", "go_to_anything"})

#: Named starting points, so somebody can ask for "the small one" without
#: ticking eighteen boxes. Applying one sets every box and then the boxes are
#: the truth again -- there is no mode to escape from, and the next change is an
#: ordinary override. Written as what each profile takes *away*, so an area
#: added later is on in all four until somebody says otherwise.
#:
#: The two named after other people's programs are named after them on purpose.
#: "Notepad" and "WordPad" say in one word what a paragraph of feature names
#: cannot, and they are the two products somebody arriving at QuillLite is most
#: likely to be replacing.
#:
#: They are also the only two that carry a *setting*, and for the same reason:
#: those names promise what the thing you type in **is**, not merely which menus
#: exist. A Notepad profile that removed the Format menu and still made a rich
#: text document on Ctrl+N would keep the letter of its name and break its
#: promise, and the user would find out one document later -- at the Save As
#: dialog, offering a format they thought they had turned off. Recommended and
#: Everything claim nothing here, because they are statements about which areas
#: exist and have no opinion about the rest.
PROFILES: tuple[AppProfile, ...] = (
    AppProfile(
        "recommended",
        "Recommended",
        "What a new install is: 15 of the 18 areas on. The three "
        "left off are the ones that would be wrong on by default rather than "
        "merely unused -- autocorrect rewriting a configuration file's quotes, "
        "backups quietly filling a folder, and a second 'go to' front door "
        "before anyone asked for one. Everything else is here, including rich "
        "text, spell check, the line tools and the clipboard. Choose this to "
        "get back to the shipped answer after experimenting.",
        frozenset(DEFAULT_OFF),
    ),
    AppProfile(
        "everything",
        "Everything",
        "All 18 areas on, including the three a new install leaves off. "
        "Autocorrect will straighten your quotes and capitalise your sentences, "
        "every save keeps a dated copy, and Go To Anything joins the command "
        "palette and the two lists as a fourth way to jump. Choose this if you "
        "would rather turn things off as they annoy you than find them one at a "
        "time.",
        frozenset(),
    ),
    AppProfile(
        "wordpad",
        "WordPad",
        "What WordPad was: rich text you can format, print and check the "
        "spelling of -- bold, italic, headings, alignment, bullets and line "
        "spacing -- and none of the writing tools behind them. No line "
        "operations, no clipboard history, no bookmarks, no abbreviations, no "
        "command palette. Ctrl+N makes a rich text document, which is the half "
        "of this name a list of menus cannot say. Five of the 18 areas, "
        "plus a spell checker WordPad never had.",
        frozenset({
            "abbreviations",
            "autoformat",
            "backups",
            "bookmarks",
            "character_info",
            "clipboard",
            "command_palette",
            "go_to_anything",
            "history",
            "markup",
            "matches",
            "selection",
            "tools",
        }),
        # Rich text is what WordPad is, so Ctrl+N makes one.
        settings=(("default_mode", "rich"),),
    ),
    AppProfile(
        "notepad",
        "Notepad",
        "The smallest QuillLite gets, and the one most people are replacing "
        "something with. Two of the 18 areas: printing and text size. No "
        "Format menu, no headings, no bookmarks, no line tools, no clipboard "
        "history, no spell check -- nothing Notepad does not have, which is the "
        "point of choosing it. Ctrl+N makes a plain text document. What stays "
        "that Notepad users will not expect: File Encoding and Line Endings, "
        "because getting a file to save back exactly as it arrived is most of "
        "what a Notepad replacement is for, and Find, Replace and Go To Line, "
        "which Notepad has had since 1985.",
        frozenset({
            "abbreviations",
            "autoformat",
            "backups",
            "bookmarks",
            "character_info",
            "clipboard",
            "command_palette",
            "go_to_anything",
            "headings",
            "history",
            # Markdown bold in a .md would be a genuine improvement on Notepad,
            # which is exactly why it is off here: this profile's promise is
            # "nothing Notepad does not have", and a profile that quietly keeps
            # the good extra is a profile whose name has stopped being true.
            # Recommended has it on, and is one click away.
            "markup",
            "matches",
            "rich_text",
            "selection",
            "spelling",
            "tools",
        }),
        # Turning the Format menu off is only half of "Notepad": the other half
        # is that what Ctrl+N makes is a plain text file. Without this the
        # profile would remove every way to *apply* formatting and still create
        # documents that carry it, and the Save As dialog would go on offering
        # rich text formats to somebody who chose Notepad.
        settings=(("default_mode", "plain"),),
    ),
)

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
