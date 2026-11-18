"""A pull request's exact patch, its revert, and its conflicts in a worktree of their own.

Three things the web does for a pull request that the Workbench now does too:

* **The exact patch** (:func:`patch_text`): every changed file's change as one
  unified diff, the text ``git apply`` reads and the web's ``.diff`` link
  shows, built from ``GET /repos/{repo}/pulls/{n}/files``. A file GitHub sends
  no text change for (a binary file, or one too large) is named on a ``#``
  line rather than silently left out, so the count of files in the patch is
  the count of files in the pull request.
* **Revert** (:func:`revert_pull`): ``revertPullRequest`` opens a new pull
  request that undoes a merged one, the web's Revert button. An unmerged pull
  request has nothing to undo and is refused before anything is sent.
* **Conflicts in a worktree** (:func:`prepare_conflict_worktree`): the pull
  request's head branch is fetched into a new folder of its own, and the base
  branch is merged into it there without committing, so the conflicted files
  are on disk with their ``<<<<<<<`` markers, ready for the editor's Resolve
  Conflicts, and the checkout the person was working in is never touched.

Every GitHub call takes the Workbench's
:class:`~quill.core.github.workbench_api.GitHubApi`, and every git call an
injected runner (``run_subprocess_safely`` in production, a fake in tests).
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "ConflictWorktree",
    "PullPatch",
    "PullToolsError",
    "conflict_branch_name",
    "patch_file_name",
    "patch_text",
    "prepare_conflict_worktree",
    "remote_for",
    "revert_pull",
]

Runner = Callable[..., object]

_PAGE = 100
#: GitHub lists at most this many files of one pull request.
_MOST_FILES = 3000


class PullToolsError(CodedError):
    """A patch, revert or conflict worktree could not be made; the message is said."""

    code = "QUILL-GITHUB-PULL-TOOLS"


# -- the exact patch -----------------------------------------------------------


@dataclass(frozen=True)
class PullPatch:
    text: str
    files: int
    without_text: tuple[str, ...] = field(default_factory=tuple)
    """Files GitHub sent no text change for: binary, or too large."""

    @property
    def sentence(self) -> str:
        noun = "file" if self.files == 1 else "files"
        said = f"The patch has {self.files} {noun}."
        if self.without_text:
            some = len(self.without_text)
            said += (
                f" {some} of them {'has' if some == 1 else 'have'} no text change GitHub "
                "can send, binary or too large, and each is named on a line starting with #."
            )
        return said


def _files(api: GitHubApi, repository: str, number: int) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    page = 1
    while len(found) < _MOST_FILES:
        data = api.rest(
            "GET",
            f"/repos/{repository}/pulls/{int(number)}/files",
            query={"per_page": str(_PAGE), "page": str(page)},
        ).data
        rows = [row for row in (data or []) if isinstance(row, Mapping)]
        found.extend(rows)
        if len(rows) < _PAGE:
            break
        page += 1
    return found


def _one_file(row: Mapping[str, Any]) -> tuple[list[str], bool]:
    """The lines of one file's part of the patch, and whether it carried text."""
    name = str(row.get("filename") or "")
    old = str(row.get("previous_filename") or name)
    status = str(row.get("status") or "modified")
    patch = row.get("patch")
    lines = [f"diff --git a/{old} b/{name}"]
    if status == "renamed" and old != name:
        lines += [f"rename from {old}", f"rename to {name}"]
    if not isinstance(patch, str) or not patch:
        if status == "renamed" and not row.get("changes"):
            return lines, True
        lines.append(f"# {name}: {status}, and GitHub sends no text change for it.")
        return lines, False
    lines.append("--- /dev/null" if status == "added" else f"--- a/{old}")
    lines.append("+++ /dev/null" if status == "removed" else f"+++ b/{name}")
    lines.extend(patch.splitlines())
    return lines, True


def patch_text(api: GitHubApi, repository: str, number: int) -> PullPatch:
    """Pull request #*number*'s change, every file, as one unified diff."""
    rows = _files(api, repository, number)
    lines: list[str] = []
    without: list[str] = []
    for row in rows:
        part, has_text = _one_file(row)
        lines.extend(part)
        if not has_text:
            without.append(str(row.get("filename") or ""))
    text = "\n".join(lines) + ("\n" if lines else "")
    return PullPatch(text=text, files=len(rows), without_text=tuple(without))


def patch_file_name(repository: str, number: int) -> str:
    """``quill-pr-1234.diff``: what the patch is saved as, before it opens."""
    name = repository.rsplit("/", 1)[-1] or "pull"
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in name)
    return f"{safe}-pr-{int(number)}.diff"


# -- revert --------------------------------------------------------------------

_REVERT = """
mutation($id: ID!, $title: String, $body: String, $draft: Boolean) {
  revertPullRequest(input: {pullRequestId: $id, title: $title, body: $body, draft: $draft}) {
    revertPullRequest { number url }
  }
}
"""


