"""What can be done to each kind of GitHub row: the Workbench's context menus as data.

GitHub PRD section 5. Each row type lists its commands in menu order: the
default first (what Enter does), Properties last, and every row about the
selected row only. The window shows about eight and puts the rest under
More (:meth:`ActionTable.menu_for`); the Item menu is the same rows, so
nothing is reachable only by right-clicking.

GitHub's own rules, tested beside this table: Codespaces only on a
repository, a branch or a pull request; the API rate limit on no row at all
(it lives in the Account menu and the status bar); and no default that
deletes, because Enter must never destroy anything.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, ActionTable, Tier

__all__ = [
    "CODESPACES_COMMAND",
    "CODESPACES_ROW_TYPES",
    "GITHUB_ACTIONS",
    "PROPERTIES_COMMAND",
    "RATE_LIMIT_COMMAND",
]

PROPERTIES_COMMAND = "github.workbench.properties"
CODESPACES_COMMAND = "github.workbench.open_codespaces"
RATE_LIMIT_COMMAND = "github.workbench.rate_limit"
CODESPACES_ROW_TYPES = frozenset({"repository", "branch", "pull_request"})

_R, _O, _W, _D = Tier.READ, Tier.ORGANIZE, Tier.WRITE, Tier.DESTRUCTIVE


def _a(
    verb: str,
    label: str,
    tier: Tier = _R,
    requirement: str = "",
    help: str = "",  # noqa: A002 - the field's name
    *,
    default: bool = False,
) -> ActionRow:
    return ActionRow(f"github.workbench.{verb}", label, tier, requirement, help, default)


def _default(verb: str, label: str, help: str) -> ActionRow:  # noqa: A002
    return _a(verb, label, _R, "", help, default=True)


_PROPERTIES = ActionRow(
    PROPERTIES_COMMAND,
    "Properties...",
    help="Everything about this item on one sheet. Alt+Enter opens it from anywhere.",
)
_COPY_LINK = _a("copy_link", "Copy Link", help="Copy the item's GitHub address.")
_OPEN_WEB = _a("open_on_github", "Open on GitHub", help="Open the item in your browser.")
_CODESPACES = ActionRow(
    CODESPACES_COMMAND,
    "Open in Codespaces...",
    _W,
    "sign_in",
    "Open GitHub's Codespaces page for this. Starting a Codespace can cost money, "
    "so QUILL asks first.",
)
_COMMENT = _a("comment", "Comment...", _W, "sign_in", "Write a comment and post it.")
_LABELS = _a("labels", "Labels...", _W, "triage", "Add or remove labels.")
_ASSIGNEES = _a("assignees", "Assignees...", _W, "triage", "Choose who it is assigned to.")
_REACT = _a("react", "React...", _O, "sign_in", "Add or remove a reaction.")
_TIMELINE = _a("timeline", "View Timeline...", help="Everything that happened to it, in order.")
_SUMMARIZE = _a("summarize", "Summarize Discussion", _R, "ai", "An AI summary of the thread.")
_WORKTREE = _a(
    "start_worktree",
    "Start in Local Worktree...",
    _O,
    "",
    "Make a branch and a local folder to work on it, and open them in the editor.",
)
_FAVORITE = _a("favorite", "Add to or Remove from Favorites", _O, "", "Keep it in Favorites.")
_COMMIT_COMMENTS = _a(
    "commit_comments", "Commit Comments...", help="Comments on the commit and its lines."
)

_ROWS: dict[str, tuple[ActionRow, ...]] = {
    "issue": (
        _default("open", "Open", "Read the issue and its comments in the details pane."),
        _COMMENT,
        _a(
            "close_reopen",
            "Close or Reopen...",
            _W,
            "triage",
            "Close it with a reason, or reopen it.",
        ),
        _LABELS,
        _ASSIGNEES,
        _COPY_LINK,
        _OPEN_WEB,
        _a("milestone", "Milestone...", _W, "triage", "Set or clear its milestone."),
        _REACT,
        _TIMELINE,
        _SUMMARIZE,
        _WORKTREE,
        _a("assign_copilot", "Assign to Copilot...", _W, "push", "Ask Copilot to work on it."),
        _a("lock", "Lock or Unlock Conversation...", _W, "triage", "Stop or allow new comments."),
        _a("pin", "Pin or Unpin Issue", _O, "triage", "Pin it to the top of the issues list."),
        _a("transfer", "Transfer Issue...", _W, "push", "Move it to another repository."),
        _a("issue_type", "Set Issue Type...", _W, "triage", "Bug, feature, task and so on."),
        _a("sub_issues", "Reorder Sub-issues...", _W, "triage", "Change the order of sub-issues."),
        _FAVORITE,
        _PROPERTIES,
    ),
    "pull_request": (
        _default("review", "Review...", "Read the review threads and checks, and review it."),
        _a("diff", "File Differences...", help="The changed files, one comparison per file."),
        _COMMENT,
        _a("merge", "Merge...", _W, "push", "Merge it, with the methods the repository allows."),
        _COPY_LINK,
        _OPEN_WEB,
        _WORKTREE,
        _CODESPACES,
        _COMMIT_COMMENTS,
        _TIMELINE,
        _SUMMARIZE,
        _REACT,
        _LABELS,
        _ASSIGNEES,
        _FAVORITE,
        _PROPERTIES,
    ),
    "run": (
        _default("jobs", "Jobs and Logs", "The run's jobs, steps and logs."),
        _a("what_failed", "What Failed...", help="The failing steps and their log lines."),
        _a("rerun_failed", "Re-run Failed Jobs Only", _W, "push", "Run only what failed again."),
        _a("rerun", "Re-run Workflow", _W, "push", "Run the whole workflow again."),
        _a("cancel_run", "Cancel Run...", _W, "push", "Stop the run. QUILL asks first."),
        _a("artifacts", "View Artifacts...", help="Files the run produced, to download."),
        _OPEN_WEB,
        _a("check_status", "Combined Check Status", help="Every check on the commit, at once."),
        _a(
            "pending_deployments",
            "Review Pending Deployments...",
            _W,
            "push",
            "Approve or reject deployments waiting on you.",
        ),
        _a("approve_fork", "Approve Run from a Fork...", _W, "push", "Let a fork's run start."),
        _a("delete_run", "Delete Run...", _D, "push", "Delete the run and its logs."),
        _COPY_LINK,
        _PROPERTIES,
    ),
    "workflow": (
        _default("workflow_runs", "Runs", "This workflow's runs."),
        _a("run_workflow", "Run Workflow on Branch...", _W, "push", "Start it on a branch."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "release": (
        _default("assets", "Assets", "The release's files and their download counts."),
        _a("edit_release", "Edit Release...", _W, "push", "Change its notes, name and flags."),
        _a("release_notes", "Draft Release Notes...", help="Notes drafted from the changes."),
        _a("upload_asset", "Upload Asset...", _W, "push", "Add a file to the release."),
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "release_asset": (
        _default("download", "Download", "Download the file in your browser."),
        _COPY_LINK,
        _a("delete_asset", "Delete Asset...", _D, "push", "Remove the file from the release."),
        _PROPERTIES,
    ),
    "branch": (
        _default("branch_commits", "Commits", "The branch's commits."),
        _a("compare", "Compare Branches...", help="Commits ahead and behind, and changed files."),
        _CODESPACES,
        _a("copy_name", "Copy Name", help="Copy the branch name."),
        _a("delete_branch", "Delete Branch...", _D, "push", "Delete the branch on GitHub."),
        _PROPERTIES,
    ),
    "commit": (
        _default("open", "Open", "The commit's message and changed files."),
        _COMMIT_COMMENTS,
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "tag": (
        _default("open", "Open", "The tagged commit."),
        _COMMIT_COMMENTS,
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "notification": (
        _default("open", "Open", "Open what the notification is about."),
        _a("mark_read", "Mark Read", _O, "sign_in", "Mark it read on GitHub."),
        _a("mark_done", "Mark Done", _O, "sign_in", "Clear it from your notifications."),
        _a("snooze", "Snooze for One Day", _O, "", "Hide it here until tomorrow."),
        _a("unsubscribe", "Unsubscribe from Thread", _O, "sign_in", "Stop notifications for it."),
        _OPEN_WEB,
        _a("unsnooze", "Unsnooze Locally", _O, "", "Show a snoozed notification again."),
        _PROPERTIES,
    ),
    "repository": (
        _default("open_repository", "Open", "Select the repository's node in the tree."),
        _a("star", "Star or Unstar", _O, "sign_in", "Star it, or take the star away."),
        _a("watch", "Watch or Unwatch", _O, "sign_in", "Choose how much it notifies you."),
        _a("clone", "Clone...", _O, "", "Copy it to a folder on this computer."),
        _a("pin_repository", "Pin", _O, "", "Keep it under Repositories > Pinned."),
        _FAVORITE,
        _OPEN_WEB,
        _CODESPACES,
        _PROPERTIES,
    ),
    "person": (
        _default("open_person", "Open", "Select the person's node in the tree."),
        _a("follow", "Follow or Unfollow", _O, "sign_in", "Follow them, or stop."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "label": (
        _default("label_issues", "Find Issues with Label", "Issues and pull requests with it."),
        _a("edit_label", "Edit Label...", _W, "push", "Change its name, color or description."),
        _a("delete_label", "Delete Label...", _D, "push", "Delete the label everywhere."),
        _PROPERTIES,
    ),
    "gist": (
        _default("edit_gist", "Edit Gist...", "Change the gist's files and description."),
        _a("star_gist", "Star or Unstar", _O, "sign_in", "Star it, or take the star away."),
        _COPY_LINK,
        _OPEN_WEB,
        _a("delete_gist", "Delete Gist...", _D, "sign_in", "Delete the gist."),
        _PROPERTIES,
    ),
    "discussion": (
        _default("discussion_thread", "Open Discussion Thread", "Read the whole thread."),
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "security_alert": (
        _default("open", "Open", "The alert's details and where it was found."),
        _a("dismiss_alert", "Dismiss or Reopen Alert...", _W, "push", "Dismiss with a reason."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "cache": (
        _default("show_details", "Show Details", "The cache's key, size and last use."),
        _a("delete_cache", "Delete Cache...", _D, "push", "Delete this Actions cache."),
        _PROPERTIES,
    ),
    "saved_search": (
        _default("run_search", "Run", "Run the saved search."),
        _a("remove_search", "Remove Saved Search", _O, "", "Forget it on this device."),
        _PROPERTIES,
    ),
    "result": (
        _default("open", "Open", "Read it in the details pane."),
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "node": (
        _default("refresh", "Refresh", "Load this view again. F5 does the same."),
        _OPEN_WEB,
        _a("help_view", "Help for This View", help="What this view shows. F1 does the same."),
        _PROPERTIES,
    ),
}

GITHUB_ACTIONS = ActionTable(_ROWS, properties_command=PROPERTIES_COMMAND)
"""Every GitHub row type's menu, checked against the shared rules on import."""
