"""Which of a pull request's files you have viewed, and whole-file comments (GH-D, PRD 22.1).

GitHub keeps, per person, whether each changed file of a pull request has been
viewed: ``VIEWED``, ``UNVIEWED``, or ``DISMISSED`` when the file changed again
after you viewed it. The review window shows that state in each file's name
in its outline, can hide the files you have viewed, and marks a file viewed or
not (GraphQL ``markFileAsViewed``, ``unmarkFileAsViewed``), the same marks
GitHub's own Files tab shows. :func:`file_comment_payload` is the REST body
for a comment on a whole file rather than a line (``subject_type: file``).

wx-free and strict-typed; requests go through the Workbench's
:class:`~quill.core.github.workbench_api.GitHubApi`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "STATE_WORDS",
    "ReviewViewedError",
    "ViewedFiles",
    "file_comment_payload",
    "file_label",
    "load_viewed",
    "set_viewed",
]

#: What each of GitHub's states is called aloud.
STATE_WORDS: dict[str, str] = {
    "VIEWED": "viewed",
    "UNVIEWED": "not viewed",
    "DISMISSED": "changed since you viewed it",
}

_MAX_PAGES = 30
_FILES = (
    "query($o:String!,$n:String!,$i:Int!,$after:String){repository(owner:$o,name:$n){"
    "pullRequest(number:$i){id files(first:100,after:$after){nodes{path viewerViewedState} "
    "pageInfo{hasNextPage endCursor}}}}}"
)
_MARK = (
    "mutation($id:ID!,$path:String!){markFileAsViewed("
    "input:{pullRequestId:$id,path:$path}){clientMutationId}}"
)
_UNMARK = (
    "mutation($id:ID!,$path:String!){unmarkFileAsViewed("
    "input:{pullRequestId:$id,path:$path}){clientMutationId}}"
)


class ReviewViewedError(CodedError):
    """A viewed mark or file comment GitHub would refuse, said in one sentence."""

    code = "QUILL-GITHUB-REVIEW-VIEWED"


@dataclass
class ViewedFiles:
    """The pull request's node id and each file's state, as GitHub last said."""

    pull_id: str = ""
    states: dict[str, str] = field(default_factory=dict)

    def is_viewed(self, path: str) -> bool:
        return self.states.get(path) == "VIEWED"

    def word(self, path: str) -> str:
        return STATE_WORDS.get(self.states.get(path, ""), "")

    def counts(self, paths: list[str] | None = None) -> tuple[int, int]:
        """(viewed, total) over *paths*, or over every file GitHub listed."""
        wanted = list(self.states) if paths is None else paths
        return sum(1 for path in wanted if self.is_viewed(path)), len(wanted)

    def sentence(self, paths: list[str] | None = None) -> str:
        viewed, total = self.counts(paths)
        return f"{viewed} of {total} files viewed."


def load_viewed(api: GitHubApi, repository: str, number: int) -> ViewedFiles:
    """Every changed file's viewed state for the signed-in person."""
    owner, _slash, name = repository.partition("/")
    found = ViewedFiles()
    after: str | None = None
    for _page in range(_MAX_PAGES):
        data = api.graphql(_FILES, {"o": owner, "n": name, "i": int(number), "after": after})
        pull = ((data.get("repository") or {}).get("pullRequest")) or {}
        if not pull:
            raise ReviewViewedError(f"{repository} has no pull request #{number}.")
        found.pull_id = str(pull.get("id") or "")
        files: Mapping[str, Any] = pull.get("files") or {}
        for node in files.get("nodes") or []:
            if node and node.get("path"):
                found.states[str(node["path"])] = str(node.get("viewerViewedState") or "")
        page = files.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        after = str(page.get("endCursor") or "")
    return found


def set_viewed(api: GitHubApi, viewed: ViewedFiles, path: str, on: bool) -> str:
    """Mark *path* viewed (*on*) or not; updates *viewed* and returns the sentence to say."""
    if not viewed.pull_id:
        raise ReviewViewedError("Load the pull request's files first.")
    if path not in viewed.states:
        raise ReviewViewedError(f"{path} is not one of this pull request's changed files.")
    api.graphql(_MARK if on else _UNMARK, {"id": viewed.pull_id, "path": path})
    viewed.states[path] = "VIEWED" if on else "UNVIEWED"
    return f"{path} marked as {'viewed' if on else 'not viewed'}. {viewed.sentence()}"


def file_label(path: str, viewed: ViewedFiles | None) -> str:
    """The outline's name for a file: its path, then its state when GitHub gave one."""
    word = viewed.word(path) if viewed is not None else ""
    return f"{path}, {word}" if word else path


def file_comment_payload(path: str, body: str, commit_id: str) -> dict[str, object]:
    """The body of ``POST .../pulls/{n}/comments`` for a comment on the whole of *path*."""
    if not body.strip():
        raise ReviewViewedError("A comment needs some text.")
    if not commit_id:
        raise ReviewViewedError("The pull request's latest commit is not known yet.")
    return {"path": path, "body": body, "commit_id": commit_id, "subject_type": "file"}
