"""The practice repository: somewhere to learn GitHub's writes on nothing that matters (PRD 22.8).

Help > Practice on GitHub... makes a private repository in the signed-in
account, ``quill-practice``, and fills it with things to practise on: three
issues (one a bug, one with a task list, one a question), labels, a branch
with a change, a pull request from it, and a workflow that fails on purpose,
so What Failed, Re-run and the jobs window have a run to read. When the
practice is over it is deleted, which GitHub allows only to a token with the
``delete_repo`` scope; without it QUILL says how to delete it on the web.

Everything is sent through the Workbench's
:class:`~quill.core.github.workbench_api.GitHubApi`. wx-free and strict-typed.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "PRACTICE_NAME",
    "PracticeError",
    "PracticeRepository",
    "create_practice",
    "delete_practice",
    "find_practice",
]

PRACTICE_NAME = "quill-practice"
_MARK = "Made by QUILL for practice. Safe to change, break and delete."


class PracticeError(CodedError):
    """The practice repository could not be made, found or deleted; the message is said."""

    code = "QUILL-GITHUB-PRACTICE"


@dataclass
class PracticeRepository:
    full_name: str
    made: list[str] = field(default_factory=list)

    @property
    def sentence(self) -> str:
        return f"Made {self.full_name}, private, with {', '.join(self.made)}."


_LABELS = (
    ("practice: bug", "d73a4a", "Something to fix, for practice"),
    ("practice: question", "d876e3", "A question, for practice"),
)

_ISSUES = (
    (
        "Practice: the greeting has a typo",
        "The README says \"Helo\". Practise labelling this, assigning it to yourself, "
        "commenting, and closing it as completed.\n\n" + _MARK,
        ("practice: bug",),
    ),
    (
        "Practice: a task list to work through",
        "Practise checking these off with Check or Uncheck a Task, and converting the "
        "rest to sub-issues.\n\n- [ ] Read this issue\n- [ ] Check this task\n"
        "- [ ] Convert this one to a sub-issue\n\n" + _MARK,
        (),
    ),
    (
        "Practice: should we add a changelog?",
        "Practise replying with the comment window, mentioning someone, and closing "
        "this as not planned.\n\n" + _MARK,
        ("practice: question",),
    ),
)

_WORKFLOW = """name: Practice checks
on: [push, pull_request, workflow_dispatch]
jobs:
  greet:
    runs-on: ubuntu-latest
    steps:
      - name: Say hello
        run: echo "Hello from the practice repository"
      - name: Fail on purpose
        run: |
          echo "This step fails on purpose, so there is a failure to read."
          exit 1
"""


def _put_file(
    api: GitHubApi, repo: str, path: str, text: str, message: str, branch: str = ""
) -> None:
    body: dict[str, object] = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }
    if branch:
        body["branch"] = branch
        current = _sha_of(api, repo, path, branch)
        if current:
            body["sha"] = current
    api.rest("PUT", f"/repos/{repo}/contents/{path}", body=body)


def _sha_of(api: GitHubApi, repo: str, path: str, branch: str) -> str:
    try:
        data = api.rest("GET", f"/repos/{repo}/contents/{path}", query={"ref": branch}).data
    except Exception:  # noqa: BLE001 - not there yet is the usual answer
        return ""
    return str((data or {}).get("sha") or "") if isinstance(data, dict) else ""


def find_practice(api: GitHubApi, login: str) -> str:
    """``login/quill-practice`` when it exists, else ``""``."""
    try:
        data = api.rest("GET", f"/repos/{login}/{PRACTICE_NAME}").data
    except Exception:  # noqa: BLE001 - 404 is "not made yet"
        return ""
    return str((data or {}).get("full_name") or "") if isinstance(data, dict) else ""


def create_practice(
    api: GitHubApi, login: str, *, progress: Callable[[str], None] | None = None
) -> PracticeRepository:
    """Make and fill the practice repository. Refuses when one is already there."""
    say = progress or (lambda _text: None)
    if find_practice(api, login):
        raise PracticeError(
            f"{login}/{PRACTICE_NAME} is already there. Open it, or delete it to start over."
        )
    created = api.rest(
        "POST",
        "/user/repos",
        body={
            "name": PRACTICE_NAME,
            "private": True,
            "auto_init": True,
            "description": _MARK,
            "has_issues": True,
        },
    ).data
    repo = str((created or {}).get("full_name") or f"{login}/{PRACTICE_NAME}")
    base = str((created or {}).get("default_branch") or "main")
    practice = PracticeRepository(repo)
    say("Adding the README and a workflow that fails on purpose.")
    _put_file(api, repo, "README.md", "# Helo\n\n" + _MARK + "\n", "Practice: a README", base)
    _put_file(api, repo, ".github/workflows/practice.yml", _WORKFLOW, "Practice: checks", base)
    practice.made.append("a workflow that fails on purpose")
    say("Adding labels and issues.")
    for name, color, description in _LABELS:
        api.rest(
            "POST",
            f"/repos/{repo}/labels",
            body={"name": name, "color": color, "description": description},
        )
    for title, body, labels in _ISSUES:
        api.rest(
            "POST",
            f"/repos/{repo}/issues",
            body={"title": title, "body": body, "labels": list(labels)},
        )
    practice.made.append(f"{len(_ISSUES)} issues")
    say("Adding a branch and a pull request.")
    head = api.rest("GET", f"/repos/{repo}/git/ref/heads/{base}").data or {}
    sha = str((head.get("object") or {}).get("sha") or "") if isinstance(head, dict) else ""
    api.rest(
        "POST", f"/repos/{repo}/git/refs", body={"ref": "refs/heads/fix-greeting", "sha": sha}
    )
    _put_file(
        api,
        repo,
        "README.md",
        "# Hello\n\n" + _MARK + "\n",
        "Practice: fix the greeting",
        "fix-greeting",
    )
    api.rest(
        "POST",
        f"/repos/{repo}/pulls",
        body={
            "title": "Practice: fix the greeting",
            "head": "fix-greeting",
            "base": base,
            "body": "Practise reviewing this: open its diff, comment on a line, approve it, "
            "and merge it.\n\n" + _MARK,
        },
    )
    practice.made.append("a branch with a pull request")
    return practice


def delete_practice(api: GitHubApi, login: str) -> str:
    """Delete ``login/quill-practice``; returns the sentence to say."""
    from quill.core.github.rest_transport import GitHubRestError

    repo = find_practice(api, login)
    if not repo:
        return f"There is no {PRACTICE_NAME} repository in {login} to delete."
    try:
        api.rest("DELETE", f"/repos/{repo}")
    except GitHubRestError as exc:
        if exc.status in (403, 404):
            raise PracticeError(
                f"GitHub would not let QUILL delete {repo}: deleting a repository needs a "
                "sign-in with the delete_repo permission. Delete it on GitHub instead, from "
                "the repository's Settings, at the bottom of General."
            ) from exc
        raise
    return f"Deleted {repo}."
