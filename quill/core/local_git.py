"""Local git accessibility engine (`docs/planning/github.md` section 4).

The crown-jewel work from the git/gh integration PRD: everything here turns
a local git operation that is normally screen-reader-hostile (a merge
conflict's raw `<<<<<<<` markers, an interactive rebase's reorderable todo
list meant to be edited by eye, `git blame`'s dense gutter) into a
structured model a dialog can narrate step by step.

wx-free, strict-typed (`mypy quill/core` scope). Every function takes an
injected ``runner`` (mirrors :data:`quill.core.vault.sync.Runner` —
``quill.stability.safe_subprocess.run_subprocess_safely`` in production, a
fake in tests) exactly like :mod:`quill.core.git_sync`, so this module is
fully unit-testable without wx and without trusting a live network. Callers
resolve the actual ``git`` executable via :mod:`quill.core.git_binaries`
before ever invoking a runner.

Scope note: this module is a *local* git engine. It never talks to GitHub's
API (that's ``quill/core/github/*``) and never pushes/pulls a remote (that's
``git_sync.py`` / ``vault/sync.py``) — it only operates on the working copy
and its own history: status, staging, diffing, branches, stash, blame,
bisect, and a genuinely accessible interactive rebase.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quill.core.vault.sync import Runner, detect_conflicts

_DEFAULT_TIMEOUT = 30.0


class LocalGitError(RuntimeError):
    """A local git operation failed. Carries git's own stderr where useful."""


@dataclass(frozen=True, slots=True)
class _CommandResult:
    returncode: int
    stdout: str
    stderr: str


