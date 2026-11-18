"""Making and deleting tags on their own, without a release (GitHub PRD 14.2).

A tag names one commit for good: ``v2.1.0``. GitHub's web makes tags only as
part of a release; here **New Tag...** on Repository > Code > Tags makes a
lightweight tag on a branch, tag or commit you name (``POST .../git/refs``),
and **Delete Tag...** removes one (``DELETE .../git/refs/tags/{name}``),
saying first when a release is built on it, because the release then loses
its tag.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.issue_development import valid_branch_name
from quill.core.github.workbench_api import GitHubApi

__all__ = ["TagError", "create_tag", "delete_tag", "release_for_tag", "valid_tag_name"]


class TagError(CodedError):
    """A tag could not be made or deleted; the message is said."""

    code = "QUILL-GITHUB-TAGS"


def valid_tag_name(name: str) -> str:
    """Why *name* cannot be a tag, or "" when it can (the same rules git has for branches)."""
    if not name:
        return "A tag needs a name, such as v1.2.0."
    why = valid_branch_name(name)
    return why.replace("a branch name", "a tag name") if why else ""


def _exists(api: GitHubApi, path: str) -> bool:
    try:
        api.rest("GET", path)
    except Exception:  # noqa: BLE001 - not found is the answer wanted
        return False
    return True


def create_tag(api: GitHubApi, repository: str, name: str, at: str) -> str:
    """Tag *at* (a branch, tag or commit) as *name*; returns the sentence to say."""
    why = valid_tag_name(name)
    if why:
        raise TagError(why)
    if _exists(api, f"/repos/{repository}/git/ref/tags/{quote(name, safe='/')}"):
        raise TagError(f"{repository} already has a tag called {name}.")
    try:
        found = api.rest("GET", f"/repos/{repository}/commits/{quote(at, safe='/')}").data
    except Exception as exc:  # noqa: BLE001 - said as one sentence
        raise TagError(f"{repository} has no branch, tag or commit called {at}.") from exc
    sha = str(found.get("sha") or "") if isinstance(found, Mapping) else ""
    if not sha:
        raise TagError(f"{repository} has no branch, tag or commit called {at}.")
    api.rest("POST", f"/repos/{repository}/git/refs", body={"ref": f"refs/tags/{name}", "sha": sha})
    return f"Made tag {name} on {at}, commit {sha[:7]}."


def release_for_tag(api: GitHubApi, repository: str, name: str) -> str:
    """The name of the release built on tag *name*, or "" when there is none."""
    try:
        data = api.rest("GET", f"/repos/{repository}/releases/tags/{quote(name, safe='/')}").data
    except Exception:  # noqa: BLE001 - no release is the usual answer
        return ""
    if not isinstance(data, Mapping):
        return ""
    return str(data.get("name") or data.get("tag_name") or name)


def delete_tag(api: GitHubApi, repository: str, name: str) -> str:
    api.rest("DELETE", f"/repos/{repository}/git/refs/tags/{quote(name, safe='/')}")
    return f"Deleted tag {name}."
