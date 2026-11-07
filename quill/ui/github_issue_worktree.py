"""Start a GitHub issue or pull request in a separate local worktree."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from quill.core.github.local_repo import detect_github_remotes
from quill.core.local_git import get_status, list_local_branches


def default_worktree_path(root: str, branch: str) -> str:
    """Choose a unique sibling folder without creating or replacing it."""
    base = Path(root).parent / f"{Path(root).name}-{branch.replace('/', '-')}"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = base.with_name(f"{base.name}-{suffix}")
        suffix += 1
    return str(candidate)


def start_issue_worktree(
    frame: Any,
    parent: object,
    repository: str,
    number: int,
    title: str,
    is_pr: bool = False,
) -> None:
    """Confirm and prepare local branch/worktree state; never contact GitHub."""
    if not frame._local_git_ready():
        return
    root = _local_git_root_for_issue(frame, parent, repository)
    if root is None:
        return
    remotes = detect_github_remotes(root)
    if repository.casefold() not in {remote.casefold() for remote in remotes}:
        description = ", ".join(remotes) if remotes else "no GitHub remotes"
        _show_message(
            frame,
            parent,
            f"This checkout has {description}, but none matches {repository}. "
            "Choose a checkout with a matching origin or upstream remote.",
            "Repository Does Not Match",
        )
        return
    try:
        status = get_status(root, runner=frame._local_git_runner())
        branches = list_local_branches(root, runner=frame._local_git_runner())
    except Exception as exc:  # noqa: BLE001 - local Git preflight is user-visible
        _show_message(
            frame, parent, f"Could not inspect this checkout: {exc}", "Local Git Preflight"
        )
        return

    branch_prefix = "pr" if is_pr else "issue"
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")[:48].strip("-")
    base_name = f"{branch_prefix}-{number}" + (f"-{slug}" if slug else "")
    existing = {branch.name.casefold() for branch in branches}
    branch_name = base_name
    suffix = 2
    while branch_name.casefold() in existing:
        branch_name = f"{base_name[:54]}-{suffix}"
        suffix += 1
    from_ref = status.branch if status.branch and status.branch != "HEAD" else "HEAD"
    dirty_note = (
        f"The current checkout has {len(status.changes)} uncommitted change(s). "
        "They stay in the current folder and will not be copied to the new worktree."
        if status.changes
        else "The current checkout is clean."
    )
    kind = "pull request" if is_pr else "issue"
    if not _confirm(
        frame,
        parent,
        f"Prepare a separate local worktree for {repository} {kind} #{number}: {title}\n\n"
        f"The dialog lets you create branch {branch_name!r} or choose an existing branch. "
        f"It starts from local ref {from_ref}. No fetch or GitHub write will happen. "
        f"{dirty_note}\n\nContinue?",
    ):
        frame._set_status("Local worktree creation cancelled")
        return

    from quill.ui.git_worktree_dialogs import NewWorktreeDialog

    request = NewWorktreeDialog(
        parent,
        frame._worktree_branch_names(root),
        default_parent_folder=default_worktree_path(root, branch_name),
        default_branch_name=branch_name,
        default_from_ref=from_ref,
        create_branch_by_default=True,
        announce_cb=frame._announce,
    ).show()
    if request is None:
        frame._set_status("Local worktree creation cancelled")
        return
    from quill.core.git_worktree import add_worktree

    def work(_progress: object) -> object:
        return add_worktree(
            frame._local_git_runner(),
            root,
            request.path,
            request.branch,
            create_branch=request.create_branch,
            from_ref=request.from_ref,
        )

    frame._run_background_task(
        f"Creating {kind} worktree", work, lambda result: frame._set_status(result.message)
    )


def _local_git_root_for_issue(frame: Any, parent: object, repository: str) -> str | None:
    path = getattr(getattr(frame, "document", None), "path", None)
    if path:
        root = frame._local_git_find_root(Path(path))
        if root is not None:
            return str(root)
    wx = frame._wx
    with wx.DirDialog(
        parent,
        f"Choose the local checkout for {repository}",
        style=wx.DD_DEFAULT_STYLE,
    ) as dialog:
        if frame._show_modal_dialog(dialog, "Choose Local Git Checkout") != wx.ID_OK:
            return None
        root = frame._local_git_find_root(Path(dialog.GetPath()))
    if root is None:
        _show_message(
            frame,
            parent,
            "That folder is not inside a Git checkout. Choose a folder with a .git directory.",
            "Git Checkout Required",
        )
        return None
    return str(root)


def _confirm(frame: Any, parent: object, message: str) -> bool:
    test_or_frame_handler = getattr(frame, "_confirm_github_issue_worktree", None)
    if callable(test_or_frame_handler):
        return bool(test_or_frame_handler(parent, message))
    wx = frame._wx
    dialog = wx.MessageDialog(
        parent, message, "Create Local Git Worktree", wx.YES_NO | wx.NO_DEFAULT
    )
    try:
        return frame._show_modal_dialog(dialog, "Create Local Git Worktree") == wx.ID_YES
    finally:
        dialog.Destroy()


def _show_message(frame: Any, parent: object, message: str, title: str) -> None:
    test_handler = getattr(frame, "_show_github_local_message", None)
    if callable(test_handler):
        test_handler(parent, message, title)
        return
    wx = frame._wx
    dialog = wx.MessageDialog(parent, message, title, wx.OK | wx.ICON_INFORMATION)
    try:
        frame._show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()


__all__ = ["default_worktree_path", "start_issue_worktree"]
