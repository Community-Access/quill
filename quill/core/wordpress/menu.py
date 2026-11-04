"""File > WordPress, as one table both editors build their menus from (wordpress.md 12).

QUILL builds its submenu from these rows (``quill/ui/main_frame_wordpress.py``)
and QUILL Lite adds the same rows to its command table
(``quill/core/lite/commands.py``), so the two menus cannot drift: same order,
same names, same shared handler in :mod:`quill.ui.wordpress_commands`.

The everyday commands sit in File > WordPress itself; the rest are grouped in
four submenus (Blocks, Media, Checking, Running the Site), because a flat menu
of sixty rows is one a listener arrows through rather than one they use, and
twenty-six letters cannot give sixty rows an access key each.

Keys: none yet. Every chord the everyday commands would want is already taken
in one editor or the other (2026-11-04 survey: of Ctrl, Alt and Shift with a
letter, a digit or an F-key, only Ctrl+Alt+Shift+Q and R are free in both).
They are reached by File > WordPress, by the Alt path, and by the Command
Palette; the proposal is in wordpress.md section 19, waiting on Jeff.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

#: One command: (command id, menu title, shared handler on WordPressCommands).
Row = tuple[str, str, str]


@dataclass(frozen=True)
class Submenu:
    """A titled group of rows inside File > WordPress."""

    title: str
    rows: tuple[Row | None, ...]


Entry = Row | Submenu | None

BLOCKS = Submenu(
    "Blo&cks",
    (
        ("wordpress.insert_block", "&Insert Block...", "cmd_insert_block"),
        ("wordpress.next_block", "&Next Block", "cmd_next_block"),
        ("wordpress.previous_block", "&Previous Block", "cmd_previous_block"),
        ("wordpress.where_am_i", "&Where Am I", "cmd_where_am_i"),
        None,
        ("wordpress.blocks", "&Blocks...", "cmd_blocks_window"),
        ("wordpress.block_settings", "Block &Settings...", "cmd_block_settings"),
        ("wordpress.preview_blocks", "Pre&view Blocks", "cmd_preview_blocks"),
    ),
)

MEDIA = Submenu(
    "Media and &Files",
    (
        (
            "wordpress.insert_from_library",
            "Insert from Media &Library...",
            "cmd_insert_from_library",
        ),
        ("wordpress.insert_picture", "Insert Picture from This &Computer...", "cmd_insert_picture"),
        ("wordpress.paste_image", "&Paste Image", "cmd_paste_image"),
        ("wordpress.upload_files", "&Upload Files...", "cmd_upload_files"),
        (
            "wordpress.upload_from_address",
            "Upload from &Web Address...",
            "cmd_upload_from_address",
        ),
        None,
        ("wordpress.image_size", "Image Si&ze...", "cmd_image_size"),
        ("wordpress.smaller_copy", "Make a S&maller Copy...", "cmd_smaller_copy"),
        ("wordpress.alt_text_review", "&Alt Text Review...", "cmd_alt_text_review"),
        ("wordpress.picture_maker", "Pictu&re Maker...", "cmd_picture_maker"),
        ("wordpress.site_logo", "Site L&ogo...", "cmd_site_logo"),
        ("wordpress.visual_review", "Vi&sual Review...", "cmd_visual_review"),
        ("wordpress.preview_and_review", "Previ&ew and Review...", "cmd_preview_and_review"),
        None,
        ("wordpress.captions", "Captions for &Video...", "cmd_captions"),
        ("wordpress.transcript", "&Transcript for Audio...", "cmd_transcript"),
        ("wordpress.listening_version", "Make a Listening Versio&n...", "cmd_listening_version"),
        ("wordpress.name_embeds", "Name Em&beds", "cmd_name_embeds"),
        ("wordpress.document_as_page", "Publish a &Document as a Page...", "cmd_document_as_page"),
    ),
)

CHECKING = Submenu(
    "Chec&king",
    (
        ("wordpress.check", "Check Before &Publishing...", "cmd_check"),
        ("wordpress.check_page", "Check &This Page", "cmd_check_page"),
        ("wordpress.check_site", "Check the &Whole Site...", "cmd_check_site"),
        ("wordpress.undo_site_fix", "&Undo Site Fix...", "cmd_undo_site_fix"),
        ("wordpress.site_find_replace", "Site-wide &Find and Replace...", "cmd_site_find_replace"),
        None,
        (
            "wordpress.accessibility_statement",
            "Write an &Accessibility Statement...",
            "cmd_accessibility_statement",
        ),
        ("wordpress.palette_report", "Pa&lette Report", "cmd_palette_report"),
        ("wordpress.mark_language", "Mark Lan&guage...", "cmd_mark_language"),
        ("wordpress.in_short", "In &Short...", "cmd_in_short"),
    ),
)

RUNNING = Submenu(
    "Runnin&g the Site",
    (
        ("wordpress.comments", "&Comments...", "cmd_comments"),
        ("wordpress.menus", "&Menus...", "cmd_menus"),
        ("wordpress.widgets", "&Widgets...", "cmd_widgets"),
        ("wordpress.site_map", "Site Ma&p...", "cmd_site_map"),
        ("wordpress.template_outline", "Template &Outline", "cmd_template_outline"),
        ("wordpress.site_check", "Site Chec&k", "cmd_site_check"),
        ("wordpress.site_settings", "Site &Settings...", "cmd_site_settings"),
        None,
        ("wordpress.manage_terms", "Categories and &Tags...", "cmd_manage_terms"),
        ("wordpress.users", "&Users...", "cmd_users"),
        ("wordpress.app_passwords", "&Application Passwords...", "cmd_app_passwords"),
        ("wordpress.plugins", "P&lugins...", "cmd_plugins"),
        ("wordpress.themes", "T&hemes...", "cmd_themes"),
        ("wordpress.fonts", "&Fonts...", "cmd_fonts"),
        ("wordpress.synced_patterns", "S&ynced Patterns...", "cmd_synced_patterns"),
        ("wordpress.bulk_edit", "&Bulk Edit...", "cmd_bulk_edit"),
        ("wordpress.page_order", "Page O&rder...", "cmd_page_order"),
        None,
        ("wordpress.sign_out", "S&ign Out This Site...", "cmd_sign_out"),
    ),
)

#: File > WordPress, in order. ``None`` is a separator. One table, so the
#: menu, the palette and the accelerator map cannot disagree.
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
    ("wordpress.media_library", "Media Li&brary...", "cmd_media_library"),
    BLOCKS,
    MEDIA,
    CHECKING,
    RUNNING,
    None,
    ("wordpress.switch_site", "Switc&h Site...", "cmd_switch_site"),
    ("wordpress.sites", "&Sites...", "cmd_sites"),
    ("wordpress.connect", "Connect &a Site...", "cmd_connect"),
)


def all_rows() -> Iterator[tuple[str, Row]]:
    """Every command row with the submenu title it sits in ("" for the top)."""
    for entry in WORDPRESS_ROWS:
        if isinstance(entry, Submenu):
            for row in entry.rows:
                if row is not None:
                    yield entry.title, row
        elif entry is not None:
            yield "", entry


def lite_handler(command_id: str) -> str:
    """QUILL Lite's handler for a row: ``wordpress.open`` -> ``cmd_wp_open``."""
    return "cmd_wp_" + command_id.split(".", 1)[1]


