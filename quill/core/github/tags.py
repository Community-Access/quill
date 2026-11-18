"""Making and deleting tags on their own, without a release (GitHub PRD 14.2).

A tag names one commit for good: ``v2.1.0``. GitHub's web makes tags only as
part of a release; here **New Tag...** on Repository > Code > Tags makes a
lightweight tag on a branch, tag or commit you name (``POST .../git/refs``),
and **Delete Tag...** removes one (``DELETE .../git/refs/tags/{name}``),
saying first when a release is built on it, because the release then loses
its tag.

A tag made with a message is an annotated tag: git keeps a tag object with the
message, who made it and when (``POST .../git/tags``), and the ref points at
that object rather than at the commit. **Read Tag Message** on a tag's row
says it (``GET .../git/tags/{sha}``), or that the tag is lightweight and has
none. Whether a name is taken is asked with ``GET .../git/matching-refs``,
which answers an empty list rather than an error.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.issue_development import valid_branch_name
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "TagError",
    "create_tag",
    "delete_tag",
    "release_for_tag",
    "tag_message",
    "valid_tag_name",
]


class TagError(CodedError):
    """A tag could not be made or deleted; the message is said."""

    code = "QUILL-GITHUB-TAGS"


def valid_tag_name(name: str) -> str:
    """Why *name* cannot be a tag, or "" when it can (the same rules git has for branches)."""
    if not name:
        return "A tag needs a name, such as v1.2.0."
    why = valid_branch_name(name)
    return why.replace("a branch name", "a tag name") if why else ""


def tag_exists(api: GitHubApi, repository: str, name: str) -> bool:
    """Whether *repository* has a tag called exactly *name*."""
    data = api.rest(
        "GET", f"/repos/{repository}/git/matching-refs/tags/{quote(name, safe='/')}"
    ).data
    wanted = f"refs/tags/{name}"
    return any(isinstance(ref, Mapping) and ref.get("ref") == wanted for ref in data or ())


def create_tag(api: GitHubApi, repository: str, name: str, at: str, message: str = "") -> str:
    """Tag *at* (a branch, tag or commit) as *name*; returns the sentence to say.

    With a *message* the tag is annotated: a tag object carries the message,
    and the ref points at that object.
    """
    why = valid_tag_name(name)
    if why:
        raise TagError(why)
    if tag_exists(api, repository, name):
        raise TagError(f"{repository} already has a tag called {name}.")
    try:
        found = api.rest("GET", f"/repos/{repository}/commits/{quote(at, safe='/')}").data
    except Exception as exc:  # noqa: BLE001 - said as one sentence
        raise TagError(f"{repository} has no branch, tag or commit called {at}.") from exc
    sha = str(found.get("sha") or "") if isinstance(found, Mapping) else ""
    if not sha:
        raise TagError(f"{repository} has no branch, tag or commit called {at}.")
    target, kind = sha, "tag"
    if message.strip():
        made = api.rest(
            "POST",
            f"/repos/{repository}/git/tags",
            body={"tag": name, "message": message.strip(), "object": sha, "type": "commit"},
        ).data
        target = str(made.get("sha") or "") if isinstance(made, Mapping) else ""
        if not target:
            raise TagError(f"GitHub did not make the annotated tag {name}.")
        kind = "annotated tag"
    api.rest(
        "POST", f"/repos/{repository}/git/refs", body={"ref": f"refs/tags/{name}", "sha": target}
    )
    return f"Made {kind} {name} on {at}, commit {sha[:7]}."


def tag_message(api: GitHubApi, repository: str, name: str) -> str:
    """The sentence for **Read Tag Message**: who tagged it, when, and the message."""
    try:
        ref = api.rest("GET", f"/repos/{repository}/git/ref/tags/{quote(name, safe='/')}").data
    except Exception as exc:  # noqa: BLE001 - said as one sentence
        raise TagError(f"{repository} has no tag called {name}.") from exc
    target = ref.get("object") if isinstance(ref, Mapping) else None
    if not isinstance(target, Mapping) or target.get("type") != "tag":
        return f"{name} is a lightweight tag: it names a commit and has no message."
    data = api.rest("GET", f"/repos/{repository}/git/tags/{target.get('sha')}").data
    if not isinstance(data, Mapping):
        raise TagError(f"GitHub sent nothing for the tag {name}.")
    raw_tagger = data.get("tagger")
    tagger: Mapping[str, Any] = raw_tagger if isinstance(raw_tagger, Mapping) else {}
    who = str(tagger.get("name") or "someone")
    when = str(tagger.get("date") or "")[:10]
    message = str(data.get("message") or "").strip() or "no message"
    return f"{name}, tagged by {who}" + (f" on {when}" if when else "") + f": {message}"


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
