"""The one level check every GitHub Workbench write passes (GitHub PRD 18.3.1, GH-R-060 to 066).

Each write command declares a tier (:mod:`quill.core.github.write_requirements`)
and each account has a Workbench level (Read Only, Organize or Full; Safe Mode
makes every account Read Only). This module answers, for one command, whether
the level allows it, and when it does not, says so in one sentence that names
the command, the level the account has, the level it needs and where that is
changed. The Workbench asks it once, where every command is dispatched
(``GitHubWorkbenchProvider.run``), and again only at the few doors that do not
go through the dispatcher: a Properties sheet's save and a sheet list's Add,
Change Role and Remove.

Never refused:

* a command that only reads (it declares no tier);
* a ``local`` write, which changes only this device's lists (favorites, pins,
  saved searches, the Workbench level itself) and sends nothing to GitHub;
* :data:`CHECKED_INSIDE`, a window whose writes are each checked as they are
  sent, so it still opens to read.

The sentence starts "Cannot", so the Workbench's outcome feedback treats it as
a failure: always spoken, with the error tone where sounds are on.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache

from quill.core.github.permissions import AccessLevel, WriteTier, level_allows, safe_mode_on
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS, EDITOR_REQUIREMENTS

__all__ = [
    "CHECKED_INSIDE",
    "WHERE_LEVEL_CHANGES",
    "command_refusal",
    "command_title",
    "gated_commands",
    "gated_tier",
    "needed_level",
    "refusal",
]

_P = "github.workbench."

#: Declared writes whose window opens to read and checks each write as it goes.
CHECKED_INSIDE: dict[str, str] = {
    f"{_P}api_console": (
        "A GET only reads; every other method needs Full and the method typed "
        "(quill.ui.github_api_console, _allowed_to_write)."
    ),
}

#: Where the account's level is changed, as the menus name it.
WHERE_LEVEL_CHANGES = "Account, Roles and Access, Workbench Level for This Account changes it"


def gated_tier(command_id: str) -> WriteTier | None:
    """The tier the level is checked against for *command_id*; None when it is never refused."""
    declared = COMMAND_REQUIREMENTS.get(command_id) or EDITOR_REQUIREMENTS.get(command_id)
    if declared is None or command_id in CHECKED_INSIDE:
        return None
    requirement, tier = declared
    return None if requirement == "local" else tier


def gated_commands() -> dict[str, WriteTier]:
    """Every command the level check can refuse, with its tier."""
    found: dict[str, WriteTier] = {}
    for command_id in (*COMMAND_REQUIREMENTS, *EDITOR_REQUIREMENTS):
        tier = gated_tier(command_id)
        if tier is not None:
            found[command_id] = tier
    return found


def needed_level(tier: WriteTier) -> AccessLevel:
    """The lowest level that allows *tier*: Organize for tiers 0 and 1, Full above."""
    return AccessLevel.ORGANIZE if level_allows(AccessLevel.ORGANIZE, tier) else AccessLevel.FULL


def refusal(what: str, tier: WriteTier, level: AccessLevel) -> str:
    """ "" when *level* allows *tier*; else one sentence: "Cannot *what*: it needs ..."."""
    if level_allows(level, tier):
        return ""
    needs = f"Cannot {what}: it needs {needed_level(tier).label} in the Workbench"
    if level is AccessLevel.READ_ONLY and safe_mode_on():
        return (
            f"{needs}, and QUILL is in Safe Mode, which keeps every account Read Only "
            "until QUILL is started normally."
        )
    return f"{needs}, and this account is {level.label}; {WHERE_LEVEL_CHANGES}."


def command_refusal(command_id: str, level: Callable[[], AccessLevel]) -> str:
    """ "" when *command_id* may run at the account's level; else why not, in one sentence.

    *level* is only called for a command that writes, so reading the stored
    level costs nothing on the many commands that only read.
    """
    tier = gated_tier(command_id)
    if tier is None:
        return ""
    return refusal(f"run {command_title(command_id)}", tier, level())


#: Names for writes with no menu row of their own: New Here in a list, a sheet
#: list's buttons, and the editor commands Repository Actions offers.
_OWN_TITLES: dict[str, str] = {
    **{
        f"{_P}{verb}": title
        for verb, title in (
            ("access_add", "Add Access"),
            ("access_change", "Change Role"),
            ("access_remove", "Remove Access"),
            ("create_team", "Create Team"),
            ("delete_team", "Delete Team"),
            ("new_issue", "New Issue"),
            ("new_tag", "New Tag"),
            ("new_star_list", "New Star List"),
            ("new_advisory", "New Advisory"),
            ("new_key", "New Key"),
            ("new_webhook", "New Webhook"),
            ("new_deploy_key", "New Deploy Key"),
            ("new_autolink", "New Autolink"),
            ("new_environment", "New Environment"),
            ("new_ruleset", "New Ruleset"),
            ("restore_package", "Restore Package"),
            ("new_runner", "New Runner"),
            ("resource_new", "New Here"),
            ("upload_sarif", "Upload SARIF"),
            ("codespace_new", "New Codespace"),
            ("pages_turn_on", "Turn On GitHub Pages"),
            ("new_workflow", "New Workflow"),
            ("compare_config", "Compare Configuration With Another Repository"),
        )
    },
    "github.fork_repository": "Fork Repository",
    "github.dispatch_workflow": "Dispatch Workflow",
    "github.create_release": "Create Release",
    "github.create_codespace": "Create Codespace",
    "github.rename_repository": "Rename Repository",
    "github.change_repository_visibility": "Change Visibility",
    "github.change_default_branch": "Change Default Branch",
    "github.configure_branch_protection": "Configure Branch Protection",
    "github.delete_branch": "Delete Branch",
    "github.commit_multiple_files": "Commit Multiple Files",
    "github.create_repository": "Create Repository",
}


def command_title(command_id: str) -> str:
    """The command's name as its menu row shows it, without the access key or the dots."""
    return _titles().get(command_id) or _OWN_TITLES.get(command_id) or _from_id(command_id)


def _from_id(command_id: str) -> str:
    words = command_id.rsplit(".", 1)[-1].replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def _clean(label: str) -> str:
    return label.split("\t", 1)[0].replace("&", "").replace("...", "").strip()


@cache
def _titles() -> dict[str, str]:
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.workbench_window_menu import WINDOW_MENU
    from quill.core.workbench.menus import all_rows

    titles: dict[str, str] = {}
    for kind in GITHUB_ACTIONS.row_types:
        for row in GITHUB_ACTIONS.rows_for(kind):
            titles.setdefault(row.command_id, _clean(row.label))
    for _menu, menu_row in all_rows(WINDOW_MENU):
        titles.setdefault(menu_row.command_id, _clean(menu_row.label))
    return {key: value for key, value in titles.items() if value}
