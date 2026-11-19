"""Why each editor WordPress command without a key has none (rule 8, review item 37).

The rule 8 gate (``tests/unit/core/test_family_rules_and_gates.py``) used to see
only :data:`quill.core.keymap.DEFAULT_KEYMAP`, and the WordPress rows that are
not on the WordPress layer (``menu.py`` :data:`~quill.core.wordpress.menu.LAYER_KEYS`)
were never in it, so dozens of commands had neither a key nor a reason and
nothing noticed. The gate now walks :func:`~quill.core.wordpress.menu.all_rows`
too, and every row without a layer key needs a line here.

The reasons are by kind, because the argument is the same within a kind and a
separate sentence per command would be seventy places for it to rot. Each is a
"reached another way" reason (the family's second kind): the row's menu, the
Command Palette and, for a site's own things, the Workbench, where the Workbench
keys work. A command that earns a key later loses its line, and the gate says so.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["UNBOUND_WORDPRESS", "unbound_reason"]

_SITE_WINDOW = (
    "Reached another way: a site window, opened from its menu row and the Command "
    "Palette, and the same things are in the Workbench (Ctrl+Alt+Shift+Grave, H), whose "
    "own keys work inside it. A few visits a month, not a few a minute (rule 9)."
)
_ONCE_A_DOCUMENT = (
    "Reached another way: its menu row in both editors, and the Command Palette. It is "
    "used once or twice a document, so a chord out of the editor's budget would be a "
    "second door to a room seldom entered (rule 9)."
)
_IN_THE_PAGE = (
    "Reached another way: its menu row in both editors, and the Command Palette. The "
    "WordPress layer has only J, Q and Z left, none of which these names teach, and a "
    "key that teaches nothing is not worth a letter (rule 9)."
)
_ACROSS_SITES = (
    "Reached another way: Tools > WordPress > Your Sites in both editors, the Command "
    "Palette, and the Workbench's Needs My Attention. Looked at now and then, by its "
    "nature (rule 9)."
)

_KINDS: Mapping[str, tuple[str, ...]] = {
    _SITE_WINDOW: (
        "abilities",
        "app_passwords",
        "ask_site",
        "comments",
        "fonts",
        "manage_terms",
        "menu_history",
        "menus",
        "page_order",
        "palette_report",
        "plugins",
        "previous_looks",
        "shop_orders",
        "sign_out",
        "site_check",
        "site_find_replace",
        "site_logo",
        "site_map",
        "site_settings",
        "site_space",
        "site_styles",
        "style_variations",
        "synced_patterns",
        "template_outline",
        "themes",
        "undo_site_fix",
        "users",
        "widgets",
        "check_site",
        "accessibility_statement",
        "library_alt_text",
        "regenerate_sizes",
        "download_design",
        "events_coming_up",
        "new_event",
    ),
    _ONCE_A_DOCUMENT: (
        "add_note",
        "block_settings",
        "bulk_edit",
        "captions",
        "custom_fields",
        "document_as_page",
        "download_writing",
        "duplicate",
        "edit_picture_on_site",
        "fix_link_text",
        "image_size",
        "in_short",
        "insert_block",
        "insert_from_library",
        "insert_icon",
        "insert_picture",
        "listening_version",
        "mark_language",
        "name_embeds",
        "notes",
        "paste_image",
        "picture_maker",
        "play_media_here",
        "plugin_fields",
        "preview_and_review",
        "preview_blocks",
        "publish_elsewhere",
        "send_document",
        "send_folder",
        "smaller_copy",
        "transcript",
        "upload_from_address",
        "upload_large_file",
        "visual_review",
    ),
    _IN_THE_PAGE: (
        "check_page",
        "hear_link",
        "insert_link",
        "next_block",
        "previous_block",
        "where_am_i",
    ),
    _ACROSS_SITES: ("coming_up", "what_changed"),
}

#: Command id -> why it has no key.
UNBOUND_WORDPRESS: dict[str, str] = {
    f"wordpress.{verb}": reason for reason, verbs in _KINDS.items() for verb in verbs
}


def unbound_reason(command_id: str) -> str:
    """Why *command_id* has no key ("" when it should have one)."""
    return UNBOUND_WORDPRESS.get(command_id, "")
