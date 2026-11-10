"""What can be done to each WordPress row, and the Workbench window's menu bar (PRD 6, 7, C).

:data:`WORDPRESS_ACTIONS` is section 7's context menus as the shared engine's
:class:`~quill.core.workbench.actions.ActionTable`: the default first (what
Enter does), the rows for that row type only, and Properties last. Each row
names the capability it needs (``requirement``), which the window checks
against ``users/me?context=edit`` before offering it (section 11), and its
tier, which decides how it is confirmed: Trash is tier 1 (undoable), a
change on the site tier 2, and Delete Permanently tier 3, never a bare key.

:data:`WINDOW_MENU` is the bar, checked by
:func:`quill.core.workbench.menus.problems` for the accelerator and
access-key rules. Keys follow Part C; the ones that must act only in the list
(Delete, Shift+Delete, Ctrl+Z) are :data:`LIST_KEYS`, which the window keeps
away from the filter box.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, ActionTable, Tier
from quill.core.workbench.menus import MenuRow, MenuSpec

__all__ = [
    "GO_NODES",
    "LIST_KEYS",
    "PREFIX",
    "PROPERTIES",
    "WINDOW_MENU",
    "WORDPRESS_ACTIONS",
    "command",
]

PREFIX = "wordpress.workbench."
PROPERTIES = f"{PREFIX}sheet"
LIST_KEYS = frozenset({"Delete", "Shift+Delete", "Ctrl+Z"})


def command(verb: str) -> str:
    return f"{PREFIX}{verb}"


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
            _SHEET,
        ),
        "media": (
            _a("open_on_site", "View or Play", default=True, help="Open the file in your browser."),
            _a("copy_link", "Copy Link", help="The file's address. Ctrl+Shift+C."),
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
            _SHEET,
        ),
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
                "send_password_reset",
                "Send Password Reset",
                needs="edit_users",
                help="Opens their wp-admin screen to send the reset email. Ctrl+Shift+W.",
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
            _SHEET,
        ),
        "theme": (
            _READ,
            _a(
                "activate_theme",
                "Activate...",
                tier=Tier.WRITE,
                needs="switch_themes",
                help="Make this the site's theme, after you confirm.",
            ),
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
        "form": (
            _a("show_entries", "Show Its Responses", default=True, help="The form's responses."),
            _SHEET,
        ),
        **{
            kind: (_READ, _SHEET)
            for kind in (
                "fact",
                "setting",
                "problem",
                "help",
                "namespace",
                "ability",
                "menu",
                "template",
                "pattern",
                "font",
                "sidebar",
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
            _SHEET,
        ),
    },
    properties_command=PROPERTIES,
)
"""Section 7's context menus, row type by row type."""


def _row(verb: str, label: str, key: str, help: str) -> MenuRow:  # noqa: A002 - field name
    return MenuRow(command(verb), label, key, help)


