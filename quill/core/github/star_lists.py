"""Repositories > Star Lists: GitHub's lists of starred repositories (PRD 14.2).

GitHub lets you sort your stars into lists, such as "Screen readers" or
"Tools I use". The Workbench's **Star Lists** node lists every repository on
every list, each row starting with its list ("Screen readers: nvaccess/nvda,
NVDA, the free screen reader"), so the rows are ordinary repository rows:
Enter opens the repository, and Star, Watch and Clone work as anywhere else.

* **New Star List...** (``Ctrl+N`` there) makes a list (``createUserList``).
* **Star Lists...** on any repository chooses which lists it is on, the ones
  it is on already checked (``updateUserListsForItem``).
* **Rename or Delete Star List...** renames a list, changes its description
  or privacy, or deletes it (``updateUserList``, ``deleteUserList``); deleting
  a list unstars nothing.

Lists come from ``viewer.lists`` (GraphQL). Takes the Workbench's
:class:`~quill.core.github.workbench_api.GitHubApi`. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "StarList",
    "StarListError",
    "create_list",
    "delete_list",
    "fetch_lists",
    "list_rows",
    "set_lists_for",
    "update_list",
]


class StarListError(CodedError):
    """A star list could not be read or changed; the message is said."""

    code = "QUILL-GITHUB-STAR-LISTS"


@dataclass(frozen=True)
class StarList:
    id: str
    name: str
    description: str = ""
    private: bool = False
    repositories: tuple[tuple[str, str], ...] = field(default=())  # (owner/name, description)

    @property
    def label(self) -> str:
        count = len(self.repositories)
        words = f"{count} repositor{'y' if count == 1 else 'ies'}"
        return f"{self.name}: {words}, {'private' if self.private else 'public'}"


_LISTS = """
query {
  viewer {
    lists(first: 100) {
      nodes {
        id name description isPrivate
        items(first: 100) {
          nodes { ... on Repository { nameWithOwner description } }
        }
      }
    }
  }
}
"""

_REPOSITORY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) { id }
}
"""

_CREATE = """
mutation($name: String!, $description: String, $isPrivate: Boolean) {
  createUserList(input: {name: $name, description: $description, isPrivate: $isPrivate}) {
    list { id name }
  }
}
"""

_UPDATE = """
mutation($listId: ID!, $name: String, $description: String, $isPrivate: Boolean) {
  updateUserList(
    input: {listId: $listId, name: $name, description: $description, isPrivate: $isPrivate}
  ) { list { id name } }
}
"""

_DELETE = """
mutation($listId: ID!) {
  deleteUserList(input: {listId: $listId}) { clientMutationId }
}
"""

_FOR_ITEM = """
mutation($itemId: ID!, $listIds: [ID!]!) {
  updateUserListsForItem(input: {itemId: $itemId, listIds: $listIds}) { clientMutationId }
}
"""


def _nodes(value: object) -> list[Mapping[str, Any]]:
    nodes = value.get("nodes") if isinstance(value, Mapping) else None
    return [node for node in nodes or () if isinstance(node, Mapping)]


def fetch_lists(api: GitHubApi) -> list[StarList]:
    data = api.graphql(_LISTS, {})
    viewer = data.get("viewer") if isinstance(data, Mapping) else None
    lists = []
    for node in _nodes(viewer.get("lists") if isinstance(viewer, Mapping) else None):
        repos = tuple(
            (str(item.get("nameWithOwner")), str(item.get("description") or ""))
            for item in _nodes(node.get("items"))
            if item.get("nameWithOwner")
        )
        lists.append(
            StarList(
                str(node.get("id") or ""),
                str(node.get("name") or ""),
                str(node.get("description") or ""),
                bool(node.get("isPrivate")),
                repos,
            )
        )
    lists.sort(key=lambda found: found.name.lower())
    return lists


def list_rows(lists: list[StarList], warnings: list[str]) -> list[ExploreRow]:
    """Every repository on every list, each row starting with its list's name."""
    rows = []
    for found in lists:
        for repo, description in found.repositories:
            label = f"{found.name}: {repo}" + (f", {description}" if description else "")
            detail = f"{label}\nOn the star list {found.label}."
            rows.append(ExploreRow(label, detail, f"https://github.com/{repo}", repo, "repo", repo))
    empty = [found.name for found in lists if not found.repositories]
    if not lists:
        warnings.append("You have no star lists yet. Press Ctrl+N here to make one.")
    elif empty:
        warnings.append("Empty star lists: " + ", ".join(empty) + ".")
    return rows


def _check_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise StarListError("A star list needs a name.")
    if len(cleaned) > 32:
        raise StarListError("GitHub keeps a star list's name to 32 characters.")
    return cleaned


def create_list(api: GitHubApi, name: str, description: str = "", *, private: bool) -> str:
    cleaned = _check_name(name)
    api.graphql(_CREATE, {"name": cleaned, "description": description, "isPrivate": private})
    return f"Made the {'private' if private else 'public'} star list {cleaned}."


def update_list(
    api: GitHubApi, found: StarList, *, name: str, description: str, private: bool
) -> str:
    cleaned = _check_name(name)
    api.graphql(
        _UPDATE,
        {"listId": found.id, "name": cleaned, "description": description, "isPrivate": private},
    )
    renamed = f", now called {cleaned}" if cleaned != found.name else ""
    return f"Changed the star list {found.name}{renamed}."


def delete_list(api: GitHubApi, found: StarList) -> str:
    api.graphql(_DELETE, {"listId": found.id})
    return f"Deleted the star list {found.name}. Its repositories are still starred."


def set_lists_for(api: GitHubApi, repository: str, chosen: list[StarList]) -> str:
    """Put *repository* on exactly the lists *chosen*; returns the sentence to say."""
    owner, _, name = repository.partition("/")
    data = api.graphql(_REPOSITORY, {"owner": owner, "name": name})
    repo = data.get("repository") if isinstance(data, Mapping) else None
    item = str(repo.get("id") or "") if isinstance(repo, Mapping) else ""
    if not item:
        raise StarListError(f"GitHub has no repository called {repository}.")
    api.graphql(_FOR_ITEM, {"itemId": item, "listIds": [found.id for found in chosen]})
    if not chosen:
        return f"{repository} is on no star lists now."
    return f"{repository} is now on: {', '.join(found.name for found in chosen)}."
