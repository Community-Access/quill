"""Reviewing one commit at a time, and hiding changes that are only whitespace (GH-D).

A pull request of twelve commits is often reviewed as twelve small steps
rather than one large change. :func:`pull_commits` lists them, oldest first,
and :func:`commit_diff` builds that one commit's change in the shape the diff
window already reads (:class:`~quill.core.github.items_provider.GitHubPullDiff`),
compared with its first parent, so the file list, the compare walk, the patch
lines and line comments all work on it unchanged.

:func:`whitespace_only` finds the changed lines of a patch that differ from
their partner only in spaces, tabs or blank lines -- a reindent, a trailing
space removed -- so Hide Whitespace Changes can leave them out, as GitHub's
"Hide whitespace" does.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.github.diff_lines import DiffLine
from quill.core.github.items_provider import GitHubPullDiff, GitHubPullFile
from quill.core.github.workbench_api import GitHubApi

__all__ = ["PullCommit", "commit_diff", "pull_commits", "whitespace_only"]

#: GitHub lists at most this many commits of one pull request.
_MOST_COMMITS = 250


@dataclass(frozen=True)
class PullCommit:
    sha: str
    headline: str
    author: str = ""

    @property
    def label(self) -> str:
        """ "3f9a2c1 Fix the parser, by ann": what the commit chooser shows."""
        by = f", by {self.author}" if self.author else ""
        return f"{self.sha[:7]} {self.headline}{by}"


def pull_commits(api: GitHubApi, repository: str, number: int) -> list[PullCommit]:
    """The pull request's commits, oldest first, up to GitHub's 250."""
    found: list[PullCommit] = []
    page = 1
    while len(found) < _MOST_COMMITS:
        data = api.rest(
            "GET",
            f"/repos/{repository}/pulls/{int(number)}/commits",
            query={"per_page": "100", "page": str(page)},
        ).data
        rows = [row for row in (data or []) if isinstance(row, Mapping)]
        for row in rows:
            commit = row.get("commit") or {}
            message = str((commit.get("message") if isinstance(commit, Mapping) else "") or "")
            who = row.get("author") or {}
            login = str(who.get("login") or "") if isinstance(who, Mapping) else ""
            if not login and isinstance(commit, Mapping):
                login = str((commit.get("author") or {}).get("name") or "")
            found.append(PullCommit(str(row.get("sha") or ""), message.split("\n", 1)[0], login))
        if len(rows) < 100:
            break
        page += 1
    return found


def _file(row: Mapping[str, Any]) -> GitHubPullFile:
    return GitHubPullFile(
        filename=str(row.get("filename") or ""),
        status=str(row.get("status") or ""),
        additions=int(row.get("additions") or 0),
        deletions=int(row.get("deletions") or 0),
        changes=int(row.get("changes") or 0),
        previous_filename=str(row.get("previous_filename") or ""),
        patch=str(row.get("patch") or ""),
    )


def commit_diff(
    api: GitHubApi, repository: str, number: int, title: str, sha: str
) -> GitHubPullDiff:
    """One commit's change, against its first parent, as the diff window reads it."""
    data = api.rest("GET", f"/repos/{repository}/commits/{sha}").data or {}
    parents = data.get("parents") if isinstance(data, Mapping) else None
    parent = str((parents[0] or {}).get("sha") or "") if parents else ""
    files = data.get("files") if isinstance(data, Mapping) else None
    headline = ""
    if isinstance(data, Mapping):
        message = str((data.get("commit") or {}).get("message") or "")
        headline = message.split("\n", 1)[0]
    return GitHubPullDiff(
        number=int(number),
        title=f"{title}, commit {sha[:7]}: {headline}" if headline else title,
        base_ref=f"commit {parent[:7]}" if parent else "the commit before",
        base_sha=parent,
        head_ref=f"commit {sha[:7]}",
        head_sha=sha,
        files=tuple(_file(row) for row in files or () if isinstance(row, Mapping)),
    )


def _collapse(text: str) -> str:
    return "".join(text.split())


def whitespace_only(lines: Sequence[DiffLine]) -> frozenset[int]:
    """The indexes of changed lines that change nothing but whitespace.

    Within one run of removals followed by additions, a removed line and an
    added line whose text is the same once every space and tab is taken out are
    a pair, matched in order; a changed line that is blank is whitespace too.
    """
    hidden: set[int] = set()
    index = 0
    while index < len(lines):
        if lines[index].kind not in ("removed", "added"):
            index += 1
            continue
        run_end = index
        while run_end < len(lines) and lines[run_end].kind in ("removed", "added"):
            run_end += 1
        removed = [i for i in range(index, run_end) if lines[i].kind == "removed"]
        added = [i for i in range(index, run_end) if lines[i].kind == "added"]
        for i in removed + added:
            if not _collapse(lines[i].text):
                hidden.add(i)
        unmatched = [i for i in added if i not in hidden]
        for i in removed:
            if i in hidden:
                continue
            key = _collapse(lines[i].text)
            partner = next((j for j in unmatched if _collapse(lines[j].text) == key), None)
            if partner is not None:
                hidden.update((i, partner))
                unmatched.remove(partner)
        index = run_end
    return frozenset(hidden)
