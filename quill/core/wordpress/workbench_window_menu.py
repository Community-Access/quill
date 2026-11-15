"""The WordPress Workbench window's menu bar, its keys and its Go row (PRD Part C).

Split from :mod:`quill.core.wordpress.workbench_actions` (GATE-11), which
re-exports everything here. :data:`WINDOW_MENU` is the bar, checked by
:func:`quill.core.workbench.menus.problems` for the accelerator and
access-key rules. Keys follow Part C; the ones that must act only in the list
(Delete, Shift+Delete, Ctrl+Z) are :data:`LIST_KEYS`, which the window keeps
away from the filter box and every other text control. :data:`WORDPRESS_KEYS`
is the window's ``APP_KEYMAPS`` entry, built from the bar so the two cannot
disagree. Wx-free.
"""

from __future__ import annotations

from quill.core.wordpress.workbench_gravity_actions import GRAVITY_ITEM_ROWS, GRAVITY_SUB
from quill.core.wordpress.workbench_site_files_actions import WXR_SUB
from quill.core.workbench.menus import MenuRow, MenuSpec, MenuSub, rows

__all__ = [
    "GO_NODES",
    "LIST_KEYS",
    "PREFIX",
    "PROPERTIES",
    "WINDOW_MENU",
    "WORDPRESS_KEYMAP_ID",
    "WORDPRESS_KEYS",
    "command",
]

PREFIX = "wordpress.workbench."
PROPERTIES = f"{PREFIX}sheet"
LIST_KEYS = frozenset({"Delete", "Shift+Delete", "Ctrl+Z"})


