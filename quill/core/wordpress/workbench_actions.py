"""What can be done to each WordPress row, and the Workbench window's menu bar (PRD 6, 7, C).

:data:`WORDPRESS_ACTIONS` is section 7's context menus as the shared engine's
:class:`~quill.core.workbench.actions.ActionTable`: the default first (what
Enter does), the rows for that row type only, and Properties last. Each row
names the capability it needs (``requirement``), which the window checks
against ``users/me?context=edit`` before offering it (section 11), and its
tier, which decides how it is confirmed: Trash is tier 1 (undoable), a
change on the site tier 2, and Delete Permanently tier 3, never a bare key.

:data:`WINDOW_MENU`, :data:`GO_NODES`, :data:`LIST_KEYS` and the window's
keymap live in :mod:`quill.core.wordpress.workbench_window_menu` (GATE-11)
and are re-exported here, where the window and the tests have always found them.
"""

from __future__ import annotations

from quill.core.wordpress.workbench_admin_actions import (
    ACROSS_ROWS,
    DASHBOARD_ROWS,
    MODEL_ROWS,
    PLUGIN_ROWS,
    PMPRO_ROWS,
    SETTING_ROWS,
    THEME_ROWS,
    USER_ROWS,
)
from quill.core.wordpress.workbench_dashboard_places import MENU_ROWS, dashboard_rows
from quill.core.wordpress.workbench_dashboard_places import NODE_ROWS as ADMIN_NODE_ROWS
from quill.core.wordpress.workbench_gap_actions import ITEM_VERSIONS, UPDATE_CHECK
from quill.core.wordpress.workbench_gravity_actions import (
    GRAVITY_BUILD_ROWS,
    GRAVITY_ENTRY_ROWS,
    GRAVITY_FEED_ROWS,
    GRAVITY_FORM_ROWS,
    GRAVITY_QAF_ROWS,
)
from quill.core.wordpress.workbench_parity_actions import ITEM_ROWS as PARITY_ITEM_ROWS
from quill.core.wordpress.workbench_parity_actions import MEDIA_ROWS as PARITY_MEDIA_ROWS
from quill.core.wordpress.workbench_parity_actions import NODE_ROWS as PARITY_NODE_ROWS
from quill.core.wordpress.workbench_places import places_rows
from quill.core.wordpress.workbench_plugin_actions import PLUGIN_ACTION_ROWS, QAF_FORM_ROWS
from quill.core.wordpress.workbench_qaf_spam_edit import QAF_SPAM_ROWS
from quill.core.wordpress.workbench_site_files_actions import MEDIA_ROWS as SITE_FILES_MEDIA_ROWS
from quill.core.wordpress.workbench_sweep_places import sweep_rows
from quill.core.wordpress.workbench_window_menu import (
    GO_NODES,
    LIST_KEYS,
    PREFIX,
    PROPERTIES,
    WINDOW_MENU,
    WORDPRESS_KEYMAP_ID,
    WORDPRESS_KEYS,
    command,
)
from quill.core.workbench.actions import ActionRow, ActionTable, Tier

__all__ = [
    "GO_NODES",
    "LIST_KEYS",
    "PREFIX",
    "PROPERTIES",
    "WINDOW_MENU",
    "WORDPRESS_ACTIONS",
    "WORDPRESS_KEYMAP_ID",
    "WORDPRESS_KEYS",
    "command",
]


def _a(
    verb: str,
    label: str,
    *,
    tier: Tier = Tier.READ,
    needs: str = "",
    help: str = "",  # noqa: A002 - field name
    default: bool = False,
) -> ActionRow:
    return ActionRow(command(verb), label, tier, needs, help, default)


_SHEET = _a("sheet", "Properties...", help="Everything about it on one sheet. Alt+Enter.")
_READ = _a("read", "Read in Full", default=True, help="Move to the details pane to read it.")
_TRASH = _a(
    "trash",
    "Move to Trash",
    tier=Tier.ORGANIZE,
    needs="delete",
    help="Into WordPress's Trash, where Restore brings it back. Delete.",
)
_RESTORE = _a(
    "restore",
    "Restore from Trash",
    tier=Tier.ORGANIZE,
    needs="edit",
    help="Out of the Trash, as a draft.",
)
_DELETE = _a(
    "delete_permanently",
    "Delete Permanently...",
    tier=Tier.DESTRUCTIVE,
    needs="delete",
    help="Gone for good, after you confirm by name. Shift+Delete.",
)
_OPEN_SITE = _a("open_on_site", "Open on the Site", help="In your browser. Shift+Enter.")
_COPY_TO_SITE = _a(
    "copy_to_site",
    "Copy to Site...",
    tier=Tier.WRITE,
    help="To another of your sites, after a preview. Ctrl+Shift+Y.",
)

