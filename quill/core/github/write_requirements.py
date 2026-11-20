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
from quill.core.github.quick_tables import QUICK_REQUIREMENTS

__all__ = ["COMMAND_REQUIREMENTS", "EDITOR_READS", "EDITOR_REQUIREMENTS", "requirement_for"]

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
    f"{_P}create_branch": ("repo:write", _V),
    f"{_P}edit_tasks": ("viewer:viewerCanUpdate", _V),
    f"{_P}convert_tasks": ("repo:triage", _V),
    f"{_P}clone": ("local", _O),
    f"{_P}close_reopen": ("viewer:viewerCanClose", _V),
    # Each item's own field write is checked again as it is sent (labels are
    # Organizing, state Visible); the sentence as a whole asks for Visible.
    f"{_P}plain_batch": ("repo:triage", _V),
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
    f"{_P}edit_title": ("viewer:viewerCanUpdate", _V),
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
    f"{_P}projects": ("scope:project", _O),
    f"{_P}react": ("sign_in", _O),
    f"{_P}remove_search": ("local", _O),
    f"{_P}pin_search": ("local", _O),
    f"{_P}unpin_search": ("local", _O),
    f"{_P}rerun": ("repo:write", _V),
    f"{_P}rerun_failed": ("repo:write", _V),
    f"{_P}run_workflow": ("repo:write", _V),
    f"{_P}snooze": ("local", _O),
    f"{_P}star": ("sign_in", _O),
    f"{_P}star_gist": ("sign_in+scope:gist", _O),
    f"{_P}start_worktree": ("local", _O),
    f"{_P}resolve_conflicts": ("local", _O),
    f"{_P}revert_pull": ("repo:write", _V),
    f"{_P}auto_merge": ("repo:write", _V),
    f"{_P}inbox_rules": ("sign_in", _O),
    f"{_P}practice": ("sign_in", _D),
    f"{_P}accept_invitation": ("sign_in", _A),
    f"{_P}decline_invitation": ("sign_in", _V),
    f"{_P}workflow_state": ("repo:write", _V),
    f"{_P}new_tag": ("repo:write", _V),
    f"{_P}delete_tag": ("repo:write", _D),
    f"{_P}transfer_repository": ("repo:admin", _D),
    f"{_P}unlink_branch": ("repo:write", _V),
    f"{_P}not_duplicate": ("repo:triage", _V),
    f"{_P}new_advisory": ("sign_in", _V),
    f"{_P}advisory_state": ("repo:admin", _D),
    f"{_P}request_cve": ("repo:admin", _V),
    f"{_P}new_key": ("sign_in", _V),
    f"{_P}delete_key": ("sign_in", _D),
    f"{_P}new_webhook": ("repo:admin", _V),  # or an organization owner, for its webhooks
    f"{_P}ping_webhook": ("repo:admin", _O),
    f"{_P}webhook_deliveries": ("repo:admin", _V),
    f"{_P}change_webhook": ("repo:admin", _V),
    f"{_P}delete_webhook": ("repo:admin", _D),
    f"{_P}new_deploy_key": ("repo:admin", _V),
    f"{_P}delete_deploy_key": ("repo:admin", _D),
    f"{_P}new_autolink": ("repo:admin", _V),
    f"{_P}delete_autolink": ("repo:admin", _D),
    f"{_P}sponsor": ("sign_in+scope:user", _D),
    f"{_P}cancel_sponsorship": ("sign_in+scope:user", _V),
    f"{_P}clone_wiki": ("local", _O),
    f"{_P}resource_new": ("sign_in", _V),
    f"{_P}resource_edit": ("sign_in", _V),
    f"{_P}resource_repositories": ("sign_in", _V),
    f"{_P}autofix_alert": ("repo:write+scope:security_events", _V),
    f"{_P}upload_sarif": ("repo:write+scope:security_events", _V),
    f"{_P}resource_delete": ("sign_in", _D),
    f"{_P}restore_package": ("sign_in+scope:delete:packages", _V),
    f"{_P}new_runner": ("repo:admin", _V),
    f"{_P}runner_labels": ("repo:admin", _O),
    f"{_P}remove_runner": ("repo:admin", _D),
    f"{_P}delete_package_version": ("sign_in+scope:delete:packages", _D),
    f"{_P}delete_package": ("sign_in+scope:delete:packages", _D),
    f"{_P}restore_package_version": ("sign_in+scope:write:packages", _V),
    **{
        f"{_P}{verb}": ("sign_in+scope:codespace", _V)
        for verb in (
            "codespace_new",
            "codespace_start",
            "codespace_stop",
            "codespace_machine",
            "codespace_export",
            "codespace_publish",
            "pull_codespace",
        )
    },
    f"{_P}codespace_delete": ("sign_in+scope:codespace", _D),
    f"{_P}react_release": ("sign_in", _O),
    f"{_P}rerun_job": ("repo:write", _V),
    f"{_P}manage_reviews": ("repo:write", _V),
    **{
        f"{_P}{verb}": ("scope:project", _V)
        for verb in (
            "project_draft",
            "project_field",
            "project_status",
            "project_link_repo",
            "project_unlink_repo",
            "project_template",
            "project_copy",
        )
    },
    f"{_P}project_field_delete": ("scope:project", _D),
    f"{_P}project_delete": ("scope:project", _D),
    f"{_P}org_roles": ("org:owner", _D),
    f"{_P}org_rulesets": ("org:owner", _D),
    f"{_P}pages_turn_on": ("repo:admin", _V),
    f"{_P}pages_rebuild": ("repo:admin", _V),
    f"{_P}pages_turn_off": ("repo:admin", _D),
    f"{_P}environment_secrets": ("repo:admin", _V),
    f"{_P}environment_variables": ("repo:admin", _V),
    f"{_P}environment_branch_policies": ("repo:admin", _D),
    f"{_P}environment_protection_rules": ("repo:admin", _D),
    f"{_P}environment_delete": ("repo:admin", _D),
    f"{_P}force_cancel_run": ("repo:write", _V),
    f"{_P}delete_run_logs": ("repo:write", _D),
    f"{_P}new_star_list": ("sign_in+scope:user", _O),
    f"{_P}star_lists": ("sign_in+scope:user", _O),
    f"{_P}edit_star_list": ("sign_in+scope:user", _V),
    f"{_P}user_status": ("sign_in+scope:user", _V),
    f"{_P}commit_status": ("repo:write", _V),
    f"{_P}merge_queue": ("repo:write", _V),
    f"{_P}merge_selected": ("repo:write", _V),
    # The wiki, and discussion to issue to pull request (GX12): github_workbench_collab.py.
    f"{_P}wiki_pages": ("local", _O),
    f"{_P}new_wiki_page": ("local", _O),
    f"{_P}publish_wiki": ("repo:write", _V),
    f"{_P}issue_from_discussion": ("sign_in", _V),
    f"{_P}pull_for_issue": ("repo:write", _V),
    f"{_P}sub_issues": ("repo:triage", _O),
    f"{_P}relationships": ("repo:triage", _O),
    f"{_P}issue_fields": ("repo:triage", _O),
    f"{_P}delete_release": ("repo:push", _D),
    f"{_P}gist_comments": ("sign_in+scope:gist", _V),
    f"{_P}fork_gist": ("sign_in+scope:gist", _V),
    f"{_P}delete_milestone": ("repo:triage", _D),
    f"{_P}delete_deployment": ("repo:push", _D),
    f"{_P}webhook_test_push": ("repo:admin", _O),
    f"{_P}webhook_on_off": ("repo:admin", _V),
    f"{_P}merge_into": ("repo:push", _V),
    f"{_P}repository_dispatch": ("repo:push", _V),
    f"{_P}delete_issue": ("repo:admin", _D),
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
    f"{_P}import_issues": ("sign_in", _V),
    f"{_P}issues_from_lines": ("sign_in", _V),
    # Templates (PRD 21.6): Save commits to the repository, or to the owner's
    # .github repository for an inherited default. Tier 1: visible to others.
    f"{_P}open_template": ("repo:write", _V),
    f"{_P}convert_template": ("repo:write", _V),
    f"{_P}copy_template": ("repo:write", _V),
    f"{_P}account_level": ("local", _O),
    f"{_P}bulk_access": ("repo:admin", _A),
    f"{_P}access_add": ("repo:admin", _A),
    f"{_P}access_change": ("repo:admin", _A),
    f"{_P}access_remove": ("repo:admin", _D),
    f"{_P}delete_team": ("org:owner", _D),
    f"{_P}create_team": ("org:member", _A),
    # Watches (PRD 22.5): this device's list only, nothing sent to GitHub.
    f"{_P}pause_watch": ("local", _O),
    f"{_P}remove_watch": ("local", _O),
    # The API Console (PRD 22.2) can send any write GitHub has, so it is held
    # to the top tier: Full access in the Workbench and the method typed first.
    f"{_P}api_console": ("sign_in", _D),
    # Across Repositories (PRD 22.11). Sets are this device's lists; the
    # by-name changes write to every repository in the set, each checked for
    # write access in its own preview step.
    f"{_P}across_edit_set": ("local", _O),
    f"{_P}across_set_filter": ("local", _O),
    f"{_P}across_new_set": ("local", _O),
    f"{_P}across_rename_set": ("local", _O),
    f"{_P}across_delete_set": ("local", _O),
    f"{_P}across_make_same": ("repo:write", _V),
    f"{_P}across_add_missing": ("repo:write", _V),
    f"{_P}across_rename_name": ("repo:write", _V),
    f"{_P}across_close_milestone": ("repo:write", _V),
    f"{_P}across_merge_label": ("repo:write", _D),
    f"{_P}across_delete_name": ("repo:write", _D),
    f"{_P}across_move_open": ("repo:write", _V),
    f"{_P}across_promote_org": ("org:owner+repo:admin", _D),
}


