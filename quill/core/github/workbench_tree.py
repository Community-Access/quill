"""The GitHub Workbench's Navigator tree, as data (GitHub PRD sections 3.3 and 10).

One :class:`~quill.core.workbench.tree.NodeSpec` per node, in the order the
tree shows them. Every repository node gets the same children, so those are
the ``repository`` template; each person and organization likewise.

Loaders name the fetch that already exists, by prefix:

- ``items:<view>`` is a GitHub Items view (``quill/ui/github_items_view.VIEWS``);
- ``explore:<view>`` is an Explore view (:data:`quill.core.github.explore_views.VIEWS`);
- ``local:``, ``files:``, ``milestones:``, ``projects:``, ``admin:`` and
  ``nav:`` name the saved-items store, the file browser, milestones, Projects,
  repository admin and a move in the tree, each an existing call.

The "nothing dropped" test checks that every Items and Explore view has
exactly one home here (``home=True``), so moving to the tree loses no view;
nodes that show the same fetch narrowed (Issues, Pull Requests, the My Work
reasons) set ``home=False``.

:data:`PLANNED` holds what GitHub does that QUILL does not yet (section 14),
with the node each will live in, so building one moves a row from there into
the tree in the same change (section 14.4). It is never shown in the window.
"""

from __future__ import annotations

from typing import Any

from quill.core.workbench.coverage import CoverageRow, CoverageStatus, CoverageTable
from quill.core.workbench.tree import Need, NodeSpec, Scope, TreeSpec

__all__ = ["GITHUB_TREE", "PLANNED", "START_NODE", "node_for_items_view"]

_SIGN_IN = frozenset({Need.SIGN_IN})
_REPO = Scope.REPOSITORY
_Q = Scope.QUERY


def _n(key: str, label: str, parent: str | None = None, **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, **kwargs)


_FIXED: tuple[NodeSpec, ...] = (
    _n("start", "Start Here"),
    _n("attention", "Needs My Attention", scope=Scope.ACCOUNT),
    _n("inbox", "Inbox", "attention", loader="explore:attention", row_type="mixed"),
    _n(
        "notifications",
        "Notifications",
        "attention",
        needs=_SIGN_IN,
        loader="explore:notifications",
        row_type="notification",
    ),
    _n(
        "review_requests",
        "Review Requests",
        "attention",
        needs=_SIGN_IN,
        loader="explore:my_work",
        preset=(("reason", "review_requested"),),
        row_type="pull_request",
    ),
    *(
        _n(
            key,
            label,
            "attention",
            needs=_SIGN_IN,
            loader="explore:my_work",
            preset=(("reason", reason),),
            row_type=row,
            home=False,
        )
        for key, label, reason, row in (
            ("assigned", "Assigned to Me", "assigned", "mixed"),
            ("mentions", "Mentions", "mentioned", "mixed"),
            ("my_pulls", "My Open Pull Requests", "authored_pr", "pull_request"),
            ("my_issues", "My Open Issues", "authored_issue", "issue"),
        )
    ),
    _n(
        "my_activity",
        "My Activity Feed",
        "attention",
        needs=_SIGN_IN,
        loader="explore:activity",
        row_type="event",
    ),
    _n(
        "repositories",
        "Repositories",
        loader="explore:chooser",
        row_type="repository",
        template="repository",
    ),
    _n("pinned", "Pinned", "repositories", loader="local:pinned", row_type="repository"),
    _n("favorites", "Favorites", "repositories", loader="local:favorites", row_type="mixed"),
    _n(
        "my_repositories",
        "My Repositories",
        "repositories",
        needs=_SIGN_IN,
        loader="explore:repositories",
        row_type="repository",
    ),
    _n("starred", "Starred", "repositories", loader="explore:starred", row_type="repository"),
    _n(
        "watched",
        "Watched",
        "repositories",
        needs=_SIGN_IN,
        loader="explore:watched",
        row_type="repository",
    ),
    _n(
        "organizations",
        "Organizations",
        "repositories",
        needs=_SIGN_IN,
        loader="admin:organizations",
        row_type="organization",
        template="organization",
    ),
    _n("search", "Search"),
    _n(
        "search_issues",
        "Issues and Pull Requests",
        "search",
        scope=_Q,
        loader="explore:search",
        row_type="mixed",
    ),
    _n(
        "search_code",
        "Code",
        "search",
        scope=_Q,
        needs=_SIGN_IN,
        loader="explore:code_search",
        row_type="code",
    ),
    _n("search_commits", "Commits", "search", scope=_Q, loader="explore:commit_search"),
    _n(
        "search_repositories",
        "Repositories",
        "search",
        scope=_Q,
        loader="explore:repo_search",
        row_type="repository",
    ),
    _n(
        "saved_searches",
        "Saved Searches",
        "search",
        loader="local:saved_searches",
        row_type="saved_search",
    ),
    _n("people", "People"),
    _n(
        "following",
        "People I Follow",
        "people",
        needs=_SIGN_IN,
        loader="explore:following",
        row_type="person",
    ),
    _n(
        "followers",
        "My Followers",
        "people",
        needs=_SIGN_IN,
        loader="explore:followers",
        row_type="person",
    ),
    _n(
        "my_teams",
        "My Teams",
        "people",
        needs=_SIGN_IN,
        loader="teams:mine",
        row_type="team",
    ),
    _n("find_person", "Find a Person...", "people", template="person"),
    _n("gists", "Gists"),
    _n("my_gists", "My Gists", "gists", needs=_SIGN_IN, loader="explore:gists", row_type="gist"),
    _n("projects", "Projects", needs=_SIGN_IN, loader="projects:mine", row_type="project"),
    # Places still to come, shown so Ctrl+7 and Ctrl+0 land somewhere that says
    # what they will hold (PRD 22.5 Watches, 22.11 Across Repositories).
    _n("watches", "Watches"),
    _n("across", "Across Repositories"),
    # Help is a place, not only a key (Part D11): the same branch in both
    # Workbenches, every node a list you can type through and filter.
    _n("help", "Help and Learning"),
    *(
        _n(key, label, "help", loader=f"help:{view}", row_type="help_topic")
        for key, label, view in (
            ("help_tasks", "Do Something", "tasks"),
            ("help_guide", "The Guide", "guide"),
            ("help_words", "Words", "words"),
            ("help_keys", "Keys", "keys"),
            ("help_changes", "What Changed", "changes"),
            ("help_ask", "Ask a Person", "ask"),
        )
    ),
)


