"""Transferring a repository to another account or organization (GitHub PRD 14.2).

**Transfer Repository...** on Repository Actions moves a repository to a new
owner (``POST /repos/{owner}/{repo}/transfer``): its issues, pull requests,
wiki, stars and watchers go with it, and GitHub redirects the old address.
Moving to a person's account sends them a request they must accept within a
day; moving to an organization you can create repositories in happens at
once. GitHub answers 202 either way, so the sentence says which to expect.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from quill.core.error_codes import CodedError
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["TransferError", "transfer_repository", "valid_owner"]

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


def transfer_repository(api: GitHubApi, repository: str, new_owner: str) -> str:
    """Transfer *repository* to *new_owner*; returns the sentence to say."""
    owner = new_owner.strip().lstrip("@")
    why = valid_owner(owner)
    if why:
        raise TransferError(why)
    current, _, name = repository.partition("/")
    if owner.lower() == current.lower():
        raise TransferError(f"{repository} already belongs to {owner}.")
    try:
        data = api.rest("POST", f"/repos/{repository}/transfer", body={"new_owner": owner}).data
    except GitHubRestError as exc:
        if exc.status == 403:
            raise TransferError(
                f"Only an owner or administrator of {repository} can transfer it."
            ) from exc
        if exc.status == 422:
            raise TransferError(
                f"GitHub refused: {owner} may not exist, may already have a repository "
                f"called {name}, or you cannot create repositories there."
            ) from exc
        raise
    landed = str(data.get("full_name") or "") if isinstance(data, Mapping) else ""
    if landed and landed.lower() != repository.lower():
        return f"Transferred {repository}; it is now {landed}. The old address redirects."
    return (
        f"Asked GitHub to transfer {repository} to {owner}. A person has a day to accept; "
        "an organization takes it at once."
    )