def _run(
    root: str, runner: Runner, *args: str, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> _CommandResult:
    """Run ``git <args>`` in *root* via the injected *runner*.

    ``Runner`` is typed ``Callable[..., object]`` (it wraps whatever
    ``run_subprocess_safely`` or a test fake returns), so the raw result's
    attributes aren't visible to mypy; ``getattr`` here is the same seam
    ``git_sync.py``'s own ``_run`` already uses for the identical reason.
    """
    raw = runner(["git", *args], cwd=root, timeout_seconds=timeout_seconds)
    return _CommandResult(
        returncode=int(getattr(raw, "returncode", 1)),
        stdout=str(getattr(raw, "stdout", "") or ""),
        stderr=str(getattr(raw, "stderr", "") or ""),
    )


def _run_ok(
    root: str, runner: Runner, *args: str, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> str:
    """Run a git command and return stdout, raising on a nonzero exit."""
    result = _run(root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        raise LocalGitError((result.stderr or result.stdout or "git command failed").strip())
    return result.stdout


# ---------------------------------------------------------------------------
# Uncommitted changes: status, diff content, stage/unstage
# ---------------------------------------------------------------------------

#: git status --porcelain=v1 staged/unstaged code -> a plain-English label.
_STATUS_LABELS = {
    "M": "modified",
    "A": "added",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "unmerged",
    "?": "untracked",
    " ": "",
}


@dataclass(frozen=True, slots=True)
class FileChange:
    """One row of ``git status`` -- a file with a staged and/or unstaged change."""

    path: str
    staged_code: str  # X column: "", or M/A/D/R/C
    unstaged_code: str  # Y column: "", or M/D/? etc.
    is_conflict: bool = False

    @property
    def staged_label(self) -> str:
        return _STATUS_LABELS.get(self.staged_code, self.staged_code)

    @property
    def unstaged_label(self) -> str:
        return _STATUS_LABELS.get(self.unstaged_code, self.unstaged_code)


@dataclass(frozen=True, slots=True)
class RepoStatus:
    branch: str
    changes: tuple[FileChange, ...]
    conflicts: tuple[str, ...]


def get_status(root: str, *, runner: Runner) -> RepoStatus:
    """The working copy's current status: branch name, changed files, conflicts."""
    branch = _run_ok(root, runner, "rev-parse", "--abbrev-ref", "HEAD").strip()
    porcelain = _run_ok(root, runner, "status", "--porcelain=v1")
    conflicts = set(detect_conflicts(porcelain))
    changes: list[FileChange] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path = line[3:].strip()
        staged, unstaged = code[0], code[1]
        changes.append(
            FileChange(
                path=path,
                staged_code="" if staged == " " else staged,
                unstaged_code="" if unstaged == " " else unstaged,
                is_conflict=path in conflicts,
            )
        )
    return RepoStatus(branch=branch, changes=tuple(changes), conflicts=tuple(sorted(conflicts)))


def file_content_at_ref(root: str, ref: str, path: str, *, runner: Runner) -> str:
    """A file's text content at *ref* ("HEAD" for the last commit, "" for the
    working tree is read directly by the caller, not through this). Returns
    "" for a file that does not exist at that ref (a newly added file has no
    HEAD side) -- mirrors ``GitHubItemsProvider.fetch_file_text``'s contract
    so the UI can feed both into the same compare-engine call."""
    result = _run(root, runner, "show", f"{ref}:{path}")
    if result.returncode != 0:
        return ""
    return str(result.stdout or "")


def stage_file(root: str, path: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "add", "--", path)


def unstage_file(root: str, path: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "restore", "--staged", "--", path)


def stage_all(root: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "add", "-A")


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BranchInfo:
    name: str
    is_current: bool


def list_local_branches(root: str, *, runner: Runner) -> list[BranchInfo]:
    output = _run_ok(root, runner, "branch", "--format=%(HEAD)%09%(refname:short)")
    branches: list[BranchInfo] = []
    for line in output.splitlines():
        if "\t" not in line:
            continue
        marker, name = line.split("\t", 1)
        branches.append(BranchInfo(name=name.strip(), is_current=marker.strip() == "*"))
    return branches


@dataclass(frozen=True, slots=True)
class SwitchResult:
    ok: bool
    message: str


def switch_branch(root: str, name: str, *, runner: Runner, force: bool = False) -> SwitchResult:
    """Switch to local branch *name*. Refuses when the working copy is dirty
    unless *force* is set -- an uncommitted-changes guard, not a git default
    (plain ``git switch`` already refuses on an actual conflict, but silently
    carries a clean fast-forward-able change over; QUILL asks first either way
    so a screen-reader user is never surprised by what came along for the
    ride)."""
    if not force:
        status = get_status(root, runner=runner)
        if status.changes:
            return SwitchResult(
                ok=False,
                message=(
                    f"{len(status.changes)} uncommitted change(s) present. "
                    "Commit, stash, or discard them before switching branches."
                ),
            )
    result = _run(root, runner, "switch", name)
    if result.returncode != 0:
        return SwitchResult(ok=False, message=(result.stderr or "Could not switch branch").strip())
    return SwitchResult(ok=True, message=f"Switched to {name}")


# ---------------------------------------------------------------------------
# Stash
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StashEntry:
    ref: str  # e.g. "stash@{0}"
    message: str


def list_stashes(root: str, *, runner: Runner) -> list[StashEntry]:
    output = _run_ok(root, runner, "stash", "list", "--format=%gd%x09%s")
    entries: list[StashEntry] = []
    for line in output.splitlines():
        if "\t" not in line:
            continue
        ref, message = line.split("\t", 1)
        entries.append(StashEntry(ref=ref.strip(), message=message.strip()))
    return entries


def stash_save(root: str, message: str, *, runner: Runner) -> None:
    args = ["stash", "push", "-m", message] if message else ["stash", "push"]
    _run_ok(root, runner, *args)


def stash_apply(root: str, ref: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "stash", "apply", ref)


def stash_drop(root: str, ref: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "stash", "drop", ref)


# ---------------------------------------------------------------------------
# Blame
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BlameInfo:
    commit_sha: str
    author: str
    date: str
    summary: str


def blame_line(root: str, path: str, line: int, *, runner: Runner) -> BlameInfo:
    """Who last touched *line* (1-indexed) of *path*, and when."""
    output = _run_ok(root, runner, "blame", "-L", f"{line},{line}", "--porcelain", "--", path)
    lines = output.splitlines()
    if not lines:
        raise LocalGitError(f"No blame data for {path}:{line}")
    sha = lines[0].split()[0]
    author = ""
    date = ""
    summary = ""
    for entry in lines[1:]:
        if entry.startswith("author "):
            author = entry[len("author ") :]
        elif entry.startswith("author-time "):
            date = entry[len("author-time ") :]
        elif entry.startswith("summary "):
            summary = entry[len("summary ") :]
    return BlameInfo(commit_sha=sha, author=author, date=date, summary=summary)


# ---------------------------------------------------------------------------
# Bisect
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BisectStatus:
    done: bool
    message: str
    culprit_sha: str = ""


def bisect_start(root: str, bad: str, good: str, *, runner: Runner) -> BisectStatus:
    _run_ok(root, runner, "bisect", "start")
    _run_ok(root, runner, "bisect", "bad", bad)
    output = _run_ok(root, runner, "bisect", "good", good)
    return _parse_bisect_output(output)


def bisect_mark(root: str, verdict: str, *, runner: Runner) -> BisectStatus:
    if verdict not in ("good", "bad"):
        raise LocalGitError(f"Unknown bisect verdict {verdict!r}; use good or bad.")
    output = _run_ok(root, runner, "bisect", verdict)
    return _parse_bisect_output(output)


def bisect_reset(root: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "bisect", "reset")


def _parse_bisect_output(output: str) -> BisectStatus:
    # git's own wording is "is the first 'bad' commit" (quotes included).
    if "is the first" in output and "commit" in output:
        sha = output.split()[0]
        return BisectStatus(done=True, message=output.strip(), culprit_sha=sha)
    return BisectStatus(done=False, message=output.strip())


# ---------------------------------------------------------------------------
# Merge conflicts: parse marker text into structured hunks a dialog can walk
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConflictHunk:
    """One ``<<<<<<<``/``=======``/``>>>>>>>`` block in a conflicted file."""

    start_line: int  # 0-indexed line of the opening marker
    end_line: int  # 0-indexed line of the closing marker (inclusive)
    ours: tuple[str, ...]
    theirs: tuple[str, ...]
    ours_label: str = "yours"
    theirs_label: str = "theirs"


def parse_conflict_hunks(text: str) -> list[ConflictHunk]:
    """Parse a conflicted file's raw text into structured hunks.

    Pure string parsing, no git call -- callers read the file themselves
    (it's already on disk, mid-conflict) and hand the text here.
    """
    lines = text.splitlines()
    hunks: list[ConflictHunk] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("<<<<<<<"):
            ours_label = lines[i][len("<<<<<<<") :].strip() or "yours"
            start = i
            ours: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("======="):
                ours.append(lines[i])
                i += 1
            theirs: list[str] = []
            i += 1  # skip =======
            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i])
                i += 1
            theirs_label = lines[i][len(">>>>>>>") :].strip() if i < len(lines) else "theirs"
            end = i
            hunks.append(
                ConflictHunk(
                    start_line=start,
                    end_line=end,
                    ours=tuple(ours),
                    theirs=tuple(theirs),
                    ours_label=ours_label or "yours",
                    theirs_label=theirs_label or "theirs",
                )
            )
        i += 1
    return hunks


def resolve_conflict_hunks(text: str, resolutions: Sequence[str]) -> str:
    """Rewrite conflicted *text*, replacing each hunk (in order) with the
    matching entry in *resolutions* -- ``"ours"``, ``"theirs"``, ``"both"``,
    or literal replacement text for a manual edit. Raises if the counts
    don't match, so a caller can never silently resolve the wrong hunk."""
    hunks = parse_conflict_hunks(text)
    if len(hunks) != len(resolutions):
        raise LocalGitError(
            f"{len(hunks)} conflict hunk(s) but {len(resolutions)} resolution(s) given."
        )
    lines = text.splitlines()
    out: list[str] = []
    cursor = 0
    for hunk, resolution in zip(hunks, resolutions, strict=True):
        out.extend(lines[cursor : hunk.start_line])
        if resolution == "ours":
            out.extend(hunk.ours)
        elif resolution == "theirs":
            out.extend(hunk.theirs)
        elif resolution == "both":
            out.extend(hunk.ours)
            out.extend(hunk.theirs)
        else:
            out.extend(resolution.splitlines())
        cursor = hunk.end_line + 1
    out.extend(lines[cursor:])
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def list_conflicted_files(root: str, *, runner: Runner) -> list[str]:
    status = get_status(root, runner=runner)
    return list(status.conflicts)


def mark_conflict_resolved(root: str, path: str, *, runner: Runner) -> None:
    """After writing the resolved content back to disk, stage it -- the same
    step ``git add`` performs to tell git a conflict is resolved."""
    stage_file(root, path, runner=runner)


# ---------------------------------------------------------------------------
# Interactive rebase, spoken: a real todo-list model instead of an editor buffer
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RebaseTodoEntry:
    sha: str
    subject: str
    action: str = "pick"  # pick / squash / reword / drop


@dataclass(frozen=True, slots=True)
class RebaseResult:
    ok: bool
    message: str
    stopped_for_conflicts: bool = False


def build_rebase_todo(root: str, base_ref: str, *, runner: Runner) -> list[RebaseTodoEntry]:
    """The commits between *base_ref* and HEAD, oldest first -- the same set
    ``git rebase -i base_ref`` would open an editor buffer for, as a plain
    list a dialog can render row by row instead."""
    output = _run_ok(root, runner, "log", "--reverse", "--format=%H%x1f%s", f"{base_ref}..HEAD")
    entries: list[RebaseTodoEntry] = []
    for line in output.splitlines():
        if "\x1f" not in line:
            continue
        sha, subject = line.split("\x1f", 1)
        entries.append(RebaseTodoEntry(sha=sha.strip(), subject=subject.strip()))
    return entries


def execute_rebase(
    root: str,
    base_ref: str,
    todo: Sequence[RebaseTodoEntry],
    *,
    runner: Runner,
    sequence_editor_command: Callable[[list[RebaseTodoEntry]], str],
) -> RebaseResult:
    """Run the rebase, substituting *todo* for git's own generated list.

    Real interactive rebase invokes ``$GIT_SEQUENCE_EDITOR <todo-file-path>``
    instead of opening the todo file for a human to hand-edit; setting
    ``sequence.editor`` to a command that writes our own resolved *todo*
    content in place of whatever git generated is the standard mechanism
    every GUI git client uses for a non-interactive-terminal rebase UI.
    *sequence_editor_command* builds that command string (a thin seam so
    tests can inject a fake without touching the filesystem); production
    code passes :func:`default_sequence_editor_command`.
    """
    command = sequence_editor_command(list(todo))
    result = _run(
        root,
        runner,
        "-c",
        f"sequence.editor={command}",
        "rebase",
        "-i",
        base_ref,
        timeout_seconds=120.0,
    )
    if result.returncode == 0:
        return RebaseResult(ok=True, message="Rebase completed.")
    status = get_status(root, runner=runner)
    if status.conflicts:
        return RebaseResult(
            ok=False,
            message=(
                f"Rebase stopped: {len(status.conflicts)} conflict(s). Resolve them, then continue."
            ),
            stopped_for_conflicts=True,
        )
    return RebaseResult(ok=False, message=(result.stderr or "Rebase failed").strip())


def rebase_continue(root: str, *, runner: Runner) -> RebaseResult:
    result = _run(root, runner, "-c", "core.editor=true", "rebase", "--continue")
    if result.returncode == 0:
        return RebaseResult(ok=True, message="Rebase completed.")
    status = get_status(root, runner=runner)
    if status.conflicts:
        return RebaseResult(
            ok=False,
            message=f"Still {len(status.conflicts)} conflict(s) remaining.",
            stopped_for_conflicts=True,
        )
    return RebaseResult(ok=False, message=(result.stderr or "Rebase --continue failed").strip())


def rebase_abort(root: str, *, runner: Runner) -> None:
    _run_ok(root, runner, "rebase", "--abort")


def default_sequence_editor_command(todo: list[RebaseTodoEntry]) -> str:
    """Build a real ``sequence.editor`` command: write *todo* to a temp file,
    plus a tiny standalone driver script that copies it over whatever path
    git appends, then reference both as plain ``"<python>" "<script>"``.

    Deliberately *not* an inline ``python -c "..."`` one-liner with the temp
    path string-interpolated into it: that command string round-trips
    through git-config's own value-escaping (``-c sequence.editor=<value>``
    unescapes backslashes in the value) before the OS ever sees it, so a
    Windows path's backslashes get silently collapsed and the script fails
    with a Python ``SyntaxError`` on the mangled string literal. A driver
    *file* sidesteps this entirely -- the path only appears inside the
    script's own source, written with a normal file write, never re-parsed
    by git-config or a shell.
    """
    lines = "\n".join(f"{entry.action} {entry.sha} {entry.subject}" for entry in todo)
    todo_fd, todo_path = tempfile.mkstemp(prefix="quill-rebase-todo-", suffix=".txt")
    with open(todo_fd, "w", encoding="utf-8") as handle:
        handle.write(lines + "\n")

    script_fd, script_path = tempfile.mkstemp(prefix="quill-rebase-editor-", suffix=".py")
    with open(script_fd, "w", encoding="utf-8") as handle:
        handle.write(f"import shutil, sys\nshutil.copyfile({todo_path!r}, sys.argv[1])\n")
    # Forward slashes even on Windows: Python and git both accept them in a
    # path, and it keeps this command string free of any backslash for the
    # git-config value parser to (mis)interpret.
    python_exe = sys.executable.replace("\\", "/")
    script_forward = script_path.replace("\\", "/")
    return f'"{python_exe}" "{script_forward}"'


__all__ = [
    "BisectStatus",
    "BlameInfo",
    "BranchInfo",
    "ConflictHunk",
    "FileChange",
    "LocalGitError",
    "RebaseResult",
    "RebaseTodoEntry",
    "RepoStatus",
    "StashEntry",
    "SwitchResult",
    "bisect_mark",
    "bisect_reset",
    "bisect_start",
    "blame_line",
    "build_rebase_todo",
    "default_sequence_editor_command",
    "execute_rebase",
    "file_content_at_ref",
    "get_status",
    "list_conflicted_files",
    "list_local_branches",
    "list_stashes",
    "mark_conflict_resolved",
    "parse_conflict_hunks",
    "rebase_abort",
    "rebase_continue",
    "resolve_conflict_hunks",
    "stage_all",
    "stage_file",
    "stash_apply",
    "stash_drop",
    "stash_save",
    "switch_branch",
    "unstage_file",
]
