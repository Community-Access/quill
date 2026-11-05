"""Where every Forms command lives, as one table both editors build from.

Plan: wordpress.md 17a.10. The same placement in QUILL and QUILL Lite, the
WordPress table's shape (``quill/core/wordpress/menu.py``) so it is learned
once: New Form beside the other New rows in File; Form Field in Insert; Form
Outline in View; Form Rules in Format; and Check This Form, Fill It In
Yourself, Form Properties and Responses in Tools > Forms. QUILL builds its
menus from :data:`PLACES` (``quill/ui/main_frame_forms.py``) and QUILL Lite's
command table is generated from it (:func:`lite_rows`), so the two cannot
drift, and every row names one shared handler on
:class:`quill.ui.forms_commands.FormsCommands`.

The rows exist whenever the Forms feature is on. The ones in
:data:`DOCUMENT_ONLY` are enabled only while a form document is in front;
elsewhere they are dimmed, and the handler itself says why when it is reached
another way (the Command Palette).

**Access letters.** QUILL Lite's File, View and Format menus are nearly full.
New Form takes M in File (Close Window (MDI) gives it up: Ctrl+F4 is its
route), and Form Rules takes M in Format (Switch Document Mode gives it up:
Alt+Shift+F is its route), so each keeps a letter of its own name. Tools >
Forms has no letter in QUILL Lite's Tools, as Tools > WordPress has none: no
letter of either name is free there. QUILL seats its own letters
(``menu_routes.py``).

**Keys: none, each with its reason** (rule 8). No chord is free in both
editors and outside every family app's system-wide key that is not a menu
letter (Alt+letter), a caret key, an AltGr character on a European keyboard
(Ctrl+Alt+digit or punctuation) or a near miss for Alt+F4 -- the 2026-11
survey behind ``wordpress/menu.py`` found the same. Rule 9: writing a form is
occasional, so each command gets a way in (its menu letters and the Command
Palette), not a chord.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

#: One command: (command id, menu title, shared handler on FormsCommands).
Row = tuple[str, str, str]

#: A form document's file extension (wordpress.md 17a.4.1; Jeff chose ``.qaf``
#: in 17a.17, for QUILL Accessible Forms). What is inside is the QAF form
#: language, whose first line (``bfl 1``) is its version.
FORM_EXTENSION = ".qaf"

#: Extensions a form document may still have from before 17a.17. Read like a
#: ``.qaf`` file and never mentioned: New Form and the Save As filter only ever
#: offer :data:`FORM_EXTENSION`.
LEGACY_FORM_EXTENSIONS: tuple[str, ...] = (".bfl",)

#: Every extension a form document is recognised by.
FORM_EXTENSIONS: tuple[str, ...] = (FORM_EXTENSION, *LEGACY_FORM_EXTENSIONS)


def is_form_path(path: Path | str | None) -> bool:
    """Whether *path* names a form document (a ``.qaf`` file, or an older ``.bfl``)."""
    return bool(path) and str(path).lower().endswith(FORM_EXTENSIONS)


@dataclass(frozen=True)
class Submenu:
    """A titled group of rows."""

    title: str
    rows: tuple[Row | Submenu | None, ...]


Entry = Row | Submenu | None

#: File: after New Plain Text Document, with the other New rows.
FILE_ROWS: tuple[Entry, ...] = (("forms.new_form", "New For&m...", "cmd_new_form"),)

#: Insert, View and Format: one row each, at the foot of the menu.
INSERT_ROWS: tuple[Entry, ...] = (
    None,
    ("forms.insert_field", "Form &Field...", "cmd_insert_field"),
)
VIEW_ROWS: tuple[Entry, ...] = (None, ("forms.outline", "&Form Outline...", "cmd_outline"))
FORMAT_ROWS: tuple[Entry, ...] = (None, ("forms.rules", "For&m Rules...", "cmd_rules"))

#: Tools > Forms: checking it, trying it, its settings, and what people sent.
TOOLS_ROWS: tuple[Entry, ...] = (
    None,
    Submenu(
        "Forms",
        (
            ("forms.check", "&Check This Form...", "cmd_check"),
            ("forms.fill_in", "&Fill It In Yourself...", "cmd_fill_in"),
            ("forms.properties", "Form &Properties...", "cmd_properties"),
            None,
            ("forms.publish", "P&ublish Form...", "cmd_publish_form"),
            ("forms.insert_into_page", "&Insert Form Into Page...", "cmd_insert_into_page"),
            ("forms.test_on_site", "&Test on Site", "cmd_test_on_site"),
            ("forms.responses", "&Responses...", "cmd_form_responses"),
            None,
            ("forms.save_web_page", "Save As &Web Page...", "cmd_save_web_page"),
            ("forms.save_word", "Save As Wor&d Document...", "cmd_save_word"),
            ("forms.save_large_print", "Save As &Large Print...", "cmd_save_large_print"),
            ("forms.save_braille", "Save As &Braille-Ready Text...", "cmd_save_braille"),
            None,
            ("forms.draft", "Dr&aft a Form...", "cmd_draft_form"),
            ("forms.plain_language", "Plain Lan&guage...", "cmd_plain_language"),
            ("forms.suggest_autofill", "Suggest Autofill &Hints...", "cmd_suggest_autofill"),
        ),
    ),
)

#: Each editor menu that takes Forms rows, with its QUILL Lite path. File's row
#: goes after New Plain Text Document; the others at the end of their menu.
PLACES: dict[str, tuple[str, tuple[Entry, ...]]] = {
    "file": ("&File", FILE_ROWS),
    "insert": ("&Insert", INSERT_ROWS),
    "view": ("&View", VIEW_ROWS),
    "format": ("F&ormat", FORMAT_ROWS),
    "tools": ("&Tools", TOOLS_ROWS),
}

#: Commands about the form in front of you: enabled only in a form document.
#: New Form starts one; Responses will list a site's forms (17a.8).
DOCUMENT_ONLY: frozenset[str] = frozenset({
    "cmd_insert_field",
    "cmd_outline",
    "cmd_rules",
    "cmd_check",
    "cmd_fill_in",
    "cmd_properties",
    "cmd_publish_form",
    "cmd_test_on_site",
    "cmd_save_web_page",
    "cmd_save_word",
    "cmd_save_large_print",
    "cmd_save_braille",
    "cmd_plain_language",
    "cmd_suggest_autofill",
})


def _walk(entries: tuple[Entry, ...], path: str) -> Iterator[tuple[str, Row]]:
    for entry in entries:
        if isinstance(entry, Submenu):
            yield from _walk(entry.rows, f"{path}|{entry.title}")
        elif entry is not None:
            yield path, entry


def all_rows() -> Iterator[tuple[str, Row]]:
    """Every command row with its QUILL Lite menu path ("&Tools|Forms")."""
    for top, entries in PLACES.values():
        yield from _walk(entries, top)


def spoken_path(path: str) -> str:
    """``"&Tools|Forms"`` -> ``"Tools > Forms"``, for docs and docstrings."""
    return " > ".join(part.replace("&", "") for part in path.split("|"))


def lite_handler(command_id: str) -> str:
    """QUILL Lite's handler for a row: ``forms.check`` -> ``cmd_forms_check``."""
    return "cmd_forms_" + command_id.split(".", 1)[1]


