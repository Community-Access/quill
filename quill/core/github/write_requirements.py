"""What every GitHub write needs, and its tier: the table GATE-GITHUB-PERM holds (PRD 18.2, 18.6).

Section 18.2: "every write declares what it needs". Editable sheet fields
declare it on their :class:`~quill.core.github.sheet_engine.Write`; the
Workbench's write *commands* (context-menu and Item rows) declare it here, in
the vocabulary :func:`quill.core.github.permissions.check` reads
(``repo:triage``, ``scope:gist``, ``sign_in``, ``local``), with the tier of
section 18.4. A command or field with neither fails
``tests/unit/core/workbench/test_github_perm_gate.py``; so does a tier that
disagrees with the action table's own, so menus, Shift+F1 and sheets cannot
disagree about what you may do.

``local`` marks a write that changes only the Workbench's own lists on this
device (favorites, pins, snoozes): no GitHub permission is involved.

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.permissions import WriteTier

__all__ = ["COMMAND_REQUIREMENTS", "requirement_for"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_P = "github.workbench."

COMMAND_REQUIREMENTS: dict[str, tuple[str, WriteTier]] = {
    f"{_P}approve_fork": ("repo:write", _A),
    f"{_P}assign_copilot": ("repo:write", _V),
    f"{_P}assignees": ("repo:triage", _O),
    f"{_P}cancel_run": ("repo:write", _V),
    f"{_P}clone": ("local", _O),
    f"{_P}close_reopen": ("viewer:viewerCanClose", _V),
    f"{_P}comment": ("sign_in", _V),
    f"{_P}delete_asset": ("repo:write", _D),
    f"{_P}delete_branch": ("repo:write", _D),
    f"{_P}delete_cache": ("repo:write", _D),
    f"{_P}delete_gist": ("sign_in+scope:gist", _D),
    f"{_P}delete_label": ("repo:write", _D),
    f"{_P}delete_run": ("repo:write", _D),
    f"{_P}dismiss_alert": ("repo:write+scope:security_events", _V),
    f"{_P}edit_label": ("repo:write", _O),
    f"{_P}edit_release": ("repo:write", _V),
    f"{_P}favorite": ("local", _O),
    f"{_P}follow": ("sign_in+scope:user:follow", _O),
    f"{_P}issue_type": ("repo:triage", _O),
    f"{_P}labels": ("repo:triage", _O),
    f"{_P}lock": ("repo:write", _V),
    f"{_P}mark_done": ("sign_in", _O),
    f"{_P}mark_read": ("sign_in", _O),
    f"{_P}merge": ("repo:write", _V),
    f"{_P}milestone": ("repo:triage", _O),
    f"{_P}open_codespaces": ("sign_in+scope:codespace", _V),
    f"{_P}pending_deployments": ("repo:write", _A),
    f"{_P}pin": ("repo:triage", _V),
    f"{_P}pin_repository": ("local", _O),
    f"{_P}react": ("sign_in", _O),
    f"{_P}remove_search": ("local", _O),
    f"{_P}rerun": ("repo:write", _V),
    f"{_P}rerun_failed": ("repo:write", _V),
    f"{_P}run_workflow": ("repo:write", _V),
    f"{_P}snooze": ("local", _O),
    f"{_P}star": ("sign_in", _O),
    f"{_P}star_gist": ("sign_in+scope:gist", _O),
    f"{_P}start_worktree": ("local", _O),
    f"{_P}sub_issues": ("repo:triage", _O),
    f"{_P}transfer": ("repo:write", _D),
    f"{_P}unsnooze": ("local", _O),
    f"{_P}unsubscribe": ("sign_in", _O),
    f"{_P}upload_asset": ("repo:write", _V),
    f"{_P}watch": ("sign_in", _O),
    # Rows of the bar that write (Edit, Account and the access tools).
    f"{_P}undo_change": ("local", _O),
    f"{_P}redo_change": ("local", _O),
    f"{_P}mark_all_read": ("sign_in", _O),
    f"{_P}save_search": ("local", _O),
    f"{_P}new_issue": ("sign_in", _V),
    f"{_P}account_level": ("local", _O),
    f"{_P}bulk_access": ("repo:admin", _A),
    f"{_P}access_add": ("repo:admin", _A),
    f"{_P}access_change": ("repo:admin", _A),
    f"{_P}access_remove": ("repo:admin", _D),
    f"{_P}delete_team": ("org:owner", _D),
    f"{_P}create_team": ("org:member", _A),
}


def requirement_for(command_id: str) -> tuple[str, WriteTier] | None:
    """What *command_id* needs and its tier, or None for a command that only reads."""
    return COMMAND_REQUIREMENTS.get(command_id)