# The quick commands (quill/core/github/quick_tables.py) declare their own.
COMMAND_REQUIREMENTS.update(QUICK_REQUIREMENTS)

#: The editor's own GitHub commands the Workbench runs for you (Repository
#: Actions, New, the admin pages): the same declaration, so the Workbench's
#: level holds for them too (quill.core.github.write_gate).
EDITOR_REQUIREMENTS: dict[str, tuple[str, WriteTier]] = {
    "github.fork_repository": ("sign_in", _V),
    "github.dispatch_workflow": ("repo:write", _V),
    "github.create_release": ("repo:write", _V),
    "github.create_codespace": ("sign_in+scope:codespace", _V),
    "github.rename_repository": ("repo:admin", _A),
    "github.change_repository_visibility": ("repo:admin", _D),
    "github.change_default_branch": ("repo:admin", _A),
    "github.configure_branch_protection": ("repo:admin", _A),
    "github.delete_branch": ("repo:write", _D),
    "github.commit_multiple_files": ("repo:write", _V),
    "github.create_repository": ("sign_in", _V),
    "github.clone_repository": ("local", _O),
}

#: The editor commands the Workbench runs that only read or open a list.
EDITOR_READS: frozenset[str] = frozenset({
    "file.github_manage_accounts",
    "github.browse_organization",
    "github.list_codespaces",
    "github.view_security_alerts",
})


def requirement_for(command_id: str) -> tuple[str, WriteTier] | None:
    """What *command_id* needs and its tier, or None for a command that only reads."""
    return COMMAND_REQUIREMENTS.get(command_id)