def _r(key: str, label: str, parent: str = "repository", **kwargs: Any) -> NodeSpec:
    return NodeSpec(key, label, parent, scope=_REPO, **kwargs)


_REPOSITORY: tuple[NodeSpec, ...] = (
    NodeSpec("repository", "owner/name", scope=_REPO),
    _r("overview", "Overview", loader="explore:repo_overview"),
    _r(
        "issues",
        "Issues",
        loader="items:issues",
        preset=(("show", "issues"),),
        row_type="issue",
        home=False,
    ),
    _r(
        "pulls",
        "Pull Requests",
        loader="items:issues",
        preset=(("show", "prs"),),
        row_type="pull_request",
        home=False,
    ),
    _r("issues_and_pulls", "Issues and Pull Requests", loader="items:issues", row_type="mixed"),
    _r(
        "discussions",
        "Discussions",
        needs=_SIGN_IN,
        loader="explore:discussions",
        row_type="discussion",
    ),
    _r("actions", "Actions"),
    _r("runs", "Runs", "actions", loader="items:runs", row_type="run"),
    _r("workflows", "Workflows", "actions", loader="items:workflows", row_type="workflow"),
    _r(
        "caches",
        "Caches",
        "actions",
        needs=_SIGN_IN,
        loader="explore:actions_caches",
        row_type="cache",
    ),
    _r("code", "Code"),
    _r("files", "Files", "code", loader="files:browse", row_type="file"),
    _r("branches", "Branches", "code", loader="items:branches", row_type="branch"),
    _r("commits", "Commits", "code", loader="items:commits", row_type="commit"),
    _r("tags", "Tags", "code", loader="items:tags", row_type="tag"),
    _r("upstream", "Upstream", "code", needs=frozenset({Need.FORK}), loader="nav:upstream"),
    _r("releases", "Releases", loader="items:releases", row_type="release"),
    _r("labels", "Labels", loader="explore:labels", row_type="label"),
    _r("milestones", "Milestones", loader="milestones:list", row_type="milestone"),
    _r("repo_projects", "Projects", needs=_SIGN_IN, loader="projects:repository"),
    _r("activity", "Activity", loader="explore:repo_activity", row_type="event"),
    _r("people", "People"),
    _r(
        "contributors",
        "Contributors and People",
        "people",
        loader="explore:repo_people",
        row_type="person",
    ),
    _r("forks", "Forks", "people", loader="explore:repo_forks", row_type="repository"),
    _r(
        "access",
        "Collaborators and Team Access",
        "people",
        needs=_SIGN_IN,
        loader="explore:repo_access",
        row_type="person",
    ),
    _r("insights", "Insights"),
    _r(
        "traffic",
        "Traffic and Contributors",
        "insights",
        needs=_SIGN_IN,
        loader="explore:insights",
    ),
    _r(
        "health",
        "Health Snapshot",
        "insights",
        needs=frozenset({Need.SIGN_IN, Need.OPT_IN}),
        loader="explore:metrics",
    ),
    _r("community", "Community Profile", "insights", loader="explore:community"),
    _r(
        "deployments",
        "Deployments and Environments",
        needs=_SIGN_IN,
        loader="explore:deployments",
        row_type="deployment",
    ),
    _r("pages", "GitHub Pages", loader="explore:pages"),
    _r("security", "Security"),
    _r("alerts", "Alerts", "security", loader="explore:security", row_type="security_alert"),
    _r(
        "alerts_closed",
        "Dismissed and Resolved Alerts",
        "security",
        loader="explore:security_closed",
        row_type="security_alert",
    ),
    _r("settings", "Settings"),
    _r(
        "secrets",
        "Secret and Variable Names",
        "settings",
        needs=frozenset({Need.SIGN_IN, Need.ADMIN}),
        loader="explore:secrets",
    ),
    _r(
        "branch_protection",
        "Branch Protection",
        "settings",
        needs=frozenset({Need.SIGN_IN, Need.ADMIN}),
        loader="admin:branch_protection",
    ),
    _r(
        "general",
        "General",
        "settings",
        needs=frozenset({Need.SIGN_IN, Need.ADMIN}),
        loader="admin:general",
    ),
)