WINDOW_MENU: tuple[MenuSpec, ...] = (
    MenuSpec(
        "&File",
        (
            _row("new_here", "&New Here...", "Ctrl+N", "A new user or password, where you are."),
            _row("open_on_site", "Open on the &Site", "Shift+Enter", "The selection in a browser."),
            _row("preview", "Pre&view on the Site", "Ctrl+Enter", "Preview the selected item."),
            None,
            _row("close", "&Close Workbench", "Alt+F4", "Close this window. The editor stays."),
        ),
    ),
    MenuSpec(
        "&Edit",
        (
            _row("undo", "&Undo WordPress Change", "Ctrl+Z", "Put back the last change."),
            _row("history", "Change &History...", "Ctrl+Shift+H", "Every change made here."),
            None,
            _row("copy_link", "Copy &Link", "Ctrl+Shift+C", "Copy the selected row's address."),
            _row("filter", "&Filter...", "Ctrl+E", "Move to the filter box above the list."),
            _row(
                "filter_builder",
                "Filter &Builder...",
                "Ctrl+Shift+F",
                "Build a filter from this list's own attributes.",
            ),
            _row(
                "show_only",
                "Show &Only Like This...",
                "Ctrl+Alt+O",
                "Keep only rows like the selected one, by a column you choose.",
            ),
            _row(
                "hide_like",
                "Hi&de Like This...",
                "Ctrl+Alt+H",
                "Hide rows like the selected one, by a column you choose.",
            ),
            _row("only_mine", "Only &Mine", "Ctrl+Alt+M", "Only what you wrote, or all again."),
        ),
    ),
    MenuSpec(
        "&View",
        (
            _row("refresh", "&Refresh", "F5", "Load this view again from the site."),
            _row("load_more", "Load &More", "Ctrl+Shift+L", "Read three hundred more rows."),
            _row("load_all", "Load A&ll", "Ctrl+Alt+L", "Read every row the site has."),
            _row("columns", "&Columns...", "Ctrl+Alt+C", "Choose the columns this list shows."),
            _row("group_by", "&Group By...", "Ctrl+Alt+G", "A child node per value of a column."),
            None,
            _row("back", "&Back", "Alt+Left", "The view you were on before. Backspace too."),
            _row("forward", "&Forward", "Alt+Right", "The view you went back from."),
            None,
            _row("next_pane", "&Next Pane", "F6", "Tree, filter, list, details, status bar."),
            _row("previous_pane", "&Previous Pane", "Shift+F6", "The same panes, backwards."),
            None,
            _row("where_am_i", "&Where Am I", "Alt+1", "Say the node and the filter in effect."),
            _row("say_selection", "Say &Selection", "Alt+2", "Say how many rows are selected."),
        ),
    ),
    MenuSpec(
        "&Go",
        (
            _row("go_start", "&Start Here", "Ctrl+9", "What this window is and how it works."),
            _row("go_inbox", "&Needs My Attention", "Ctrl+1", "What needs you, on every site."),
            _row("go_site", "Current S&ite", "Ctrl+2", "The current site's overview."),
            _row("go_posts", "&Posts", "Ctrl+Shift+1", "This site's posts."),
            _row("go_pages", "P&ages", "Ctrl+Shift+2", "This site's pages."),
            _row("go_media", "&Media", "Ctrl+Shift+3", "This site's media."),
            _row("go_comments", "&Comments", "Ctrl+Shift+4", "This site's comments."),
            _row("go_users", "&Users", "Ctrl+Shift+5", "This site's people."),
            _row("go_plugins", "P&lugins", "Ctrl+Shift+6", "This site's plugins."),
            _row("go_appearance", "Appearanc&e", "Ctrl+Shift+7", "Themes, templates, patterns."),
            _row("go_settings", "Settin&gs", "Ctrl+Shift+8", "This site's settings."),
            _row("go_health", "Site &Health", "Ctrl+Shift+9", "This site's health checks."),
            None,
            _row("go_parent", "Paren&t Node", "Alt+Up", "The node above this one in the tree."),
        ),
    ),
    MenuSpec(
        "&Item",
        (
            MenuRow(PROPERTIES, "&Properties...", "Alt+Enter", "Everything about it on one sheet."),
            _row("publish", "P&ublish or Update...", "Ctrl+Shift+P", "Publish the selection."),
            _row("approve", "&Approve, or Not Spam", "Ctrl+Shift+A", "Approve, or release spam."),
            _row("unapprove", "U&napprove", "Ctrl+Shift+U", "Back to waiting."),
            _row("spam", "&Spam", "Ctrl+Shift+S", "Mark the selection as spam."),
            _row("reply", "&Reply...", "Ctrl+Shift+M", "Reply to the selected comment."),
            _row(
                "allow_sender",
                "Not Spam, and A&llow This Sender",
                "Ctrl+Alt+W",
                "Approve the comment and let this person's next ones through.",
            ),
            _row("merge_into", "&Merge Into...", "Ctrl+Shift+G", "Fold this term into another."),
            _row(
                "convert_term",
                "Con&vert to Category or Tag...",
                "Ctrl+Shift+K",
                "A tag becomes a category, or a category a tag.",
            ),
            _row(
                "send_password_reset",
                "Send Pass&word Reset",
                "Ctrl+Shift+W",
                "Open this person's wp-admin screen to send the reset email.",
            ),
            None,
            _row("trash", "Move to &Trash", "Delete", "Into WordPress's Trash; Restore undoes it."),
            _row("restore", "R&estore from Trash", "Ctrl+Shift+R", "Out of the Trash."),
            _row(
                "delete_permanently",
                "&Delete Permanently...",
                "Shift+Delete",
                "Gone for good, after you confirm by name.",
            ),
        ),
    ),
    MenuSpec(
        "&Site",
        (
            _row(
                "site_sheet", "Site &Properties...", "Alt+Shift+Enter", "The current site's sheet."
            ),
            _row("what_can_i_do", "&What Can I Do Here?", "Shift+F1", "What your role allows."),
            _row(
                "view_as", "&View As Role...", "Ctrl+Alt+V", "See the site as another role would."
            ),
            _row("access", "Workbench &Access...", "Ctrl+Alt+A", "Read Only, Organize or Full."),
            _row("roles", "&Roles and What They May Do", "Ctrl+Alt+R", "Each role in plain words."),
            _row(
                "empty_spam",
                "E&mpty Spam...",
                "Ctrl+Alt+E",
                "Delete every comment held as spam on this site, after you confirm.",
            ),
        ),
    ),
    MenuSpec(
        "&Window",
        (
            _row(
                "switch_to_editor",
                "Switch to &Editor",
                "Ctrl+Shift+E",
                "Bring forward the editor that opened this window.",
            ),
        ),
    ),
    MenuSpec(
        "&Help",
        (_row("help_view", "&Help for This View", "F1", "What this view and control do."),),
    ),
)
"""The bar, in order: File, Edit, View, Go, Item, Site, Window, Help."""

GO_NODES: dict[str, tuple[str, str]] = {
    command("go_start"): ("", "start"),
    command("go_inbox"): ("", "inbox"),
    command("go_site"): ("site", "overview"),
    command("go_posts"): ("site", "posts"),
    command("go_pages"): ("site", "pages"),
    command("go_media"): ("site", "media"),
    command("go_comments"): ("site", "comments"),
    command("go_users"): ("site", "users"),
    command("go_plugins"): ("site", "plugins"),
    command("go_appearance"): ("site", "themes"),
    command("go_settings"): ("site", "settings"),
    command("go_health"): ("site", "site_health"),
}
"""Where each Go row lands: (template, node key); a template node is the current site's."""