def revert_pull(
    api: GitHubApi,
    repository: str,
    number: int,
    *,
    title: str = "",
    body: str = "",
    draft: bool = False,
) -> str:
    """Open a pull request that undoes merged #*number*; returns the sentence to say."""
    pull = api.rest("GET", f"/repos/{repository}/pulls/{int(number)}").data or {}
    if not isinstance(pull, Mapping) or not pull.get("node_id"):
        raise PullToolsError(f"{repository} has no pull request #{number}.")
    if not pull.get("merged"):
        raise PullToolsError(
            f"#{number} is not merged, so there is nothing to revert. "
            "Close it instead, if it should not go in."
        )
    variables: dict[str, object] = {"id": str(pull["node_id"]), "draft": bool(draft)}
    variables["title"] = title or f'Revert "{pull.get("title") or ""}"'
    if body:
        variables["body"] = body
    data = api.graphql(_REVERT, variables)
    made = ((data or {}).get("revertPullRequest") or {}).get("revertPullRequest") or {}
    if not made.get("number"):
        raise PullToolsError(f"GitHub did not open a revert of #{number}.")
    kind = "draft pull request" if draft else "pull request"
    return f"Opened {kind} #{made['number']}, which reverts #{number}."


# -- conflicts in a worktree ---------------------------------------------------


@dataclass(frozen=True)
class ConflictWorktree:
    ok: bool
    message: str
    path: str = ""
    files: tuple[str, ...] = field(default_factory=tuple)
    """The conflicted files, relative to *path*."""


def _git(runner: Runner, cwd: str, *args: str, timeout: float = 120.0) -> tuple[int, str]:
    try:
        raw = runner(["git", *args], cwd=cwd, timeout_seconds=timeout)
    except OSError as exc:
        raise PullToolsError(f"Could not run git in {cwd}: {exc}") from exc
    out = str(getattr(raw, "stdout", "") or "")
    err = str(getattr(raw, "stderr", "") or "")
    return int(getattr(raw, "returncode", 1)), (out + "\n" + err).strip()


def remote_for(runner: Runner, root: str, repository: str) -> str:
    """The name of the remote of *root* that is *repository* on GitHub, or ``""``.

    Remote addresses can carry a credential on a misconfigured checkout, so
    only the remote's name ever leaves this function.
    """
    from quill.core.github.local_repo import parse_github_remote_url

    code, out = _git(runner, root, "remote", "-v", timeout=15.0)
    if code != 0:
        return ""
    wanted = repository.casefold()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and (parse_github_remote_url(parts[1]) or "").casefold() == wanted:
            return parts[0]
    return ""


def conflict_branch_name(number: int) -> str:
    """``pr-12-conflicts``: the local branch the merge is made on, never the head itself."""
    return f"pr-{int(number)}-conflicts"


def prepare_conflict_worktree(
    runner: Runner,
    root: str,
    *,
    remote: str,
    number: int,
    head: str,
    base: str,
    path: str,
    taken_branches: Sequence[str] = (),
) -> ConflictWorktree:
    """Fetch *head* and *base*, put *head* in a new worktree at *path*, merge *base* there.

    Nothing is committed and the checkout at *root* is never changed: the
    merge happens in the new folder, on a new local branch made from the
    head, so the conflicts are on disk to resolve and the person decides when
    to commit and push. ``git fetch`` is the only network call, made by the
    person's own git with their own credentials.
    """
    from quill.core.git_worktree import add_worktree

    for name in (head, base):
        if not name or name.startswith("-") or ".." in name:
            raise PullToolsError("This pull request's branches could not be read.")
    code, out = _git(
        runner,
        root,
        "fetch",
        "--no-tags",
        remote,
        f"+refs/heads/{head}:refs/remotes/{remote}/{head}",
        f"+refs/heads/{base}:refs/remotes/{remote}/{base}",
    )
    if code != 0:
        return ConflictWorktree(
            False, f"git could not fetch {head} and {base} from {remote}: {_last(out)}"
        )
    branch = conflict_branch_name(number)
    suffix = 2
    taken = {name.casefold() for name in taken_branches}
    while branch.casefold() in taken:
        branch = f"{conflict_branch_name(number)}-{suffix}"
        suffix += 1
    added = add_worktree(
        runner, root, path, branch, create_branch=True, from_ref=f"{remote}/{head}"
    )
    if not added.ok:
        return ConflictWorktree(False, added.message)
    where = added.path or path
    code, out = _git(runner, where, "merge", "--no-commit", "--no-ff", f"{remote}/{base}")
    _code, listed = _git(runner, where, "diff", "--name-only", "--diff-filter=U", timeout=30.0)
    files = tuple(line.strip() for line in listed.splitlines() if line.strip())
    if files:
        noun = "file conflicts" if len(files) == 1 else "files conflict"
        return ConflictWorktree(
            True,
            f"{len(files)} {noun} in {where}, on branch {branch}: {', '.join(files)}. "
            "Nothing is committed. Resolve each, then commit and push the branch "
            f"to {head} (git push {remote} {branch}:{head}).",
            path=where,
            files=files,
        )
    if code != 0:
        return ConflictWorktree(False, f"git could not merge {base} into {head}: {_last(out)}")
    return ConflictWorktree(
        True,
        f"{base} merges into {head} with no conflicts, in {where} on branch {branch}. "
        "The merge is staged, not committed: commit and push it if you want it.",
        path=where,
    )


def _last(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-1].strip() if lines else "no reason given"
