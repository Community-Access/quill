"""Transferring a repository to another account or organization (GitHub PRD 14.2).

**Transfer Repository...** on Repository Actions moves a repository to a new
owner (``POST /repos/{owner}/{repo}/transfer``): its issues, pull requests,
wiki, stars and watchers go with it, and GitHub redirects the old address.
Moving to a person's account sends them a request they must accept within a
day; moving to an organization you can create repositories in happens at
once. GitHub answers 202 either way, so the sentence says which to expect.
It may take a new name on the way (`new_name`), and, for an organization,
the teams to give access (`team_ids`, found here from their names).

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["TransferError", "team_ids", "transfer_repository", "valid_name", "valid_owner"]

_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


class TransferError(CodedError):
    """A repository could not be transferred; the message is said."""

    code = "QUILL-GITHUB-REPO-TRANSFER"


def valid_owner(owner: str) -> str:
    """Why *owner* cannot be a GitHub account name, or "" when it can."""
    if not owner:
        return "Transferring needs the new owner: a person's username or an organization."
    if not _OWNER.match(owner):
        return f"{owner} is not a GitHub account name."
    return ""


_NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def valid_name(name: str) -> str:
    """Why *name* cannot be a repository's new name, or "" when it can (or is blank)."""
    if name and (not _NAME.match(name) or name in (".", "..")):
        return (
            f"{name} is not a repository name: use letters, digits, hyphens, "
            "underscores and full stops."
        )
    return ""


def team_ids(api: GitHubApi, org: str, names: Sequence[str]) -> list[int]:
    """The ids of *org*'s teams named *names* (slugs or names), for the transfer to give access."""
    found: list[int] = []
    for name in (n.strip() for n in names):
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-")
        try:
            data = api.rest("GET", f"/orgs/{quote(org, safe='')}/teams/{quote(slug, safe='')}").data
        except GitHubRestError as exc:
            if exc.status == 404:
                raise TransferError(
                    f"{org} has no team called {name} that you can see; teams are for "
                    "an organization, and a person's account has none."
                ) from exc
            raise
        number = data.get("id") if isinstance(data, Mapping) else None
        if not isinstance(number, int):
            raise TransferError(f"GitHub did not say which team {name} is.")
        found.append(number)
    return found


def transfer_repository(
    api: GitHubApi,
    repository: str,
    new_owner: str,
    *,
    new_name: str = "",
    teams: Sequence[str] = (),
) -> str:
    """Transfer *repository* to *new_owner*, renamed and with *teams* given access; says it."""
    owner = new_owner.strip().lstrip("@")
    why = valid_owner(owner) or valid_name(new_name.strip())
    if why:
        raise TransferError(why)
    current, _, name = repository.partition("/")
    renamed = new_name.strip()
    if owner.lower() == current.lower():
        raise TransferError(f"{repository} already belongs to {owner}.")
    body: dict[str, object] = {"new_owner": owner}
    if renamed and renamed != name:
        body["new_name"] = renamed
    if any(t.strip() for t in teams):
        body["team_ids"] = team_ids(api, owner, teams)
    try:
        data = api.rest("POST", f"/repos/{repository}/transfer", body=body).data
    except GitHubRestError as exc:
        if exc.status == 403:
            raise TransferError(
                f"Only an owner or administrator of {repository} can transfer it."
            ) from exc
        if exc.status == 422:
            raise TransferError(
                f"GitHub refused: {owner} may not exist, may already have a repository "
                f"called {renamed or name}, or you cannot create repositories there."
            ) from exc
        raise
    landed = str(data.get("full_name") or "") if isinstance(data, Mapping) else ""
    if landed and landed.lower() != repository.lower():
        return f"Transferred {repository}; it is now {landed}. The old address redirects."
    return (
        f"Asked GitHub to transfer {repository} to {owner}. A person has a day to accept; "
        "an organization takes it at once."
    )