WORDPRESS_ACTIONS = ActionTable(
    {
        "item": (
            _a(
                "open_in_editor",
                "Open in Editor",
                default=True,
                needs="edit",
                help="Open it in the editor to write. Enter.",
            ),
            _a("preview", "Preview on the Site", help="In your browser. Ctrl+Enter."),
            _a(
                "visual_review",
                "Visual Review...",
                help="The editor's Visual Review of this published page: it is captured, and "
                "described by your AI only after you say yes. Nothing on the site changes.",
            ),
            _a(
                "publish",
                "Publish or Update...",
                tier=Tier.WRITE,
                needs="publish",
                help="Make the selected items public, after a preview. Ctrl+Shift+P.",
            ),
            _TRASH,
            _RESTORE,
            _DELETE,
            _a("copy_link", "Copy Link", help="Its address on the site. Ctrl+Shift+C."),
            _COPY_TO_SITE,
            _a(
                "approve_schedule",
                "Approve and Schedule...",
                tier=Tier.WRITE,
                needs="publish",
                help="Publish it now or at a time you give. Ctrl+Shift+D.",
            ),
            _a(
                "send_back",
                "Send Back with a Note...",
                tier=Tier.WRITE,
                needs="edit",
                help="Back to draft, with a note for its writer. Ctrl+Shift+B.",
            ),
            _a(
                "assign_reviewer",
                "Assign a Reviewer...",
                tier=Tier.WRITE,
                needs="edit",
                help="A note naming who reviews it. Ctrl+Shift+J.",
            ),
            _a(
                "move_day",
                "Move to Another Day...",
                tier=Tier.WRITE,
                needs="edit",
                help="A new date and time, previewed in the site's time and yours. "
                "Ctrl+Alt+Shift+D.",
            ),
            _a(
                "show_comments",
                "Show Its Comments",
                help="Its comments, and how many it has. Ctrl+Alt+Shift+M.",
            ),
            ITEM_VERSIONS,
            *PARITY_ITEM_ROWS,
            _SHEET,
        ),
        "media": (
            _a("open_on_site", "View or Play", default=True, help="Open the file in your browser."),
            _a(
                "insert_picked",
                "Insert into the Document",
                help=(
                    "At the caret of the document Insert > Picture from the Media Library "
                    "came from; there, Enter does this."
                ),
            ),
            _a("copy_link", "Copy Link", help="The file's address. Ctrl+Shift+C."),
            _COPY_TO_SITE,
            *SITE_FILES_MEDIA_ROWS,
            *PARITY_MEDIA_ROWS,
            _DELETE,
            _SHEET,
        ),
        "comment": (
            _READ,
            _a(
                "approve",
                "Approve, or Not Spam",
                tier=Tier.ORGANIZE,
                needs="moderate_comments",
                help="Approve it; on a comment held as spam, Not Spam. Ctrl+Shift+A.",
            ),
            _a(
                "allow_sender",
                "Not Spam, and Allow This Sender",
                tier=Tier.ORGANIZE,
                needs="moderate_comments",
                help="Approve it and let this person's next comments through. Ctrl+Alt+W.",
            ),
            _a(
                "unapprove",
                "Unapprove",
                tier=Tier.ORGANIZE,
                needs="moderate_comments",
                help="Back to waiting. Ctrl+Shift+U.",
            ),
            _a(
                "spam",
                "Spam",
                tier=Tier.ORGANIZE,
                needs="moderate_comments",
                help="Mark it as spam, which the site's spam plugin learns from. Ctrl+Shift+S.",
            ),
            _a(
                "reply",
                "Reply...",
                tier=Tier.WRITE,
                needs="moderate_comments",
                help="Write a reply, posted as you. Ctrl+Shift+M.",
            ),
            _TRASH,
            _RESTORE,
            _DELETE,
            _SHEET,
        ),
        "form_entry": (
            _READ,
            _a(
                "approve",
                "Not Spam",
                tier=Tier.ORGANIZE,
                needs="forms",
                help="Back to the form's entries. Ctrl+Shift+A.",
            ),
            _a(
                "spam",
                "Spam",
                tier=Tier.ORGANIZE,
                needs="forms",
                help="Hold it as spam. Ctrl+Shift+S.",
            ),
            *GRAVITY_ENTRY_ROWS,
            _SHEET,
        ),
        "pmpro": (_READ, *PMPRO_ROWS, _SHEET),
        "term": (
            _a("show_posts", "Show Its Posts", default=True, help="The posts filed under it."),
            _a(
                "merge_into",
                "Merge Into...",
                tier=Tier.DESTRUCTIVE,
                needs="manage_categories",
                help="File its posts under another term, then delete it. Ctrl+Shift+G.",
            ),
            _a(
                "convert_term",
                "Convert to Category or Tag...",
                tier=Tier.DESTRUCTIVE,
                needs="manage_categories",
                help="Make a tag a category, or a category a tag, posts and all. Ctrl+Shift+K.",
            ),
            _COPY_TO_SITE,
            _DELETE,
            _SHEET,
        ),
        "user": (
            _a("show_posts", "Show Their Posts", default=True, help="The posts they wrote."),
            _a(
                "change_role",
                "Change Role...",
                tier=Tier.WRITE,
                needs="promote_users",
                help="Choose another role for this person.",
            ),
            _a(
                "pmpro_memberships",
                "Show Memberships...",
                help="Read this person's current and past Paid Memberships Pro memberships.",
            ),
            *USER_ROWS,
            _a(
                "send_password_reset",
                "Send Password Reset",
                needs="edit_users",
                help="Opens their wp-admin screen to send the reset email. Ctrl+Shift+W.",
            ),
            _a(
                "set_password",
                "Set New Password...",
                tier=Tier.WRITE,
                needs="edit_users",
                help="Give them a new sign-in password: a strong one is offered, then previewed.",
            ),
            _a("roles", "Roles and What They May Do", help="Each role in plain words. Ctrl+Alt+R."),
            _a(
                "remove_user",
                "Remove...",
                tier=Tier.DESTRUCTIVE,
                needs="delete_users",
                help="Remove this person, with their content given to someone else. Delete.",
            ),
            _SHEET,
        ),
        "plugin": (
            _READ,
            _a(
                "toggle_plugin",
                "Activate or Deactivate",
                tier=Tier.WRITE,
                needs="activate_plugins",
                help="Turn the plugin on or off, after you confirm.",
            ),
            *PLUGIN_ROWS,
            UPDATE_CHECK,
            _SHEET,
        ),
        "theme": (
            _READ,
            _a(
                "activate_theme",
                "Activate...",
                needs="switch_themes",
                help="REST cannot switch themes, so this opens Appearance > Themes in wp-admin.",
            ),
            *THEME_ROWS,
            UPDATE_CHECK,
            _SHEET,
        ),
        "app_password": (
            _READ,
            _a(
                "revoke",
                "Revoke...",
                tier=Tier.DESTRUCTIVE,
                help="Stop this password working, after you confirm. Delete.",
            ),
            _SHEET,
        ),
        "site": (
            _a("open_site", "Open This Site", default=True, help="Select its node in the tree."),
            _OPEN_SITE,
            *QAF_SPAM_ROWS,  # QUILL Accessible Forms' question bank and weeks (complete.md WP-C)
            _SHEET,
        ),
        "writing_type": (
            _a("open_kind", "Open Its List", default=True, help="Select its node in the tree."),
            _SHEET,
        ),
        "taxonomy": (
            _a("open_kind", "Open Its List", default=True, help="Select its node in the tree."),
            _SHEET,
        ),
        "namespace": (
            _a("open_namespace", "List Its Routes", default=True, help="Select its node. Enter."),
            _SHEET,
        ),
        "route": (
            _a("read_route", "Read It", default=True, help="Ask the site and read the answer."),
            _a("route_schema", "What It Accepts", help="Its arguments and fields, from the site."),
            _SHEET,
        ),
        "ability": (
            _a(
                "run_ability",
                "Run...",
                default=True,
                help="Fill in its input, see the preview, then run it. Enter.",
            ),
            _a(
                "offer_to_ask",
                "Offer to Ask the Site",
                help=(
                    "Turn on or off whether Ask the Site may suggest this ability. Kept on this "
                    "computer; QUILL still asks you before every run."
                ),
            ),
            _SHEET,
        ),
        "model": (_READ, *MODEL_ROWS, _SHEET),
        **PLUGIN_ACTION_ROWS,  # shop, events, SEO (workbench_plugin_actions)
        "update": (
            _a(
                "open_on_site",
                "Open Dashboard Updates in the Browser",
                default=True,
                help="Where WordPress shows and runs updates; REST cannot run them. Enter.",
            ),
            _a("read", "Read in Full", help="Move to the details pane to read it."),
            UPDATE_CHECK,
            _SHEET,
        ),
        **places_rows(_READ, _SHEET),
        **dashboard_rows(_READ, _SHEET),  # templates, Additional CSS, wp-admin screens
        **sweep_rows(_READ, _SHEET),
        "across": (*places_rows(_READ, _SHEET)["across"][:-1], *ACROSS_ROWS, _SHEET),
        "dashboard": (
            *DASHBOARD_ROWS,
            _a("read", "Read in Full", help="Move to the details pane to read it."),
            _SHEET,
        ),
        "setting": (_READ, *SETTING_ROWS, _SHEET),
        "day": (
            _a("open_day", "Open This Day", default=True, help="List what the day holds."),
            _SHEET,
        ),
        "search_result": (
            _a(
                "open_on_site",
                "Open Result on the Site",
                default=True,
                help="Open this result in your browser. Enter.",
            ),
            _SHEET,
        ),
        "global_style": (
            _READ,
            _a(
                "edit_global_style",
                "Change...",
                tier=Tier.WRITE,
                needs="edit_theme_options",
                help="Change this palette colour or font size after a preview.",
            ),
            _SHEET,
        ),
        "pattern": (_READ, _COPY_TO_SITE, _SHEET),
        "menu": (_READ, *MENU_ROWS, _COPY_TO_SITE, _SHEET),
        "form": (
            _a("show_entries", "Show Its Responses", default=True, help="The form's responses."),
            *QAF_FORM_ROWS,
            *GRAVITY_QAF_ROWS,
            _COPY_TO_SITE,
            _SHEET,
        ),
        "gravity_form": (
            _a("show_entries", "Show Its Responses", default=True, help="The form's responses."),
            _a(
                "change_gravity_field_type",
                "Change a Field Type...",
                tier=Tier.WRITE,
                needs="gravityforms_create_form",
                help=(
                    "Change a supported Gravity Forms control after reviewing a full-form preview."
                ),
            ),
            *GRAVITY_FORM_ROWS,
            *GRAVITY_BUILD_ROWS,
            _COPY_TO_SITE,
            _SHEET,
        ),
        "gravity_feed": (_READ, *GRAVITY_FEED_ROWS, _DELETE, _SHEET),
        "gravity_result": (_READ, _SHEET),
        **{
            kind: (_READ, _SHEET)
            for kind in (
                "fact",
                "problem",
                "help",
                "font",
                "mixed",
            )
        },
        "node": (
            _a("refresh", "Refresh", default=True, help="Load this view again. F5."),
            _a("new_here", "New Here...", tier=Tier.WRITE, help="Make something new here. Ctrl+N."),
            _a("load_more", "Load More", help="Read three hundred more rows. Ctrl+Shift+L."),
            _a("load_all", "Load All", help="Read every row the site has. Ctrl+Alt+L."),
            _a("columns", "Columns...", help="Choose the columns this list shows. Ctrl+Alt+C."),
            _a("group_by", "Group By...", help="A child node per value of a column. Ctrl+Alt+G."),
            _a("what_can_i_do", "What Can I Do Here?", help="What your role allows. Shift+F1."),
            *PARITY_NODE_ROWS,
            *ADMIN_NODE_ROWS,
            _SHEET,
        ),
    },
    properties_command=PROPERTIES,
)
"""Section 7's context menus, row type by row type."""