CommandRow = tuple[str, str, str, str, str]


def _lite(entries: tuple[Entry, ...], path: str) -> list[CommandRow]:
    rows: list[CommandRow] = []
    for entry in entries:
        if entry is None:
            rows.append((path, "", "", "", "sep"))
        elif isinstance(entry, Submenu):
            rows.append((path, entry.title, "", "", "sub"))
            rows.extend(_lite(entry.rows, f"{path}|{entry.title}"))
        else:
            rows.append((path, entry[1], "", lite_handler(entry[0]), ""))
    return rows


def lite_rows(place: str = "file") -> list[CommandRow]:
    """One place's rows in QUILL Lite's command-table shape (no keys: see above)."""
    top, entries = PLACES[place]
    return _lite(entries, top)


def lite_placed_rows() -> list[CommandRow]:
    """Every place but File, for the end of QUILL Lite's table (each menu's tail)."""
    return [row for place in PLACES if place != "file" for row in lite_rows(place)]


def submenu_paths() -> list[str]:
    """Every submenu path the rows sit under, for QUILL Lite's area map."""
    return [
        f"{top}|{entry.title}"
        for top, entries in PLACES.values()
        for entry in entries
        if isinstance(entry, Submenu)
    ]


def direct_handlers() -> list[str]:
    """Lite handlers sitting straight in an editor menu, not in the Forms submenu."""
    return [lite_handler(row[0]) for path, row in all_rows() if "|" not in path]
