"""The pieces every GitHub row type is built from, and the account and settings row types.

Split from :mod:`quill.core.github.item_actions` (which merges
:data:`ACCOUNT_ROWS` into its table and re-exports :data:`PROPERTIES_COMMAND`)
to keep both under the module size budget. The rows here are the ones added
for PRD 14.2 and 14.3: runners, packages, keys, security advisories, webhooks,
deploy keys, autolinks and sponsorships. wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier

__all__ = [
    "ACCOUNT_ROWS",
    "PROJECT_ROWS",
    "PROPERTIES_COMMAND",
]

PROPERTIES_COMMAND = "github.workbench.properties"

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

#: Row types added for PRD 14.2 and 14.3, merged into the Workbench's table.
ACCOUNT_ROWS: dict[str, tuple[ActionRow, ...]] = {
    # Moved from item_actions.py to keep it under the module size budget.
    "release_asset": (
        _default("download", "Download", "Download the file in your browser."),
        _COPY_LINK,
        _a(
            "asset_attestations",
            "Attestations...",
            help="The file's digest and GitHub's attestations for it, such as build provenance.",
        ),
        _a(
            "check_download",
            "Check Download...",
            help="Whether the copy you downloaded matches GitHub's SHA-256 digest for the file.",
        ),
        _a("delete_asset", "Delete Asset...", _D, "push", "Remove the file from the release."),
        _PROPERTIES,
    ),
    "deployment": (
        _default("open", "Open", "Read it in the details pane."),
        _a("delete_deployment", "Delete Deployment...", _D, "push", "Only an inactive one."),
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    # Repository > Discussions > Categories (quill/core/github/discussion_categories.py).
    "discussion_section": (
        _default("open_section", "Open Section", "List the categories in this section."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "discussion_category": (
        _default(
            "category_discussions",
            "Find Discussions in Category",
            "The repository's discussions in this category.",
        ),
        _COPY_LINK,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "runner": (
        _default("show_details", "Show Details", "The runner's state, system and labels."),
        _a("runner_labels", "Runner Labels...", _O, "admin", "Add a label, or take one away."),
        _a("remove_runner", "Remove Runner...", _D, "admin", "GitHub forgets it; asks first."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "pages_site": (
        _default("show_details", "Show Details", "The site's address, status and source."),
        _a("pages_check", "Check Site", help="The latest build, then the custom domain's health."),
        _a("pages_rebuild", "Rebuild", _W, "sign_in", "Ask GitHub for a fresh build."),
        _a("pages_turn_off", "Turn Off Pages...", _D, "sign_in", "Stop publishing, after asking."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "environment": (
        _default("show_details", "Show Details", "The environment's protection rules."),
        _a(
            "environment_deployments",
            "Deployments...",
            help="Its newest deployments, each with its latest state.",
        ),
        _a(
            "environment_secrets", "Secrets...", _W, "sign_in", "Add, change or delete its secrets."
        ),
        _a("environment_variables", "Variables...", _W, "sign_in", "Add, change or delete them."),
        _a(
            "environment_branch_policies",
            "Branch Policies...",
            _W,
            "sign_in",
            "Which branches and tags may deploy.",
        ),
        _a(
            "environment_protection_rules",
            "Protection Rules...",
            _W,
            "sign_in",
            "Apps that must approve a deployment.",
        ),
        _a("environment_delete", "Delete...", _D, "sign_in", "Delete it, after asking."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "codespace": (
        _default("show_details", "Show Details", "The codespace's repository, branch and machine."),
        _a("codespace_start", "Start", _W, "sign_in", "Start it, as it was when it stopped."),
        _a("codespace_stop", "Stop", _W, "sign_in", "Stop it; its files are kept."),
        _a("codespace_machine", "Change Machine...", _W, "sign_in", "A bigger or smaller machine."),
        _a(
            "codespace_export", "Export to a Branch", _W, "sign_in", "Unpushed changes to a branch."
        ),
        _a(
            "codespace_publish",
            "Publish to a New Repository...",
            _W,
            "sign_in",
            "For a codespace made from a template.",
        ),
        _a("codespace_delete", "Delete...", _D, "sign_in", "Delete it, after asking."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "package": (
        _default("show_details", "Show Details", "The package's type, visibility and repository."),
        _OPEN_WEB,
        _a(
            "show_package_versions",
            "Show Versions",
            _R,
            "sign_in",
            "Every version, newest first, with its tags.",
        ),
        _a(
            "restore_package_version",
            "Restore Package Version...",
            _W,
            "sign_in",
            "Bring back a version deleted in the last 30 days.",
        ),
        _a(
            "delete_package_version",
            "Delete Package Version...",
            _D,
            "sign_in",
            "Choose a version, newest first with its tags, and delete it after asking.",
        ),
        _a(
            "delete_package",
            "Delete Package...",
            _D,
            "sign_in",
            "Delete the package and every version, after you type its name.",
        ),
        _COPY_LINK,
        _PROPERTIES,
    ),
    "key": (
        _default("show_details", "Show Details", "The key, its fingerprint, and when it was used."),
        _a("delete_key", "Delete Key...", _D, "sign_in", "Remove it; asks first."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "advisory": (
        _default("show_details", "Show Details", "Its severity, state, packages and credits."),
        _a("advisory_state", "Publish or Close Advisory...", _D, "admin", "Change its state."),
        _a("request_cve", "Request CVE...", _W, "admin", "Ask GitHub for a CVE number."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "webhook": (
        _default("show_details", "Show Details", "Its address, events and last delivery."),
        _a("ping_webhook", "Ping", _O, "admin", "Send it a test message."),
        _a("webhook_test_push", "Send Test Push", _O, "admin", "A push event, if it listens."),
        _a("webhook_on_off", "Turn On or Off...", _W, "admin", "Stop or start its events."),
        _a("webhook_deliveries", "Recent Deliveries...", _W, "admin", "Read and redeliver."),
        _a(
            "change_webhook",
            "Change Address or Secret...",
            _W,
            "admin",
            "The secret is write-only.",
        ),
        _a("delete_webhook", "Delete Webhook...", _D, "admin", "Stop sending it anything."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "deploy_key": (
        _default("show_details", "Show Details", "The key, its fingerprint and access."),
        _a("delete_deploy_key", "Delete Deploy Key...", _D, "admin", "Remove it; asks first."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "autolink": (
        _default("show_details", "Show Details", "The prefix and the address it links to."),
        _a("delete_autolink", "Delete Autolink...", _D, "admin", "Remove it; asks first."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "resource": (
        _default("show_details", "Show Details", "Everything GitHub says about it."),
        _a("resource_edit", "Change...", _W, "sign_in", "Change what GitHub lets you change."),
        _a(
            "resource_repositories",
            "Repositories Allowed...",
            _W,
            "sign_in",
            "Choose which repositories may use it.",
        ),
        _a("resource_delete", "Delete...", _D, "sign_in", "Remove it; asks first."),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "wiki": (
        _default("open_on_github", "Open on GitHub", "Read the wiki in your browser."),
        _a("clone_wiki", "Clone Wiki...", _O, "", "Copy its pages to a folder, to edit them."),
        _COPY_LINK,
        _PROPERTIES,
    ),
    "sponsorship": (
        _default("show_details", "Show Details", "Who, how much, and since when."),
        _a("cancel_sponsorship", "Cancel Sponsorship...", _W, "sign_in", "Stop it; asks first."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "sponsor_tier": (
        _default("show_details", "Show Details", "The tier's price and what it says."),
        _a("sponsor", "Sponsor at This Tier...", _D, "sign_in", "Pay; you type their login."),
        _OPEN_WEB,
        _PROPERTIES,
    ),
}


#: A Project's own care, on its row (quill/ui/github_workbench_project_admin.py).
PROJECT_ROWS: tuple[ActionRow, ...] = (
    _a("project_draft", "Add Draft Issue...", _W, "sign_in", "A quick note on the board."),
    _a("project_field", "New Field...", _W, "sign_in", "Text, number, date or choices."),
    _a("project_field_delete", "Delete Field...", _D, "sign_in", "And every value in it."),
    _a("project_status", "Post Status Update...", _W, "sign_in", "On track, at risk and so on."),
    _a("project_link_repo", "Link to Repository...", _O, "sign_in", "Show it in the repository."),
    _a("project_unlink_repo", "Unlink from Repository...", _O, "sign_in", "Take it out of one."),
    _a("project_template", "Template...", _O, "sign_in", "Offer it, or stop, as a template."),
    _a("project_copy", "Copy Project...", _W, "sign_in", "Fields and views, not its items."),
    _a("project_delete", "Delete Project...", _D, "sign_in", "Asks for its title typed out."),
)
