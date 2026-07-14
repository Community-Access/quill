"""QUILL Sync, folder edition: git as the sync engine, for any folder.

Part of "QUILL Sync" (0.9.0 Beta 3): rather than building QUILL's own
sync engine (the large, deferred design in the retired
``docs/planning/quill-sync-plan.md``), QUILL leans on infrastructure that
already exists and is already trusted: git for structured, versioned,
conflict-aware sync over a remote you control (typically GitHub), and the
OS filesystem plus a folder-level cloud client (OneDrive, Dropbox, Google
Drive, iCloud, a NAS, a USB drive) for simple whole-folder replication (see
``core.data_location`` for relocating QUILL's own settings/data folder onto
one of those). QUILL never talks to a cloud provider's API and never hosts a
sync server; a folder is just files, and syncing it is somebody else's
already-solved problem to reuse, not QUILL's to reinvent.

This module is the *generalized* half of that story: the git-sync engine
Accessible Vault's "Sync Vault" already shipped
(:mod:`quill.core.vault.sync`) has no vault-specific logic in it at all — it
takes a bare folder path and three git-plumbing commands (add/commit,
pull, push), nothing more. This module gives that engine a
general-purpose, non-vault-branded home and two small pieces Vault didn't
need: checking whether a folder is even a git repository with a remote yet,
and setting one up (``git init`` + ``git remote add``) when it isn't. The
sync mechanics themselves are not reimplemented here — deliberately, so
there is exactly one commit/pull/push implementation in the tree, exercised
by both Vault Sync and this general "Sync Folder with GitHub" feature.

Like Vault Sync, this relies on the user's own git installation and its own
credential handling (an SSH key, or a stored HTTPS credential via the
system's git credential manager) — QUILL does not store or inject a
separate token for git subprocess calls, matching the existing Vault Sync
contract exactly. wx-free, unit-tested with a fake subprocess runner.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.vault.sync import Runner, SyncResult, SyncStep, run_vault_sync

__all__ = [
    "GitRepoStatus",
    "check_repo_status",
    "init_repo_with_remote",
    "sync_folder_via_git",
]


@dataclass(frozen=True, slots=True)
class GitRepoStatus:
    """Whether *root* is ready for :func:`sync_folder_via_git`."""

    is_git_repo: bool
    has_remote: bool
    remote_url: str = ""
    current_branch: str = ""

    @property
    def ready(self) -> bool:
        return self.is_git_repo and self.has_remote


def _run(root: str, runner: Runner, *args: str, timeout_seconds: float = 30.0) -> SyncStep:
    result = runner(["git", "-C", root, *args], timeout_seconds=timeout_seconds)
    code = int(getattr(result, "returncode", 1))
    out = (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")
    return SyncStep(command=("git", *args), returncode=code, output=out)


def check_repo_status(root: str, *, runner: Runner, timeout_seconds: float = 30.0) -> GitRepoStatus:
    """Return whether *root* is a git repo with a remote, and its branch.

    Best-effort and side-effect-free (no network, no writes): every probe
    tolerates a non-zero exit (not a repo yet, no remote yet, detached HEAD)
    by reporting the negative/empty case rather than raising, so the caller
    can always show a clear next step instead of a stack trace.
    """
    inside = _run(
        root, runner, "rev-parse", "--is-inside-work-tree", timeout_seconds=timeout_seconds
    )
    is_repo = inside.returncode == 0 and "true" in inside.output.lower()
    if not is_repo:
        return GitRepoStatus(is_git_repo=False, has_remote=False)

    remote = _run(root, runner, "remote", "get-url", "origin", timeout_seconds=timeout_seconds)
    has_remote = remote.returncode == 0 and remote.output.strip() != ""
    remote_url = remote.output.strip() if has_remote else ""

    branch = _run(
        root, runner, "rev-parse", "--abbrev-ref", "HEAD", timeout_seconds=timeout_seconds
    )
    current_branch = branch.output.strip() if branch.returncode == 0 else ""

    return GitRepoStatus(
        is_git_repo=True,
        has_remote=has_remote,
        remote_url=remote_url,
        current_branch=current_branch,
    )


def init_repo_with_remote(
    root: str, remote_url: str, *, runner: Runner, timeout_seconds: float = 30.0
) -> SyncResult:
    """Prepare *root* for syncing: ``git init`` (if needed) + add ``origin``.

    Never overwrites an existing ``origin`` — if one is already configured,
    this is a no-op for the remote step (the existing status check already
    told the caller a remote exists, so reaching here with one present would
    mean stale UI state, not something to silently override).
    """
    status = check_repo_status(root, runner=runner, timeout_seconds=timeout_seconds)
    steps: list[SyncStep] = []

    if not status.is_git_repo:
        init_step = _run(root, runner, "init", timeout_seconds=timeout_seconds)
        steps.append(init_step)
        if init_step.returncode != 0:
            return SyncResult(
                False, "Could not turn this folder into a git repository.", (), tuple(steps)
            )

    if not status.has_remote:
        remote_step = _run(
            root, runner, "remote", "add", "origin", remote_url, timeout_seconds=timeout_seconds
        )
        steps.append(remote_step)
        if remote_step.returncode != 0:
            return SyncResult(False, "Could not set the remote repository.", (), tuple(steps))

    return SyncResult(True, "Folder is ready to sync.", (), tuple(steps))


def sync_folder_via_git(
    root: str,
    *,
    runner: Runner,
    commit_message: str = "QUILL sync",
    remote: str = "origin",
    timeout_seconds: float = 120.0,
) -> SyncResult:
    """Commit, pull, and push *root* over its configured git remote.

    The one difference from calling :func:`quill.core.vault.sync.run_vault_sync`
    directly: the branch to sync is detected from the repository itself
    (``git rev-parse --abbrev-ref HEAD``) rather than assumed to be
    ``"main"`` — a general folder the user points this at may just as
    plausibly be on ``master`` or any other branch name, unlike Vault's own
    always-``main`` convention.
    """
    status = check_repo_status(root, runner=runner, timeout_seconds=timeout_seconds)
    if not status.is_git_repo:
        return SyncResult(False, "This folder is not set up for GitHub sync yet.", ())
    if not status.has_remote:
        return SyncResult(False, "This folder has no remote repository configured yet.", ())
    branch = status.current_branch or "main"

    result = run_vault_sync(
        root,
        runner=runner,
        commit_message=commit_message,
        remote=remote,
        branch=branch,
        timeout_seconds=timeout_seconds,
    )
    if result.ok and result.message == "Vault synced.":
        return SyncResult(True, "Folder synced.", result.conflicts, result.steps)
    if not result.ok and result.conflicts:
        message = (
            f"{len(result.conflicts)} file(s) changed in both places — resolve, then sync again."
        )
        return SyncResult(False, message, result.conflicts, result.steps)
    return result
