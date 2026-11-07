"""Starting GitHub work in a local worktree stays local and preserves work."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.ui.git_worktree_dialogs import NewWorktreeRequest
from quill.ui.github_issue_worktree import start_issue_worktree
from quill.ui.main_frame_worktrees import WorktreesMixin


class _Runner:
    def __init__(self, *, conflicting_branch: bool = False) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.conflicting_branch = conflicting_branch

    def __call__(self, command, *, cwd, timeout_seconds):
        args = tuple(command[1:])
        self.calls.append(args)
        output = ""
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            output = "main\n"
        elif args == ("status", "--porcelain=v1"):
            output = " M README.md\n?? notes.txt\n"
        elif args == ("branch", "--format=%(HEAD)%09%(refname:short)"):
            output = "*\tmain\n"
            if self.conflicting_branch:
                output += " \tissue-17-fix-crash-on-open\n"
        elif args == ("worktree", "list", "--porcelain"):
            output = "worktree C:/repo\nHEAD abcdef0\nbranch refs/heads/main\n"
        return SimpleNamespace(returncode=0, stdout=output, stderr="")


class _NewWorktreeDialog:
    options: dict[str, object] = {}

    def __init__(self, _parent, _branches, **options) -> None:
        type(self).options = options

    def show(self) -> NewWorktreeRequest:
        return NewWorktreeRequest(
            path=str(self.options["default_parent_folder"]),
            branch=str(self.options["default_branch_name"]),
            create_branch=bool(self.options["create_branch_by_default"]),
            from_ref=str(self.options["default_from_ref"]),
        )


class _Frame(WorktreesMixin):
    def __init__(self, root: Path, *, conflicting_branch: bool = False) -> None:
        self.root = root
        self.runner = _Runner(conflicting_branch=conflicting_branch)
        self._wx = SimpleNamespace()
        self._announce = lambda _message: None
        self.document = SimpleNamespace(path=root / "README.md")
        self.confirmation = ""
        self.messages: list[str] = []
        self.task = None

    def _local_git_ready(self) -> bool:
        return True

    def _local_git_root_for_issue(self, _parent, _repository: str) -> str:
        return str(self.root)

    def _local_git_find_root(self, _path: Path) -> Path:
        return self.root

    def _local_git_runner(self):
        return self.runner

    def _confirm_github_issue_worktree(self, _parent, message: str) -> bool:
        self.confirmation = message
        return True

    def _show_github_local_message(self, _parent, message: str, _title: str) -> None:
        self.messages.append(message)

    def _run_background_task(self, _label, work, completed) -> None:
        self.task = (work, completed)

    def _set_status(self, message: str) -> None:
        self.messages.append(message)


def _repository(root: Path, remotes: tuple[tuple[str, str], ...]) -> None:
    config = root / ".git" / "config"
    config.parent.mkdir(parents=True)
    config.write_text(
        "".join(f'[remote "{name}"]\n\turl = {url}\n' for name, url in remotes),
        encoding="utf-8",
    )


def test_issue_handoff_uses_matching_upstream_and_keeps_dirty_changes_in_place(
    monkeypatch, tmp_path: Path
) -> None:
    import quill.ui.git_worktree_dialogs as dialogs

    root = tmp_path / "fork"
    root.mkdir()
    _repository(
        root,
        (
            ("origin", "https://github.com/alice/quill.git"),
            ("upstream", "https://github.com/Community-Access/quill.git"),
        ),
    )
    monkeypatch.setattr(dialogs, "NewWorktreeDialog", _NewWorktreeDialog)
    frame = _Frame(root, conflicting_branch=True)

    start_issue_worktree(frame, object(), "community-access/QUILL", 17, "Fix crash on open")

    assert "2 uncommitted change(s)" in frame.confirmation
    assert "stay in the current folder" in frame.confirmation
    assert _NewWorktreeDialog.options["default_branch_name"] == "issue-17-fix-crash-on-open-2"
    assert _NewWorktreeDialog.options["default_from_ref"] == "main"
    assert str(_NewWorktreeDialog.options["default_parent_folder"]).startswith(str(tmp_path))
    assert frame.task is not None
    work, completed = frame.task
    result = work(None)
    completed(result)
    assert result.ok
    assert "issue-17-fix-crash-on-open-2" in frame.messages[-1]
    assert not any(call and call[0] in {"fetch", "push"} for call in frame.runner.calls)


def test_issue_handoff_refuses_a_checkout_for_an_unrelated_repository(tmp_path: Path) -> None:
    root = tmp_path / "other"
    root.mkdir()
    _repository(root, (("origin", "https://github.com/other/repo.git"),))
    frame = _Frame(root)

    start_issue_worktree(frame, object(), "owner/repo", 3, "Do work")

    assert frame.messages
    assert "none matches owner/repo" in frame.messages[0]
    assert frame.task is None
    assert not frame.runner.calls
