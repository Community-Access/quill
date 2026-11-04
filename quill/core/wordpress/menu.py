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

Keys: one layer, the same in both editors (wordpress.md 19, option 1, Jeff's
choice). Of every Ctrl, Alt and Shift chord with a letter, a digit or an
F-key, only Ctrl+Alt+Shift+Q and R were free in both editors, so the commands
share one prefix instead -- Ctrl+Alt+Shift+Grave, beside the QUILL key -- and
then one letter from :data:`LAYER_KEYS`. :mod:`quill.core.wordpress.keys` is
the layer; both editors' keymaps are built from this table.
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
    ("wordpress.custom_fields", "Custom &Fields...", "cmd_custom_fields"),
    ("wordpress.plugin_fields", "Plu&gin Fields...", "cmd_plugin_fields"),
    ("wordpress.versions", "Previous &Versions...", "cmd_versions"),
    ("wordpress.compare", "Co&mpare with Site", "cmd_compare"),
    ("wordpress.trash", "Move to &Trash...", "cmd_trash"),
    Submenu(
        "Send and &Copy",
        (
            ("wordpress.send_document", "Send This &Document to WordPress...", "cmd_send_document"),
            ("wordpress.publish_elsewhere", "&Publish to Another Site...", "cmd_publish_elsewhere"),
            ("wordpress.duplicate", "D&uplicate...", "cmd_duplicate"),
            ("wordpress.send_folder", "Send a &Folder as Drafts...", "cmd_send_folder"),
            ("wordpress.download_writing", "Download &My Writing...", "cmd_download_writing"),
        ),
    ),
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
    ("wordpress.add_note", "N&ote on This Block...", "cmd_add_note"),
    ("wordpress.picture_maker", "Make a Pictu&re...", "cmd_picture_maker"),
    ("wordpress.insert_icon", "WordPress &Icon...", "cmd_insert_icon"),
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
    ("wordpress.notes", "B&lock Notes...", "cmd_notes"),
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
            ("wordpress.hear_link", "&Hear Where a Link Goes", "cmd_hear_link"),
            ("wordpress.fix_link_text", "Fix &Link Text...", "cmd_fix_link_text"),
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
        ("wordpress.upload_large_file", "Upload a &Large File...", "cmd_upload_large_file"),
        ("wordpress.regenerate_sizes", "&Regenerate Sizes...", "cmd_regenerate_sizes"),
        ("wordpress.smaller_copy", "Make a S&maller Copy...", "cmd_smaller_copy"),
        (
            "wordpress.edit_picture_on_site",
            "Edit a Picture on the S&ite...",
            "cmd_edit_picture_on_site",
        ),
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
        ("wordpress.previous_looks", "Previous Loo&ks...", "cmd_previous_looks"),
        ("wordpress.site_space", "&Space Used", "cmd_site_space"),
        (
            "wordpress.download_design",
            "Download a Copy of the Site's &Design...",
            "cmd_download_design",
        ),
        None,
        ("wordpress.abilities", "AI Abili&ties...", "cmd_abilities"),
        ("wordpress.ask_site", "Ask th&e Site...", "cmd_ask_site"),
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
            (
                "wordpress.library_alt_text",
                "Alt Text for the Whole Lib&rary...",
                "cmd_library_alt_text",
            ),
            ("wordpress.visual_review", "&Visual Review...", "cmd_visual_review"),
            MORE_MEDIA,
            None,
            ("wordpress.comments", "&Comments...", "cmd_comments"),
            ("wordpress.manage_terms", "Categories and Ta&gs...", "cmd_manage_terms"),
            ("wordpress.menus", "Me&nus...", "cmd_menus"),
            ("wordpress.menu_history", "Menu &History...", "cmd_menu_history"),
            ("wordpress.site_check", "Site Chec&k", "cmd_site_check"),
            ("wordpress.site_settings", "Site S&ettings...", "cmd_site_settings"),
            Submenu(
                "&Design",
                (
                    ("wordpress.style_variations", "Style &Variations...", "cmd_style_variations"),
                    ("wordpress.site_styles", "Site &Styles...", "cmd_site_styles"),
                ),
            ),
            Submenu(
                "Plug&in Extras",
                (
                    ("wordpress.events_coming_up", "Events &Coming Up...", "cmd_events_coming_up"),
                    ("wordpress.new_event", "New &Event...", "cmd_new_event"),
                    ("wordpress.shop_orders", "Shop &Orders...", "cmd_shop_orders"),
                ),
            ),
            MANAGE,
            Submenu(
                "&Your Sites",
                (
                    ("wordpress.coming_up", "Coming &Up...", "cmd_coming_up"),
                    ("wordpress.what_changed", "&What Changed on My Sites...", "cmd_what_changed"),
                ),
            ),
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

#: The prefix that starts the WordPress keys, in both editors. Free in QUILL,
#: in QUILL Lite and in every family app's system-wide key (2026-11 survey).
LAYER_PREFIX = "Ctrl+Alt+Shift+Grave"

#: The WordPress keys: the key pressed after :data:`LAYER_PREFIX` -> command id.
#: A row's own access letter wherever it is free, so the menu teaches the key.
#: Where two rows want one letter the everyday one keeps it (rule 3): Publish
#: keeps P, so New Page takes G (paGe); Media Library keeps M, so Compare with
#: Site takes C; Switch Site keeps S, so Sites (the list, rule 9) takes Shift+S.
#: B, K, U and X give four Tools and View rows their own access letters.
LAYER_KEYS: dict[str, str] = {
    "G": "wordpress.new_page",
    "N": "wordpress.new_post",
    "O": "wordpress.open",
    "W": "wordpress.open_by_address",
    "L": "wordpress.open_local_draft",
    "D": "wordpress.save_draft",
    "P": "wordpress.publish",
    "E": "wordpress.schedule",
    "I": "wordpress.open_on_site",
    "Y": "wordpress.copy_address",
    "R": "wordpress.properties",
    "V": "wordpress.versions",
    "C": "wordpress.compare",
    "T": "wordpress.trash",
    "S": "wordpress.switch_site",
    "Shift+S": "wordpress.sites",
    "A": "wordpress.connect",
    "M": "wordpress.media_library",
    "B": "wordpress.blocks",
    "K": "wordpress.check",
    "U": "wordpress.upload_files",
    "X": "wordpress.alt_text_review",
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
    "cmd_play_media_here",
    "cmd_custom_fields",
    "cmd_add_note",
    "cmd_notes",
    "cmd_hear_link",
    "cmd_fix_link_text",
    "cmd_insert_icon",
    "cmd_publish_elsewhere",
    "cmd_plugin_fields",
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


def layer_chord(command_id: str) -> str:
    """``wordpress.open`` -> ``"Ctrl+Alt+Shift+Grave, O"``, or "" for a row with no key."""
    for key, owner in LAYER_KEYS.items():
        if owner == command_id:
            return f"{LAYER_PREFIX}, {key}"
    return ""


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
            rows.append((path, entry[1], layer_chord(entry[0]), lite_handler(entry[0]), ""))
    return rows


def lite_rows(place: str = "file") -> list[CommandRow]:
    """One place's rows in QUILL Lite's command-table shape.

    A row in :data:`LAYER_KEYS` carries its layer chord as its key
    (``"Ctrl+Alt+Shift+Grave, O"``); the rest have none. Submenu titles become ``"sub"`` rows
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
