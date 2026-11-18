"""Setting a commit status by hand (GitHub PRD 22: "Commit statuses").

People who run their own checks outside GitHub Actions -- a test lab, a manual
sign-off -- report the result on the commit as a status: a state, a name
(GitHub calls it the context), a short description and an optional link
(``POST /repos/{repo}/statuses/{sha}``). It shows beside the commit's checks
and can be required by branch protection like any other.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["STATES", "CommitStatusError", "set_commit_status"]

#: The state as offered, and GitHub's word for it.
STATES: tuple[tuple[str, str], ...] = (
    ("Passed", "success"),
    ("Failed", "failure"),
    ("Still running", "pending"),
    ("Could not run", "error"),
)


class CommitStatusError(CodedError):
    """A status could not be set; the message is said."""

    code = "QUILL-GITHUB-COMMIT-STATUS"


def set_commit_status(
    api: GitHubApi,
    repository: str,
    sha: str,
    state: str,
    context: str,
    description: str = "",
    target_url: str = "",
) -> str:
    """Report *state* on commit *sha* under the name *context*; returns the sentence to say."""
    words = next((said for said, code in STATES if code == state), "")
    if not words:
        raise CommitStatusError(f"{state!r} is not a state GitHub takes.")
    name = context.strip() or "manual"
    if target_url and not target_url.startswith("https://"):
        raise CommitStatusError("A status link has to start with https://.")
    body: dict[str, object] = {"state": state, "context": name}
    if description:
        body["description"] = description[:140]
    if target_url:
        body["target_url"] = target_url
    api.rest("POST", f"/repos/{repository}/statuses/{sha}", body=body)
    return f"Set {name} to {words.casefold()} on commit {sha[:7]}."
