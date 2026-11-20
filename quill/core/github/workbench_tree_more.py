"""More GitHub Workbench nodes, kept apart so :mod:`workbench_tree` stays under its size budget.

``MORE_FIXED`` joins the account's own nodes and ``MORE_REPOSITORY`` each
repository's; :mod:`quill.core.github.workbench_tree` adds both to the tree.
wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.workbench.coverage import CoverageRow, CoverageStatus, CoverageTable
from quill.core.workbench.tree import Need, NodeSpec, Scope

__all__ = [
    "ACROSS_BY_NAME",
    "ACROSS_GROUPS",
    "MORE_FIXED",
    "MORE_REPOSITORY",
    "PINNED_SEARCH",
    "PLANNED",
]

_SIGN_IN = frozenset({Need.SIGN_IN})

#: Across Repositories' by-name places, category first (GX16): each group is a
#: node whose children are its kinds, every one a row per name (PRD 22.11).
ACROSS_GROUPS: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "across_planning",
        "Planning by Name",
        (
            ("labels", "Labels by Name"),
            ("milestones", "Milestones by Name"),
            ("topics", "Topics by Name"),
        ),
    ),
    (
        "across_code",
        "Code by Name",
        (
            ("tags", "Tags by Name"),
            ("branches", "Branches by Name"),
            ("rules", "Rules and Branch Protection"),
        ),
    ),
    (
        "across_actions",
        "Actions by Name",
        (
            ("environments", "Environments by Name"),
            ("secrets", "Secrets by Name"),
            ("variables", "Variables by Name"),
        ),
    ),
    (
        "across_settings",
        "Settings by Name",
        (
            ("webhooks", "Webhooks by Name"),
            ("deploy_keys", "Deploy Keys by Name"),
            ("autolinks", "Autolinks by Name"),
        ),
    ),
)

ACROSS_BY_NAME: tuple[NodeSpec, ...] = (
    *(
        node
        for key, label, kinds in ACROSS_GROUPS
        for node in (
            NodeSpec(key, label, "across", needs=_SIGN_IN),
            *(
                NodeSpec(
                    f"across_by_{kind}",
                    name,
                    key,
                    needs=_SIGN_IN,
                    loader=f"across:by_{kind}",
                    row_type="by_name",
                )
                for kind, name in kinds
            ),
        )
    ),
    NodeSpec(
        "across_fleet", "Fleet", "across", needs=_SIGN_IN, loader="across:fleet", row_type="fleet"
    ),
)

MORE_FIXED: tuple[NodeSpec, ...] = (
    *ACROSS_BY_NAME,
    NodeSpec(
        "search_people",
        "People and Organizations",
        "search",
        scope=Scope.QUERY,
        loader="explore:user_search",
        row_type="person",
    ),
    NodeSpec("search_topics", "Topics", "search", scope=Scope.QUERY, loader="explore:topic_search"),
    NodeSpec(
        "my_codespaces",
        "My Codespaces",
        "repositories",
        needs=_SIGN_IN,
        loader="explore:my_codespaces",
        row_type="codespace",
    ),
)

MORE_REPOSITORY: tuple[NodeSpec, ...] = (
    NodeSpec(
        "environments",
        "Environments",
        "settings",
        scope=Scope.REPOSITORY,
        needs=frozenset({Need.SIGN_IN, Need.ADMIN}),
        loader="explore:repo_environments",
        row_type="environment",
    ),
    NodeSpec(
        "repo_codespaces",
        "Codespaces",
        "code",
        scope=Scope.REPOSITORY,
        needs=_SIGN_IN,
        loader="explore:repo_codespaces",
        row_type="codespace",
    ),
    # Under Discussions: the spotlight (read only: GitHub's API cannot pin one)
    # and the categories, by section where GitHub gives sections.
    *(
        NodeSpec(
            key,
            label,
            "discussions",
            scope=Scope.REPOSITORY,
            needs=_SIGN_IN,
            loader=f"discussions:{view}",
            row_type=row,
        )
        for key, label, view, row in (
            ("discussions_pinned", "Pinned (spotlight)", "pinned", "discussion"),
            ("discussion_categories", "Categories", "categories", "discussion_category"),
        )
    ),
)

#: A saved search pinned as a node of its own under Saved Searches (GH-R-053):
#: the node is named by the search, and its list is that search's results.
PINNED_SEARCH: tuple[NodeSpec, ...] = (
    NodeSpec(
        "pinned_search",
        "Saved search",
        loader="explore:search",
        preset=(("search", "instance"),),
        row_type="mixed",
        home=False,  # the search's home is Search > Issues and Pull Requests
    ),
)


def _planned(feature: str, node: str, reference: str = "") -> CoverageRow:
    return CoverageRow(feature, CoverageStatus.PLANNED, node, reference=reference)


PLANNED = CoverageTable((
    # 14.1, worth adding: people will look for these.
    _planned(
        "Wiki: pages listed and edited in the Workbench", "Repository > Wiki > each page", "GX12"
    ),
    _planned(
        "Security advisories: comments, private forks, an organization's",
        "Repository > Security > Advisories",
        "GX11",
    ),
    # 14.2, worth adding later.
    _planned("Dependency graph and SBOM export", "Repository > Security > Dependencies"),
    _planned("Packages: one version at a time, and other people's", "Packages > a version"),
    _planned(
        "Self-hosted runners: just-in-time setup and removal tokens",
        "Repository > Actions > Runners > a token",
    ),
))
"""GitHub features with a future home and no node yet (GitHub PRD 14.1, 14.2)."""
