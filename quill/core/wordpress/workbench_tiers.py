"""How much every WordPress Workbench command changes, row or no row (how.md review 1).

The context menus carry each command's tier (:data:`WORDPRESS_ACTIONS`), but
a command run from the menu bar, a key or a node acts with no row of its own
kind selected, and the access check used to find no tier for it and let it
through: Empty Spam, New Here and the imports ran under Read Only. This
module answers for every command:

- :func:`tier_of`: the tier from the context menus (the highest any row type
  gives it), or from :data:`MENU_TIERS` for a command only the menu bar has,
  or READ for one of :data:`READ_ONLY_VERBS`. ``None`` means unclassified,
  which ``tests/unit/core/wordpress/test_wp_workbench_tiers.py`` fails on, so
  a new command cannot forget to say what it changes.
- :func:`effective_command`: what Delete and Shift+Delete really run on a row
  (Remove on a person, Revoke on an application password, a plugin's own
  trash), so they are checked as that command and not as Move to Trash.

Wx-free.
"""

from __future__ import annotations

from quill.core.wordpress.workbench_plugin_actions import PLUGIN_TRASH
from quill.core.wordpress.workbench_window_menu import PREFIX, command
from quill.core.workbench.actions import ActionTable, Tier

__all__ = ["MENU_TIERS", "READ_ONLY_VERBS", "effective_command", "tier_of"]

#: Commands only the menu bar has that change the site.
MENU_TIERS: dict[str, Tier] = {
    command("empty_spam"): Tier.DESTRUCTIVE,
    command("empty_comment_trash"): Tier.DESTRUCTIVE,
    command("import_posts"): Tier.WRITE,
    command("import_folder"): Tier.WRITE,
    command("import_wxr"): Tier.WRITE,
    command("import_platform"): Tier.WRITE,
    command("plain_batch"): Tier.WRITE,
    command("restore_snapshot"): Tier.WRITE,
    command("your_profile"): Tier.WRITE,
}

#: Commands only the menu bar has that read, or change only this computer.
#: The REST Console and a saved request open here; a write they send is
#: checked when it is sent. Undo is the history's, checked by the change itself.
READ_ONLY_VERBS: frozenset[str] = frozenset({
    "access",
    "archive_static",
    "comment_counts",
    "compare_sites",
    "export_list",
    "export_wxr",
    "filter_builder",
    "forget_saved",
    "hide_like",
    "history",
    "only_mine",
    "options",
    "practice",
    "read_site",
    "rest_console",
    "run_saved",
    "scope",
    "show_only",
    "site_sets",
    "site_sheet",
    "snapshot",
    "undo",
    "view_as",
})

#: Delete and Shift+Delete on these rows run another command.
_LIST_KEY_COMMANDS: dict[str, str] = {
    "user": command("remove_user"),
    "app_password": command("revoke"),
}


def effective_command(command_id: str, row_kind: str) -> str:
    """The command Delete (trash) or Shift+Delete really runs on a *row_kind* row."""
    verb = command_id.removeprefix(PREFIX)
    if verb not in ("trash", "delete_permanently"):
        return command_id
    if row_kind in _LIST_KEY_COMMANDS:
        return _LIST_KEY_COMMANDS[row_kind]
    if verb == "trash" and row_kind in PLUGIN_TRASH:
        return command(PLUGIN_TRASH[row_kind].removeprefix("do_"))
    return command_id


def tier_of(command_id: str, actions: ActionTable) -> Tier | None:
    """How much *command_id* changes, whatever row is selected (``None``: unclassified)."""
    if command_id in MENU_TIERS:
        return MENU_TIERS[command_id]
    tiers = [
        row.tier
        for kind in actions.row_types_offering(command_id)
        for row in actions.rows_for(kind)
        if row.command_id == command_id
    ]
    if tiers:
        return max(tiers)
    if command_id.removeprefix(PREFIX) in READ_ONLY_VERBS:
        return Tier.READ
    return None
