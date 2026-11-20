"""A repository's You page, the rest of it: star lists, your fork, sponsoring its owner (PRD 16.7).

Beside Starred and Watch level (:mod:`quill.core.github.sheets_repo`):

- **Star lists**: a check list of your lists, the ones holding this
  repository checked. Saving sends ``updateUserListsForItem``, the very
  mutation **Star Lists...** on the row sends
  (:data:`quill.core.github.star_lists.FOR_ITEM_MUTATION`); several
  repositories at once change only the lists you ticked or cleared.
- **Forked by you**: ticking it forks the repository to your account
  (``POST /repos/{owner}/{repo}/forks``, as **Fork...** on the row does),
  and the save is checked by reading your fork back. A fork is a repository
  of its own, so clearing the box is refused with a sentence saying where it
  is deleted instead.
- **Sponsoring the owner** reads only: sponsoring spends money at a tier you
  choose, so **Sponsor the Owner...** on the row opens the owner's Sponsor
  tiers instead, where nothing is charged until you type their name.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Options, Read, SheetSaveError, Write
from quill.core.github.sheet_fields import dig, ed, ro
from quill.core.github.sheets_you import sponsoring_values
from quill.core.github.star_lists import FOR_ITEM_MUTATION, fetch_lists
from quill.core.workbench.properties import FieldKind, FieldSpec, Value

__all__ = [
    "FORK_READ",
    "FORK_WRITE",
    "OWNER_SPONSOR_READ",
    "OWNER_SPONSOR_WHY",
    "STAR_LISTS_OPTIONS",
    "STAR_LISTS_READ",
    "STAR_LISTS_WRITE",
    "forked_field",
    "owner_sponsoring_field",
    "star_lists_field",
]

OWNER_SPONSOR_WHY = (
    "Sponsoring spends money at a tier you choose, so it is never a check box: "
    "Sponsor the Owner... on the repository's context menu opens the owner's Sponsor "
    "tiers, and GitHub charges nothing until you choose one and type their name."
)
_UNFORK_WHY = (
    "Your fork is a repository of its own, so clearing Forked by you does not delete it; "
    "open your fork and use Delete Repository..., which asks first."
)


# -- star lists ------------------------------------------------------------------------


def star_lists_field() -> FieldSpec:
    return ed(
        "star_lists",
        "Star lists",
        FieldKind.CHECKLIST,
        "Your star lists; the ones holding this repository are checked. New Star List... "
        "in Repositories > Star Lists makes one.",
    )


def _lists_holding(api: Any, ident: Ident) -> dict[str, Value]:
    """The names of your lists that hold this repository; nothing when they cannot be read."""
    try:
        lists = fetch_lists(api)
    except Exception:  # noqa: BLE001 - signed out, or no lists: the field stays empty
        return {}
    wanted = ident.get("repo", "").casefold()
    holding = [
        found.name for found in lists if any(r.casefold() == wanted for r, _d in found.repositories)
    ]
    return {"star_lists": tuple(holding)}


STAR_LISTS_READ = Read(fetch=_lists_holding)

STAR_LISTS_OPTIONS = Options(
    "",
    name=lambda row: str(row.get("name") or ""),
    value=lambda row: str(row.get("id") or ""),
    graphql="query{viewer{lists(first:100){nodes{id name}}}}",
    variables=lambda _ident: {},
    rows=lambda data: [
        n for n in dig(data, "viewer", "lists", "nodes") or () if isinstance(n, Mapping)
    ],
)


def _lists_encode(value: Value, choices: Mapping[str, object], ident: Ident) -> dict[str, object]:
    chosen = value if isinstance(value, tuple) else ()
    return {"itemId": ident.get("node_id", ""), "listIds": [choices.get(n, n) for n in chosen]}


#: The whole set of lists, as Star Lists... sends it; a batch applies each row's own delta first.
STAR_LISTS_WRITE = Write(
    FOR_ITEM_MUTATION, "sign_in", WriteTier.ORGANIZING, "POST", "graphql", encode=_lists_encode
)


# -- your fork -------------------------------------------------------------------------


def forked_field() -> FieldSpec:
    return ed(
        "forked",
        "Forked by you",
        FieldKind.CHECK,
        "Check it to fork the repository to your account, as Fork... on the row does. "
        "GitHub copies the files in a moment; a fork is deleted as a repository of its own.",
    )


_FORK = "query($name:String!){viewer{repository(name:$name){parent{nameWithOwner}}}}"


def _forked(data: Mapping[str, Any], ident: Ident) -> dict[str, Value]:
    parent = str(dig(data, "viewer", "repository", "parent", "nameWithOwner") or "")
    return {"forked": bool(parent) and parent.casefold() == ident.get("repo", "").casefold()}


FORK_READ = Read(
    graphql=_FORK,
    variables=lambda ident: {"name": ident["repo"].partition("/")[2]},
    pick=_forked,
    optional=True,
    fallback={"forked": False},
)


def _fork_encode(value: Value, _choices: Mapping[str, object], _ident: Ident) -> dict[str, object]:
    if value is not True:
        raise SheetSaveError(_UNFORK_WHY)
    return {}


#: Forking is ``POST /repos/{owner}/{repo}/forks``; GitHub cannot take a fork back, so no undo.
FORK_WRITE = Write(
    "/repos/{repo}/forks",
    "sign_in",
    WriteTier.VISIBLE,
    "POST",
    "post",
    encode=_fork_encode,
    undo=False,
)


# -- sponsoring the owner --------------------------------------------------------------


def owner_sponsoring_field() -> FieldSpec:
    return ro("sponsoring", "Sponsoring the owner", FieldKind.CHECK, OWNER_SPONSOR_WHY)


OWNER_SPONSOR_READ = Read(
    graphql=(
        "query($login:String!){repositoryOwner(login:$login)"
        "{... on Sponsorable{viewerIsSponsoring}}}"
    ),
    variables=lambda ident: {"login": ident["repo"].partition("/")[0]},
    extract=sponsoring_values,
    optional=True,
)