_PERSON: tuple[NodeSpec, ...] = (
    NodeSpec("person", "person", scope=Scope.PERSON),
    *(
        NodeSpec(key, label, "person", scope=Scope.PERSON, loader=f"explore:{view}", row_type=row)
        for key, label, view, row in (
            ("person_repositories", "Repositories", "person_repos", "repository"),
            ("person_activity", "Activity", "person_activity", "event"),
            ("person_followers", "Followers", "person_followers", "person"),
            ("person_following", "Following", "person_following", "person"),
        )
    ),
)

_ORGANIZATION: tuple[NodeSpec, ...] = (
    NodeSpec("organization", "organization", scope=Scope.ORGANIZATION),
    NodeSpec(
        "organization_repositories",
        "Repositories",
        "organization",
        scope=Scope.ORGANIZATION,
        loader="admin:org_repositories",
        row_type="repository",
    ),
    NodeSpec(
        "organization_teams",
        "Teams",
        "organization",
        scope=Scope.ORGANIZATION,
        needs=_SIGN_IN,
        loader="teams:organization",
        row_type="team",
    ),
)

GITHUB_TREE = TreeSpec(
    _FIXED,
    {"repository": _REPOSITORY, "person": _PERSON, "organization": _ORGANIZATION},
)
"""The whole GitHub Navigator."""

START_NODE = "start"

_ITEMS_NODES = {
    "issues": "issues_and_pulls",
    "branches": "branches",
    "commits": "commits",
    "tags": "tags",
    "releases": "releases",
    "workflows": "workflows",
    "runs": "runs",
}


def node_for_items_view(view: str) -> str:
    """The repository-template node that is GitHub Items' *view*'s home."""
    return _ITEMS_NODES[view]


def _planned(feature: str, node: str, reference: str = "") -> CoverageRow:
    return CoverageRow(feature, CoverageStatus.PLANNED, node, reference=reference)


PLANNED = CoverageTable((
    # 14.1, worth adding: people will look for these.
    _planned("Close reason: completed, not planned, duplicate", "Item > Close Issue..."),
    _planned("Linked pull requests and branches for an issue", "Item > Linked Pull Requests"),
    _planned("Saved replies", "Item > Insert Saved Reply", "GX05, GX12"),
    _planned("Wiki", "Repository > Wiki", "GX12"),
    _planned("Repository invitations", "Needs My Attention > Invitations"),
    _planned("Revert a merged pull request", "Pull request context menu > More > Revert..."),
    _planned("Security policy and advisories", "Repository > Security > Advisories", "GX11"),
    # 14.2, worth adding later.
    _planned("Packages", "Repository > Packages"),
    _planned("Insights tables: commit activity, code frequency", "Repository > Insights"),
    _planned("Dependency graph and SBOM export", "Repository > Security > Dependencies"),
    _planned("Create and delete tags", "Repository > Code > Tags"),
    _planned("Hide a comment", "Details > Hide Comment..."),
    _planned("Transfer a repository", "Repository > Settings > Transfer..."),
    _planned("Self-hosted runners", "Repository > Actions > Runners"),
    _planned("Star lists", "Repositories > Starred > each list"),
    _planned("Profile and status", "Account > Profile and Status..."),
))
"""GitHub features with a future home and no node yet (GitHub PRD 14.1, 14.2)."""
