"""The Workbench nodes the spike left unloaded, through the calls that already exist.

GitHub PRD section 11, Phase 3: Pinned, Favorites, Saved Searches, Files,
Milestones, Projects, Organizations and the repository admin pages now fill
their lists. Every one reuses an existing store or fetch, so there is no new
network call and no new egress row:

- ``local:`` reads :class:`quill.core.github.saved_items.GitHubSavedItems`, the
  same per-account file GitHub Items keeps its pins, favorites and searches in;
- ``files:`` is :meth:`GitHubRepoFilesMixin.fetch_repo_folder` (Browse
  Repository Files' call), one folder at a time, with an "Up one folder" row;
- ``milestones:`` is :meth:`GitHubMilestonesMixin.fetch_milestones`;
- ``projects:repository`` is :func:`quill.core.github.projects.list_projects`;
- ``admin:organizations`` and ``admin:org_repositories`` are
  :class:`quill.core.github.repo_admin.GitHubRepoAdminProvider`'s listings;
- ``admin:general`` and ``admin:branch_protection`` list the settings commands
  the editor already has, as rows Enter runs (the change itself stays in the
  dialog it always used, so nothing is changed without that dialog's
  confirmation).

Rows are :class:`~quill.core.github.explore_models.ExploreRow`, so the list,
the details pane and the action table treat them like Explore's own. Every
loader runs off the UI thread.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.navigation_state import account_key_for_token
from quill.core.workbench.tree import NodeSpec

__all__ = ["ADMIN_ACTIONS", "LOCAL_PREFIXES", "load_local", "saved_items_for"]

LOCAL_PREFIXES = ("local:", "files:", "milestones:", "projects:", "admin:")

#: The rows of the two admin pages: (editor command id, label, what it does).
ADMIN_ACTIONS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "general": (
        ("github.rename_repository", "Rename Repository...", "Give the repository a new name."),
        (
            "github.change_repository_visibility",
            "Change Visibility...",
            "Make it public or private.",
        ),
        (
            "github.change_default_branch",
            "Change Default Branch...",
            "The branch pull requests target and the repository opens on.",
        ),
    ),
    "branch_protection": (
        (
            "github.configure_branch_protection",
            "Configure Branch Protection...",
            "Who may change a branch, and what a change needs first.",
        ),
        ("github.delete_branch", "Delete Branch...", "Delete a branch on GitHub. Asks first."),
    ),
}

#: A favorite's item type -> Explore's row kind.
_FAVORITE_KINDS = {"issue": "issue", "pr": "pr"}


def saved_items_for(items: Any) -> Any:
    """GitHub Items' pins, favorites and searches for this account."""
    from quill.core.github.saved_items import GitHubSavedItems

    return GitHubSavedItems.load(account_key=account_key_for_token(getattr(items, "token", None)))


def _local_rows(items: Any, view: str) -> list[ExploreRow]:
    saved = saved_items_for(items)
    if view == "pinned":
        return [
            ExploreRow(repo, "Pinned repository.", f"https://github.com/{repo}", repo, "repo", repo)
            for repo in saved.pinned
        ]
    if view == "favorites":
        return [
            ExploreRow(
                f"{entry.title} ({entry.repo})" if entry.title else entry.url,
                "\n".join(part for part in (entry.subtitle, entry.url) if part),
                entry.url,
                entry.repo,
                _FAVORITE_KINDS.get(entry.item_type, "favorite"),
                entry.key,
                title=entry.title,
            )
            for entry in saved.favorites
        ]
    return [
        ExploreRow(query, "A saved search. Enter runs it.", "", "", "saved_search", query)
        for query in saved.searches or []
    ]


def _file_rows(items: Any, repository: str, folder: str) -> list[ExploreRow]:
    branch = items.fetch_default_branch(repository)
    rows: list[ExploreRow] = []
    if folder:
        parent = folder.rsplit("/", 1)[0] if "/" in folder else ""
        rows.append(
            ExploreRow("Up one folder", f"Back to /{parent}", "", repository, "folder", parent)
        )
    for entry in items.fetch_repo_folder(repository, branch, folder):
        url = entry.url or f"https://github.com/{repository}/blob/{branch}/{entry.path}"
        rows.append(
            ExploreRow(
                entry.label,
                f"{entry.path}\n{url}",
                url,
                repository,
                "folder" if entry.is_folder else "file",
                entry.path,
            )
        )
    return rows


def _organizations(items: Any) -> Any:
    from quill.core.github.repo_admin import GitHubRepoAdminProvider

    return GitHubRepoAdminProvider(getattr(items, "token", "") or "")


def load_local(items: Any, node: NodeSpec, *, instance: str, folder: str = "") -> list[ExploreRow]:
    """Fetch the rows of a ``local:``, ``files:``, ``milestones:``, ``projects:`` or
    ``admin:`` node. Runs off the UI thread."""
    prefix, _, view = node.loader.partition(":")
    if prefix == "local":
        return _local_rows(items, view)
    if prefix == "files":
        return _file_rows(items, instance, folder)
    if prefix == "milestones":
        return [
            ExploreRow(
                milestone.label(),
                milestone.summary(),
                getattr(milestone, "url", "") or f"https://github.com/{instance}/milestones",
                instance,
                "milestone",
                milestone.title,
            )
            for milestone in items.fetch_milestones(instance, state="all")
        ]
    if prefix == "projects":
        from quill.core.github.projects import list_projects

        result = list_projects(getattr(items, "token", "") or "", instance)
        return [
            ExploreRow(
                f"{project.title} (#{project.number})" + (", closed" if project.closed else ""),
                project.description or "A Project board.",
                project.url,
                instance,
                "project",
                project.node_id,
            )
            for project in result.items
        ]
    if view == "organizations":
        return [
            ExploreRow(
                login,
                "An organization you belong to.",
                f"https://github.com/{login}",
                "",
                "org",
                login,
            )
            for login in _organizations(items).list_organizations()
        ]
    if view == "org_repositories":
        return [
            ExploreRow(
                repo.full_name + (", private" if repo.is_private else ""),
                repo.description or "No description.",
                repo.html_url or f"https://github.com/{repo.full_name}",
                repo.full_name,
                "repo",
                repo.full_name,
            )
            for repo in _organizations(items).list_org_repositories(instance)
        ]
    return [
        ExploreRow(label, f"{what} Enter opens it.", "", instance, "admin_action", command)
        for command, label, what in ADMIN_ACTIONS.get(view, ())
    ]