def lite_rows(parent: str = "&File|&WordPress") -> list[tuple[str, str, str, str, str]]:
    """The rows in QUILL Lite's command-table shape, under *parent*.

    No keys: see the module docstring. Submenu titles become ``"sub"`` rows
    and their rows sit under ``parent|title``, which is how the Lite menu
    builder nests them.
    """
    # The submenu's own title row in File, after a separator. Alt+F, W, as in
    # QUILL: Print Preview gave up its W for T, which nothing else in File claims.
    top, _, title = parent.rpartition("|")
    rows: list[tuple[str, str, str, str, str]] = [
        (top, "", "", "", "sep"),
        (top, title, "", "", "sub"),
    ]
    for entry in WORDPRESS_ROWS:
        if entry is None:
            rows.append((parent, "", "", "", "sep"))
        elif isinstance(entry, Submenu):
            rows.append((parent, entry.title, "", "", "sub"))
            child = f"{parent}|{entry.title}"
            for row in entry.rows:
                if row is None:
                    rows.append((child, "", "", "", "sep"))
                else:
                    rows.append((child, row[1], "", lite_handler(row[0]), ""))
        else:
            rows.append((parent, entry[1], "", lite_handler(entry[0]), ""))
    return rows


def submenu_paths(parent: str = "&File|&WordPress") -> list[str]:
    """Every menu path the rows sit under, for QUILL Lite's area map."""
    return [parent] + [f"{parent}|{e.title}" for e in WORDPRESS_ROWS if isinstance(e, Submenu)]
