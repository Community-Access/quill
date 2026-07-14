"""Optional Vault Git Sync (Accessible Vault, Phase 7) — wx-free.

QUILL never hosts sync — the vault is plain files, so any file sync already works. This
adds an opt-in "Sync vault" = commit + pull + push over the user's own git remote, with
**conflict detection** surfaced as a spoken, itemized list ("these N notes changed both
places — keep mine / keep theirs / merge") instead of a visual diff. The subprocess
``runner`` is injected (the app passes ``stability.safe_subprocess.run_subprocess_safely``)
so this stays wx-free and unit-testable with a fake runner.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

#: A subprocess runner: ``runner(command, timeout_seconds=...) -> obj`` with
#: ``returncode``/``stdout``/``stderr`` (mirrors safe_subprocess.run_subprocess_safely).
Runner = Callable[..., object]

#: git status --porcelain codes that mean a merge conflict.
_CONFLICT_CODES = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})


@dataclass(frozen=True, slots=True)
class SyncStep:
    command: tuple[str, ...]
    returncode: int
    output: str


@dataclass(frozen=True, slots=True)
class SyncResult:
    ok: bool
    message: str
    conflicts: tuple[str, ...]
    steps: tuple[SyncStep, ...] = field(default=())


def detect_conflicts(porcelain: str) -> list[str]:
    """Return the conflicted paths from ``git status --porcelain`` output."""
    conflicts: list[str] = []
    for line in porcelain.splitlines():
        if len(line) >= 3 and line[:2] in _CONFLICT_CODES:
            conflicts.append(line[3:].strip())
    return conflicts


def run_vault_sync(
    root: str,
    *,
    runner: Runner,
    commit_message: str = "Vault sync",
    remote: str = "origin",
    branch: str = "main",
    timeout_seconds: float = 120.0,
) -> SyncResult:
    """Commit local changes, pull (detecting conflicts), then push. Returns a summary.

    Stops and reports if a pull leaves conflicts (never force-resolves); the UI then
    offers keep-mine / keep-theirs / merge per file. Any git step failing short-circuits
    with an accessible message. Nothing here writes files itself beyond git.
    """
    steps: list[SyncStep] = []

    def git(*args: str) -> SyncStep:
        result = runner(["git", "-C", root, *args], timeout_seconds=timeout_seconds)
        code = int(getattr(result, "returncode", 1))
        out = (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")
        step = SyncStep(command=("git", *args), returncode=code, output=out)
        steps.append(step)
        return step

    git("add", "-A")
    status = git("status", "--porcelain")
    if status.output.strip():
        commit = git("commit", "-m", commit_message)
        if commit.returncode != 0:
            return SyncResult(False, "Could not commit local changes.", (), tuple(steps))

    pull = git("pull", "--no-edit", remote, branch)
    conflicts = detect_conflicts(git("status", "--porcelain").output)
    if conflicts:
        return SyncResult(
            False,
            f"{len(conflicts)} note(s) changed in both places — resolve, then sync again.",
            tuple(conflicts),
            tuple(steps),
        )
    if pull.returncode != 0:
        return SyncResult(False, "Could not pull remote changes.", (), tuple(steps))

    push = git("push", remote, branch)
    if push.returncode != 0:
        return SyncResult(False, "Local changes are saved, but the push failed.", (), tuple(steps))
    return SyncResult(True, "Vault synced.", (), tuple(steps))


def summarize(result: SyncResult) -> str:
    """One spoken line for the status bar / announcement."""
    return result.message


__all__ = ["SyncStep", "SyncResult", "Runner", "detect_conflicts", "run_vault_sync", "summarize"]