def command(verb: str) -> str:
    return f"{PREFIX}{verb}"


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
            None,
            _row("export_list", "E&xport List...", "Ctrl+Shift+X", "This list as Excel or CSV."),
            _row(
                "import_posts",
                "&Import Posts from a Spreadsheet...",
                "Ctrl+Shift+I",
                "Posts or pages from an Excel or CSV file, previewed row by row.",
            ),
            _row(
                "import_folder",
                "Import a Folder of Documen&ts...",
                "Ctrl+Alt+Shift+I",
                "Each Markdown, text or Word file in a folder as a draft, previewed file by file.",
            ),
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
    # Ctrl+1 to Ctrl+0 are this window's Go row (PRD Part C). Ctrl+3 is the
    # family's AI chord elsewhere (codex.md 10A.9); this window has no AI menu,
    # so it does nothing here and Calendar keeps it, as the GitHub Workbench's
    # Go row keeps all ten digits. Ctrl+4 and Ctrl+8 stay unbound. Decided
    # 2026-11-13; tests/unit/ui/test_main_frame_hosted_ai.py names the exemption.
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
            _row("go_across", "Acr&oss Sites", "Ctrl+0", "The same name on every site."),
            _row("go_calendar", "Calen&dar", "Ctrl+3", "Every site's content, by day."),
            _row("go_watches", "&Watches", "Ctrl+5", "What the Workbench watches for you."),
            _row("go_practice", "P&ractice Site", "Ctrl+6", "The WordPress site on this computer."),
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
                "approve_schedule",
                "Approve and S&chedule...",
                "Ctrl+Shift+D",
                "Publish what waits for review, now or at a time.",
            ),
            _row(
                "send_back",
                "Send &Back with a Note...",
                "Ctrl+Shift+B",
                "Back to draft, with a note.",
            ),
            _row("assign_reviewer", "Assi&gn a Reviewer...", "Ctrl+Shift+J", "Name a reviewer."),
            _row(
                "move_day",
                "Move to Another Da&y...",
                "Ctrl+Alt+Shift+D",
                "A new date and time, previewed in the site's time and yours.",
            ),
            _row("copy_to_site", "C&opy to Site...", "Ctrl+Shift+Y", "To another of your sites."),
            _row(
                "send_password_reset",
                "Send Pass&word Reset",
                "Ctrl+Shift+W",
                "Open this person's wp-admin screen to send the reset email.",
            ),
            _row(
                "show_comments",
                "Show &Its Comments",
                "Ctrl+Alt+Shift+M",
                "The selected post's comments, with how many it has.",
            ),
            *GRAVITY_ITEM_ROWS,
            GRAVITY_SUB,
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
            _row(
                "empty_comment_trash",
                "&Empty Comment Trash...",
                "Ctrl+Alt+Shift+E",
                "Delete every comment in this site's Trash, after you confirm.",
            ),
            _row(
                "comment_counts",
                "Comment &Counts",
                "Ctrl+Alt+Shift+C",
                "How many comments wait, are approved, are spam and are in the Trash.",
            ),
            _row(
                "your_profile",
                "&Your Profile...",
                "Ctrl+Alt+Shift+P",
                "Your own name, email, website, biography and language on this site.",
            ),
            None,
            _row("compare_sites", "Compare S&ites...", "Ctrl+Alt+K", "What differs from another."),
            _row("site_sets", "Site Se&ts...", "Ctrl+Alt+T", "Name a set of your sites."),
            _row("scope", "Across Sites Sc&ope...", "Ctrl+Alt+Y", "Every site, or one set."),
            _row(
                "snapshot", "Take a S&napshot...", "Ctrl+Alt+S", "Everything but media, saved here."
            ),
            _row(
                "restore_snapshot",
                "Put Bac&k from a Snapshot...",
                "Ctrl+Alt+Shift+S",
                "Set posts, pages, patterns and terms back to a snapshot, after a preview.",
            ),
            _row(
                "read_site",
                "Read Site as &Document",
                "Ctrl+Alt+D",
                "The pages as one document in the editor.",
            ),
        ),
    ),
    MenuSpec(
        "&Tools",
        (
            _row(
                "options",
                "Workbench &Options...",
                "Ctrl+Shift+O",
                "Choose which Watches the Workbench announces.",
            ),
            _row("rest_console", "&REST Console...", "Ctrl+Shift+T", "Any route on the site."),
            _row(
                "run_saved",
                "Run a Saved Re&quest...",
                "Ctrl+Alt+Q",
                "Open the REST Console with a request you saved; a read is sent at once.",
            ),
            MenuSub(
                "Sa&ved Requests",
                dynamic="rest_saved",
                help="The requests you saved from the REST Console, numbered 1 to 9.",
            ),
            _row(
                "forget_saved",
                "&Forget a Saved Request...",
                "Ctrl+Alt+Shift+F",
                "Remove a request from Saved Requests.",
            ),
            _row(
                "plain_batch",
                "Plain-&Language Batch...",
                "Ctrl+Alt+B",
                "Say a change in words; check the exact items it means, then send them.",
            ),
            _row(
                "practice", "&Practice Site...", "Ctrl+Alt+P", "Start, stop, connect or reset it."
            ),
            WXR_SUB,
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
        (
            _row("help_view", "&Help for This View", "F1", "What this view and control do."),
            _row(
                "glossary",
                "What &Is This?",
                "Alt+F1",
                "The WordPress word for this row, explained.",
            ),
            _row(
                "guide_chapter",
                "WordPress &Guide",
                "Ctrl+F1",
                "The WordPress and Forms guide, at the chapter for where you are.",
            ),
            _row(
                "search_help",
                "&Search Help...",
                "Ctrl+Shift+F1",
                "Type a few words to find a place, a command, a WordPress word or a task.",
            ),
            _row("keys", "Workbench &Keys", "Alt+Shift+F1", "Every key in this window."),
            None,
            _row("repeat_result", "Say &Last Result Again", "F9", "Say the last result again."),
            _row(
                "explain_result",
                "E&xplain That",
                "Shift+F9",
                "What the last result means and what you might do next.",
            ),
        ),
    ),
)
"""The bar, in order: File, Edit, View, Go, Item, Site, Tools, Window, Help."""

WORDPRESS_KEYMAP_ID = "wordpress_workbench"
"""The window's section of ``keymap.APP_KEYMAPS`` (the provider's ``keymap_id``)."""

WORDPRESS_KEYS: dict[str, str] = {row.command_id: row.key for _menu, row in rows(WINDOW_MENU)}
"""Every default key in the WordPress Workbench window: its ``APP_KEYMAPS`` entry.

Built from the bar, so the menu, the keyboard reference and a rebinding cannot
disagree. Delete, Shift+Delete and Ctrl+Z are here too; :data:`LIST_KEYS` keeps
them to the list, so a text box keeps its own editing.
"""

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
    command("go_across"): ("", "across"),
    command("go_calendar"): ("", "calendar"),
    command("go_watches"): ("", "watches"),
    command("go_practice"): ("", "practice"),
}
"""Where each Go row lands: (template, node key); a template node is the current site's."""
