"""Where every WordPress command lives, as one table both editors build from.

Plan: wordpress.md 12 (Jeff, 2026-11-04). Commands go where Word users already
look for them. File > WordPress keeps only what is about a whole document or a
site; what you do *inside* a page joins Insert, Format, View and Edit; the
site's own upkeep is Tools > WordPress. The same placement in both editors:
QUILL builds its menus from :data:`PLACES` (``quill/ui/main_frame_wordpress.py``)
and QUILL Lite's command table is generated from it (:func:`lite_rows`), so the
two cannot drift, and every row names one shared handler in
:mod:`quill.ui.wordpress_commands`.

The rows exist whenever the WordPress feature is on. The ones in
:data:`DOCUMENT_ONLY` are enabled only while a WordPress document is in front;
elsewhere they are dimmed, and the handler itself says why when it is reached
another way (the Command Palette).

Format and Edit take their rows as a WordPress submenu rather than loose rows:
both menus are nearly full in QUILL Lite, and a row with no free access letter
there would have no route at all. Tools > WordPress has no access letter in
QUILL Lite's Tools for the same reason (Say Word Summary holds the W).

Keys: none yet. Of every Ctrl, Alt and Shift chord with a letter, a digit or
an F-key, only Ctrl+Alt+Shift+Q and R are free in both editors (2026-11-04
survey); the proposal is in wordpress.md section 19, waiting on Jeff.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

#: One command: (command id, menu title, shared handler on WordPressCommands).
Row = tuple[str, str, str]


@dataclass(frozen=True)
class Submenu:
    """A titled group of rows."""

    title: str
    rows: tuple[Row | Submenu | None, ...]


Entry = Row | Submenu | None

# --------------------------------------------------------------------------- #
# File > WordPress: the whole document, and the sites

WORDPRESS_ROWS: tuple[Entry, ...] = (
    ("wordpress.new_page", "New &Page...", "cmd_new_page"),
    ("wordpress.new_post", "&New Post...", "cmd_new_post"),
    ("wordpress.open", "&Open Page or Post...", "cmd_open"),
    ("wordpress.open_by_address", "Open by &Web Address...", "cmd_open_by_address"),
    ("wordpress.open_local_draft", "Open &Local Draft...", "cmd_open_local_draft"),
    None,
    ("wordpress.save_draft", "Save &Draft to Site", "cmd_save_draft"),
    ("wordpress.publish", "P&ublish or Update...", "cmd_publish"),
    ("wordpress.schedule", "Sch&edule Publish...", "cmd_schedule"),
    ("wordpress.open_on_site", "Open on S&ite", "cmd_open_on_site"),
    ("wordpress.copy_address", "Cop&y Address", "cmd_copy_address"),
    None,
    ("wordpress.properties", "P&roperties...", "cmd_properties"),
    ("wordpress.versions", "Previous &Versions...", "cmd_versions"),
    ("wordpress.compare", "Co&mpare with Site", "cmd_compare"),
    ("wordpress.trash", "Move to &Trash...", "cmd_trash"),
    None,
    ("wordpress.switch_site", "Switc&h Site...", "cmd_switch_site"),
    ("wordpress.sites", "&Sites...", "cmd_sites"),
    ("wordpress.connect", "Connect &a Site...", "cmd_connect"),
)

# --------------------------------------------------------------------------- #
# Inside a page: Insert, Format, View, Edit

INSERT_ROWS: tuple[Entry, ...] = (
    None,
    ("wordpress.insert_block", "WordPress &Block...", "cmd_insert_block"),
    (
        "wordpress.insert_from_library",
        "&Picture from the Media Library...",
        "cmd_insert_from_library",
    ),
    ("wordpress.insert_picture", "Picture from This &Computer...", "cmd_insert_picture"),
    ("wordpress.insert_link", "Li&nk to a Page on This Site...", "cmd_insert_link"),
    ("wordpress.picture_maker", "Make a Pictu&re...", "cmd_picture_maker"),
)

FORMAT_ROWS: tuple[Entry, ...] = (
    None,
    Submenu(
        "Word&Press",
        (
            ("wordpress.block_settings", "Block &Settings...", "cmd_block_settings"),
            ("wordpress.image_size", "Image Si&ze...", "cmd_image_size"),
            ("wordpress.mark_language", "Mark &Language...", "cmd_mark_language"),
        ),
    ),
)

VIEW_ROWS: tuple[Entry, ...] = (
    None,
    ("wordpress.blocks", "WordPress &Blocks...", "cmd_blocks_window"),
    ("wordpress.preview_blocks", "&Preview Blocks", "cmd_preview_blocks"),
    ("wordpress.play_media_here", "Play &Media Here", "cmd_play_media_here"),
)

EDIT_ROWS: tuple[Entry, ...] = (
    None,
    Submenu(
        "&WordPress",
        (
            ("wordpress.next_block", "&Next Block", "cmd_next_block"),
            ("wordpress.previous_block", "&Previous Block", "cmd_previous_block"),
            ("wordpress.where_am_i", "&Where Am I", "cmd_where_am_i"),
        ),
    ),
)

# --------------------------------------------------------------------------- #
# Tools > WordPress: checking the site, its media, and running it

MORE_MEDIA = Submenu(
    "M&ore Media",
    (
        ("wordpress.upload_files", "&Upload Files...", "cmd_upload_files"),
        (
            "wordpress.upload_from_address",
            "Upload from &Web Address...",
            "cmd_upload_from_address",
        ),
        ("wordpress.paste_image", "&Paste Image", "cmd_paste_image"),
        ("wordpress.smaller_copy", "Make a S&maller Copy...", "cmd_smaller_copy"),
        ("wordpress.site_logo", "Site L&ogo...", "cmd_site_logo"),
        ("wordpress.preview_and_review", "Previ&ew and Review...", "cmd_preview_and_review"),
        None,
        ("wordpress.captions", "Captions for &Video...", "cmd_captions"),
        ("wordpress.transcript", "&Transcript for Audio...", "cmd_transcript"),
        ("wordpress.listening_version", "Make a Listening Versio&n...", "cmd_listening_version"),
        ("wordpress.name_embeds", "Name Em&beds", "cmd_name_embeds"),
        ("wordpress.document_as_page", "Publish a &Document as a Page...", "cmd_document_as_page"),
    ),
)

MANAGE = Submenu(
    "&Manage",
    (
        ("wordpress.users", "&Users...", "cmd_users"),
        ("wordpress.app_passwords", "&Application Passwords...", "cmd_app_passwords"),
        ("wordpress.plugins", "P&lugins...", "cmd_plugins"),
        ("wordpress.themes", "T&hemes...", "cmd_themes"),
        ("wordpress.fonts", "&Fonts...", "cmd_fonts"),
        ("wordpress.synced_patterns", "S&ynced Patterns...", "cmd_synced_patterns"),
        None,
        ("wordpress.widgets", "&Widgets...", "cmd_widgets"),
        ("wordpress.site_map", "Site Ma&p...", "cmd_site_map"),
        ("wordpress.template_outline", "Template &Outline", "cmd_template_outline"),
        None,
        ("wordpress.bulk_edit", "&Bulk Edit...", "cmd_bulk_edit"),
        ("wordpress.page_order", "Page O&rder...", "cmd_page_order"),
        None,
        ("wordpress.sign_out", "S&ign Out This Site...", "cmd_sign_out"),
    ),
)

TOOLS_ROWS: tuple[Entry, ...] = (
    None,
    Submenu(
        "WordPress",
        (
            ("wordpress.check", "Check Before &Publishing...", "cmd_check"),
            ("wordpress.check_page", "Check &This Page", "cmd_check_page"),
            ("wordpress.check_site", "Check the &Whole Site...", "cmd_check_site"),
            ("wordpress.undo_site_fix", "&Undo Site Fix...", "cmd_undo_site_fix"),
            (
                "wordpress.site_find_replace",
                "Site-wide &Find and Replace...",
                "cmd_site_find_replace",
            ),
            (
                "wordpress.accessibility_statement",
                "Write an &Accessibility Statement...",
                "cmd_accessibility_statement",
            ),
            ("wordpress.palette_report", "Pa&lette Report", "cmd_palette_report"),
            ("wordpress.in_short", "In &Short...", "cmd_in_short"),
            None,
            ("wordpress.media_library", "Media Li&brary...", "cmd_media_library"),
            ("wordpress.alt_text_review", "Alt Te&xt Review...", "cmd_alt_text_review"),
            ("wordpress.visual_review", "&Visual Review...", "cmd_visual_review"),
            MORE_MEDIA,
            None,
            ("wordpress.comments", "&Comments...", "cmd_comments"),
            ("wordpress.manage_terms", "Categories and Ta&gs...", "cmd_manage_terms"),
            ("wordpress.menus", "Me&nus...", "cmd_menus"),
            ("wordpress.site_check", "Site Chec&k", "cmd_site_check"),
            ("wordpress.site_settings", "Site S&ettings...", "cmd_site_settings"),
            MANAGE,
        ),
    ),
)

#: Each editor menu that takes WordPress rows, with its QUILL Lite path.
#: File's rows sit in their own submenu; the others are appended at the end of
#: the menu, after a separator.
PLACES: dict[str, tuple[str, tuple[Entry, ...]]] = {
    "file": ("&File", (None, Submenu("&WordPress", WORDPRESS_ROWS))),
    "edit": ("&Edit", EDIT_ROWS),
    "view": ("&View", VIEW_ROWS),
    "insert": ("&Insert", INSERT_ROWS),
    "format": ("F&ormat", FORMAT_ROWS),
    "tools": ("&Tools", TOOLS_ROWS),
}

#: Commands about the page in front of you: enabled only in a WordPress
#: document (wordpress.md 12). The site-wide ones work from anywhere.
DOCUMENT_ONLY: frozenset[str] = frozenset({
    "cmd_save_draft",
    "cmd_publish",
    "cmd_schedule",
    "cmd_open_on_site",
    "cmd_copy_address",
    "cmd_properties",
    "cmd_versions",
    "cmd_compare",
    "cmd_trash",
    "cmd_insert_block",
    "cmd_insert_from_library",
    "cmd_insert_picture",
    "cmd_insert_link",
    "cmd_block_settings",
    "cmd_image_size",
    "cmd_mark_language",
    "cmd_blocks_window",
    "cmd_preview_blocks",
    "cmd_next_block",
    "cmd_previous_block",
    "cmd_where_am_i",
    "cmd_check",
    "cmd_alt_text_review",
    "cmd_in_short",
    "cmd_name_embeds",
    "cmd_listening_version",
})


def _walk(entries: tuple[Entry, ...], path: str) -> Iterator[tuple[str, Row]]:
    for entry in entries:
        if isinstance(entry, Submenu):
            yield from _walk(entry.rows, f"{path}|{entry.title}")
        elif entry is not None:
            yield path, entry


def all_rows() -> Iterator[tuple[str, Row]]:
    """Every command row with its QUILL Lite menu path ("&Tools|WordPress|&Manage")."""
    for top, entries in PLACES.values():
        yield from _walk(entries, top)


def spoken_path(path: str) -> str:
    """``"&Tools|WordPress"`` -> ``"Tools > WordPress"``, for docs and docstrings."""
    return " > ".join(part.replace("&", "") for part in path.split("|"))


def lite_handler(command_id: str) -> str:
    """QUILL Lite's handler for a row: ``wordpress.open`` -> ``cmd_wp_open``."""
    return "cmd_wp_" + command_id.split(".", 1)[1]


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
    """One place's rows in QUILL Lite's command-table shape.

    No keys (see the module docstring). Submenu titles become ``"sub"`` rows
    and their rows sit under ``parent|title``, which is how the Lite menu
    builder nests them.
    """
    top, entries = PLACES[place]
    return _lite(entries, top)


def lite_placed_rows() -> list[CommandRow]:
    """Every place but File, for the end of QUILL Lite's table (each menu's tail)."""
    return [row for place in PLACES if place != "file" for row in lite_rows(place)]


def submenu_paths() -> list[str]:
    """Every submenu path the rows sit under, for QUILL Lite's area map."""
    paths: list[str] = []
    for top, entries in PLACES.values():
        stack = [(top, entries)]
        while stack:
            path, rows = stack.pop()
            for entry in rows:
                if isinstance(entry, Submenu):
                    child = f"{path}|{entry.title}"
                    paths.append(child)
                    stack.append((child, entry.rows))
    return paths


def direct_handlers() -> list[str]:
    """Lite handlers sitting straight in an editor menu, not in a WordPress submenu."""
    return [lite_handler(row[0]) for path, row in all_rows() if "|" not in path]
