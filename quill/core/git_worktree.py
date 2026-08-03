"""Git worktrees, made speakable.

A git *worktree* is a second (third, fourth...) folder attached to the same
repository, each with its own branch checked out. Without one, moving between
branches means checking a different branch out **in place**: every file on
disk is rewritten around you, including the document you have open. A sighted
user sees the editor flicker and the tab title change; a screen-reader user
gets no cue at all -- the paragraph under the review cursor is suddenly a
paragraph from another branch, in a file that still claims to be the file they
opened. That is precisely the silent, uncued context switch QUILL works to
avoid everywhere else.

With a worktree, each branch lives at its own path. Nothing under the cursor
ever mutates: switching context becomes "open a different file", which is an
action the user performs and hears, instead of "this file is now a different
file", which simply happens to them. That is the accessibility case for
worktrees, and the reason this module exists.

Scope and shape mirror :mod:`quill.core.local_git`: wx-free, strict-typed, and
driven entirely through an injected ``runner`` (``Runner`` from
:mod:`quill.core.vault.sync` -- ``quill.stability.safe_subprocess.
run_subprocess_safely`` in production, a fake in tests), so nothing here needs
a live repository to be exercised. Every operation returns a
:class:`WorktreeResult`: a success flag, a sentence written to be *spoken*, and
the parsed data. Git's raw stderr is kept in ``detail`` for logs and never
handed to the user as-is.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.vault.sync import Runner

__all__ = [
    "WorktreeEntry",
    "WorktreeError",
    "WorktreeResult",
    "add_worktree",
    "list_worktrees",
    "lock_worktree",
    "move_worktree",
    "parse_worktree_porcelain",
    "prune_worktrees",
    "remove_worktree",
    "unlock_worktree",
]

_DEFAULT_TIMEOUT = 60.0


class WorktreeError(CodedError):
    """Git itself could not be started for a worktree command.

    Raised only for "the tool did not run at all" failures (a missing or
    unlaunchable ``git``, a vanished working directory, a timeout). A git
    command that *runs* and refuses is not an exception -- it comes back as a
    :class:`WorktreeResult` with ``ok=False`` and an explanatory sentence.
    """

    code = "QUILL-GIT-WORKTREE-NO-GIT"


@dataclass(frozen=True, slots=True)
class WorktreeEntry:
    """One worktree attached to a repository, as reported by git."""

    path: str
    branch: str = ""  # short name ("main", "feature/x"); "" when detached or bare
    head: str = ""  # short commit sha; "" for a bare repository
    is_main: bool = False
    is_locked: bool = False
    is_prunable: bool = False
    is_bare: bool = False
    is_detached: bool = False
    lock_reason: str = ""
    prune_reason: str = ""

    def describe(self) -> str:
        """A full sentence a screen reader can read as one list row."""
        kind = "Main worktree" if self.is_main else "Linked worktree"
        if self.is_bare:
            parts = [f"Bare repository at {self.path}"]
        else:
            parts = [f"{kind} at {self.path}"]
            if self.branch:
                parts.append(f"on branch {self.branch}")
            elif self.is_detached:
                commit = self.head or "an unknown commit"
                parts.append(f"not on a branch, at commit {commit}")
        if self.is_locked:
            parts.append(f"locked: {self.lock_reason}" if self.lock_reason else "locked")
        if self.is_prunable:
            parts.append("missing from disk, ready to prune")
        return ", ".join(parts)


@dataclass(frozen=True, slots=True)
class WorktreeResult:
    """The outcome of one worktree operation.

    ``message`` is always a finished, user-facing sentence. ``detail`` holds
    git's own output for the log and for support triage; it is deliberately
    not what a caller announces.
    """

    ok: bool
    message: str
    worktrees: tuple[WorktreeEntry, ...] = ()
    pruned: tuple[str, ...] = ()
    path: str = ""
    command: tuple[str, ...] = field(default=())
    detail: str = ""


@dataclass(frozen=True, slots=True)
class _CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return (self.stderr or self.stdout or "").strip()


def _run(
    root: str, runner: Runner, *args: str, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> _CommandResult:
    """Run ``git <args>`` inside *root* through the injected *runner*.

    ``Runner`` is typed ``Callable[..., object]`` (it wraps whatever
    ``run_subprocess_safely`` or a test fake returns), so ``getattr`` is the
    same seam :mod:`quill.core.local_git` already uses for the same reason.
    """
    try:
        raw = runner(["git", *args], cwd=root, timeout_seconds=timeout_seconds)
    except OSError as exc:
        raise WorktreeError(f"Could not run git in {root}: {exc}") from exc
    return _CommandResult(
        returncode=int(getattr(raw, "returncode", 1)),
        stdout=str(getattr(raw, "stdout", "") or ""),
        stderr=str(getattr(raw, "stderr", "") or ""),
    )


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def parse_worktree_porcelain(text: str) -> tuple[WorktreeEntry, ...]:
    """Parse ``git worktree list --porcelain`` output into entries.

    The format is one record per worktree, records separated by a blank line,
    each line a key with an optional value: ``worktree <path>``, ``HEAD <sha>``,
    ``branch <ref>``, and the valueless-or-reasoned flags ``bare``,
    ``detached``, ``locked [reason]`` and ``prunable [reason]``. The first
    record is always the main worktree.
    """
    entries: list[WorktreeEntry] = []
    record: dict[str, str] = {}

    def flush() -> None:
        if not record.get("worktree"):
            record.clear()
            return
        branch_ref = record.get("branch", "")
        branch = branch_ref.removeprefix("refs/heads/") if branch_ref else ""
        head = record.get("HEAD", "")
        entries.append(
            WorktreeEntry(
                path=record["worktree"],
                branch=branch,
                head=head[:7],
                is_main=not entries,
                is_locked="locked" in record,
                is_prunable="prunable" in record,
                is_bare="bare" in record,
                is_detached="detached" in record,
                lock_reason=record.get("locked", ""),
                prune_reason=record.get("prunable", ""),
            )
        )
        record.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flush()
            continue
        key, _sep, value = line.partition(" ")
        record[key] = value.strip()
    flush()
    return tuple(entries)


def list_worktrees(
    runner: Runner, repo_root: str, *, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> WorktreeResult:
    """Every worktree attached to the repository at *repo_root*."""
    args = ("worktree", "list", "--porcelain")
    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        return WorktreeResult(
            False,
            "QUILL could not read the worktrees for this repository. "
            "Check that this folder is a git repository.",
            command=args,
            detail=result.output,
        )
    entries = parse_worktree_porcelain(result.stdout)
    if not entries:
        return WorktreeResult(True, "No worktrees found.", command=args, detail=result.output)
    if len(entries) == 1:
        message = "1 worktree: just the main one."
    else:
        message = f"{len(entries)} worktrees, including the main one."
    return WorktreeResult(True, message, worktrees=entries, command=args, detail=result.output)


# ---------------------------------------------------------------------------
# Creating
# ---------------------------------------------------------------------------


def _is_inside(candidate: Path, container: Path) -> bool:
    try:
        candidate.relative_to(container)
    except ValueError:
        return False
    return True


def _normalize(path: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(path)))


def _existing_checkout(entries: tuple[WorktreeEntry, ...], branch: str) -> WorktreeEntry | None:
    for entry in entries:
        if entry.branch and entry.branch == branch:
            return entry
    return None


def _refuse_new_path(repo_root: str, path: str) -> str:
    """The user-facing reason *path* cannot host a new worktree, or ``""``."""
    if not path.strip():
        return "Choose a folder for the new worktree first."
    target = _normalize(path)
    root = _normalize(repo_root)
    if target == root or _is_inside(target, root):
        return (
            "A worktree cannot live inside the repository it belongs to. "
            "Pick a folder outside "
            f"{root} -- a sibling folder next to it is the usual choice."
        )
    try:
        if target.exists():
            if not target.is_dir():
                return f"{target} is a file, not a folder. Pick a folder that does not exist yet."
            if any(target.iterdir()):
                return (
                    f"{target} already has files in it. Git needs an empty or "
                    "brand-new folder for a worktree."
                )
    except OSError as exc:
        return f"QUILL could not check {target}: {exc}"
    return ""


def add_worktree(
    runner: Runner,
    repo_root: str,
    path: str,
    branch: str,
    *,
    create_branch: bool = False,
    from_ref: str = "",
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> WorktreeResult:
    """Attach a new worktree at *path*.

    With ``create_branch=False`` this checks out the existing *branch* there
    (``git worktree add <path> <branch>``); with ``create_branch=True`` it
    creates *branch* at that folder (``git worktree add -b <branch> <path>
    [<from_ref>]``). Every refusal -- an occupied path, a path inside the
    repository, a branch already checked out somewhere else -- comes back as a
    sentence explaining what to do instead, never a raw git error.
    """
    if not branch.strip():
        return WorktreeResult(
            False,
            "Name the branch this worktree should use."
            if create_branch
            else "Choose the branch to check out in the new worktree.",
        )
    refusal = _refuse_new_path(repo_root, path)
    if refusal:
        return WorktreeResult(False, refusal, path=path)

    target = str(_normalize(path))
    branch = branch.strip()

    listed = list_worktrees(runner, repo_root, timeout_seconds=timeout_seconds)
    if listed.ok and not create_branch:
        clash = _existing_checkout(listed.worktrees, branch)
        if clash is not None:
            return WorktreeResult(
                False,
                f"Branch {branch} is already checked out at {clash.path}. "
                "A branch can only be checked out in one worktree at a time -- "
                "open that folder instead, or pick another branch.",
                path=target,
            )
    if listed.ok and create_branch and _existing_checkout(listed.worktrees, branch) is not None:
        return WorktreeResult(
            False,
            f"There is already a branch named {branch} checked out in this repository. "
            "Choose a different name for the new branch.",
            path=target,
        )

    if create_branch:
        args: tuple[str, ...] = ("worktree", "add", "-b", branch, target)
        if from_ref.strip():
            args = (*args, from_ref.strip())
    else:
        args = ("worktree", "add", target, branch)

    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        return WorktreeResult(
            False,
            _explain_add_failure(result.output, branch),
            path=target,
            command=args,
            detail=result.output,
        )
    verb = "created" if create_branch else "checked out"
    return WorktreeResult(
        True,
        f"Worktree ready at {target}, with branch {branch} {verb} there.",
        path=target,
        command=args,
        detail=result.output,
    )


def _explain_add_failure(output: str, branch: str) -> str:
    lowered = output.lower()
    if "already checked out" in lowered or "is already used by worktree" in lowered:
        return (
            f"Git says branch {branch} is already checked out in another worktree. "
            "A branch can live in only one worktree at a time."
        )
    if "already exists" in lowered:
        return (
            f"Git says branch {branch} already exists. Clear the "
            "'Create a new branch' checkbox to check the existing one out instead."
        )
    if "not a valid object name" in lowered or "invalid reference" in lowered:
        return "Git did not recognise the branch or starting point you named. Check the spelling."
    if "is not an empty directory" in lowered or "already exists" in lowered:
        return "That folder already has files in it. Choose an empty or brand-new folder."
    return "Git could not create that worktree. Check the folder and branch, then try again."


# ---------------------------------------------------------------------------
# Removing, pruning, moving
# ---------------------------------------------------------------------------


def remove_worktree(
    runner: Runner,
    repo_root: str,
    path: str,
    *,
    force: bool = False,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> WorktreeResult:
    """Detach and delete the worktree at *path*.

    Git refuses when the worktree still holds uncommitted or untracked work.
    That refusal is surfaced verbatim in meaning -- QUILL never quietly adds
    ``--force`` on the user's behalf; ``force=True`` only happens after the
    user has been told what is at stake and has said yes.
    """
    if not path.strip():
        return WorktreeResult(False, "Choose a worktree to remove first.")
    target = str(_normalize(path))
    args: tuple[str, ...] = ("worktree", "remove", target)
    if force:
        args = ("worktree", "remove", "--force", target)
    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        lowered = result.output.lower()
        if "modified or untracked files" in lowered or "use --force" in lowered:
            message = (
                f"{target} still has changes that are not committed. "
                "Commit or discard them there first, or choose Remove again and "
                "confirm that you want to discard them."
            )
        elif "is a main working tree" in lowered:
            message = "That is the repository's main folder, so it cannot be removed as a worktree."
        elif "is locked" in lowered:
            message = f"{target} is locked. Unlock it first, then remove it."
        else:
            message = f"Git could not remove the worktree at {target}."
        return WorktreeResult(False, message, path=target, command=args, detail=result.output)
    return WorktreeResult(
        True,
        f"Removed the worktree at {target}.",
        path=target,
        command=args,
        detail=result.output,
    )


def prune_worktrees(
    runner: Runner, repo_root: str, *, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> WorktreeResult:
    """Forget worktrees whose folders are gone from disk, and say which ones."""
    args = ("worktree", "prune", "--verbose")
    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        return WorktreeResult(
            False,
            "Git could not tidy up the worktree records for this repository.",
            command=args,
            detail=result.output,
        )
    pruned = tuple(
        line.split(":", 1)[0].strip().removeprefix("Removing worktrees/").strip()
        for line in (result.stdout + "\n" + result.stderr).splitlines()
        if line.strip().lower().startswith("removing")
    )
    if not pruned:
        return WorktreeResult(
            True, "Nothing to tidy up: every worktree is still on disk.", command=args
        )
    if len(pruned) == 1:
        message = f"Tidied up 1 worktree record: {pruned[0]}."
    else:
        message = f"Tidied up {len(pruned)} worktree records: {', '.join(pruned)}."
    return WorktreeResult(True, message, pruned=pruned, command=args, detail=result.output)


def move_worktree(
    runner: Runner,
    repo_root: str,
    source: str,
    destination: str,
    *,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> WorktreeResult:
    """Move the worktree at *source* to *destination*, keeping git in step."""
    if not source.strip() or not destination.strip():
        return WorktreeResult(False, "Choose both the worktree to move and where to move it.")
    refusal = _refuse_new_path(repo_root, destination)
    if refusal:
        return WorktreeResult(False, refusal, path=destination)
    src = str(_normalize(source))
    dest = str(_normalize(destination))
    args = ("worktree", "move", src, dest)
    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        lowered = result.output.lower()
        if "is a main working tree" in lowered:
            message = "The repository's main folder cannot be moved this way."
        elif "is locked" in lowered:
            message = f"{src} is locked. Unlock it first, then move it."
        else:
            message = f"Git could not move the worktree from {src} to {dest}."
        return WorktreeResult(False, message, path=src, command=args, detail=result.output)
    return WorktreeResult(
        True, f"Moved the worktree to {dest}.", path=dest, command=args, detail=result.output
    )


# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------


def lock_worktree(
    runner: Runner,
    repo_root: str,
    path: str,
    *,
    reason: str = "",
    timeout_seconds: float = _DEFAULT_TIMEOUT,
) -> WorktreeResult:
    """Lock the worktree at *path* so prune and remove leave it alone.

    Worth doing for a worktree on a removable drive or a network share: git
    would otherwise see the missing folder and consider the worktree prunable.
    """
    if not path.strip():
        return WorktreeResult(False, "Choose a worktree to lock first.")
    target = str(_normalize(path))
    args: tuple[str, ...] = ("worktree", "lock", target)
    if reason.strip():
        args = ("worktree", "lock", "--reason", reason.strip(), target)
    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        lowered = result.output.lower()
        if "already locked" in lowered:
            return WorktreeResult(
                False,
                f"{target} is already locked.",
                path=target,
                command=args,
                detail=result.output,
            )
        return WorktreeResult(
            False,
            f"Git could not lock the worktree at {target}.",
            path=target,
            command=args,
            detail=result.output,
        )
    suffix = f", reason: {reason.strip()}" if reason.strip() else ""
    return WorktreeResult(
        True, f"Locked {target}{suffix}.", path=target, command=args, detail=result.output
    )


def unlock_worktree(
    runner: Runner, repo_root: str, path: str, *, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> WorktreeResult:
    """Unlock the worktree at *path* so it can be pruned or removed again."""
    if not path.strip():
        return WorktreeResult(False, "Choose a worktree to unlock first.")
    target = str(_normalize(path))
    args = ("worktree", "unlock", target)
    result = _run(repo_root, runner, *args, timeout_seconds=timeout_seconds)
    if result.returncode != 0:
        lowered = result.output.lower()
        if "not locked" in lowered:
            return WorktreeResult(
                False,
                f"{target} was not locked.",
                path=target,
                command=args,
                detail=result.output,
            )
        return WorktreeResult(
            False,
            f"Git could not unlock the worktree at {target}.",
            path=target,
            command=args,
            detail=result.output,
        )
    return WorktreeResult(
        True, f"Unlocked {target}.", path=target, command=args, detail=result.output
    )
