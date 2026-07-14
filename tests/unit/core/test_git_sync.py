"""Tests for quill.core.git_sync: the general-purpose "sync any folder via
git" engine (Beta 3 QUILL Sync), wx-free, with a scripted fake git runner."""

from __future__ import annotations

from quill.core.git_sync import (
    GitRepoStatus,
    check_repo_status,
    init_repo_with_remote,
    sync_folder_via_git,
)


class _FakeGit:
    """A scripted git runner keyed by the git subcommand (mirrors the Vault
    Sync test convention in tests/unit/core/vault/test_phase7.py)."""

    def __init__(self, responses: dict[str, tuple[int, str]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
        self.calls.append(list(command))
        sub = command[3]
        code, out = self.responses.get(sub, (0, ""))

        class R:
            returncode = code
            stdout = out
            stderr = ""

        return R()


# --- check_repo_status -------------------------------------------------


def test_check_repo_status_not_a_repo() -> None:
    runner = _FakeGit({"rev-parse": (128, "fatal: not a git repository")})
    status = check_repo_status("/some/folder", runner=runner)
    assert status == GitRepoStatus(is_git_repo=False, has_remote=False)
    assert status.ready is False


def test_check_repo_status_repo_no_remote() -> None:
    class _Runner:
        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            sub = command[3]
            if sub == "rev-parse" and "--is-inside-work-tree" in command:
                out, code = "true\n", 0
            elif sub == "rev-parse":  # --abbrev-ref HEAD
                out, code = "main\n", 0
            elif sub == "remote":
                out, code = "", 1  # no origin configured
            else:
                out, code = "", 0

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

    status = check_repo_status("/repo", runner=_Runner())
    assert status.is_git_repo is True
    assert status.has_remote is False
    assert status.ready is False


def test_check_repo_status_repo_with_remote_and_branch() -> None:
    class _Runner:
        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            sub = command[3]
            if sub == "rev-parse" and "--is-inside-work-tree" in command:
                out, code = "true\n", 0
            elif sub == "rev-parse":
                out, code = "feature-x\n", 0
            elif sub == "remote":
                out, code = "https://github.com/o/r.git\n", 0
            else:
                out, code = "", 0

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

    status = check_repo_status("/repo", runner=_Runner())
    assert status.ready is True
    assert status.remote_url == "https://github.com/o/r.git"
    assert status.current_branch == "feature-x"


# --- init_repo_with_remote ------------------------------------------------


def test_init_repo_with_remote_inits_and_adds_remote_when_neither_exists() -> None:
    runner = _FakeGit({"rev-parse": (128, "fatal: not a git repository")})
    result = init_repo_with_remote("/folder", "https://github.com/o/r.git", runner=runner)
    assert result.ok is True
    subs = [c[3] for c in runner.calls]
    assert "init" in subs
    assert "remote" in subs


def test_init_repo_with_remote_skips_init_when_already_a_repo() -> None:
    class _Runner:
        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            sub = command[3]
            if sub == "rev-parse" and "--is-inside-work-tree" in command:
                out, code = "true\n", 0
            elif sub == "rev-parse":
                out, code = "main\n", 0
            elif sub == "remote" and "get-url" in command:
                out, code = "", 1  # no remote yet
            elif sub == "remote" and "add" in command:
                out, code = "", 0
            else:
                out, code = "", 0

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

        calls: list = []

    runner = _Runner()
    result = init_repo_with_remote("/folder", "https://github.com/o/r.git", runner=runner)
    assert result.ok is True


def test_init_repo_with_remote_reports_failed_init() -> None:
    runner = _FakeGit({
        "rev-parse": (128, "fatal: not a git repository"),
        "init": (1, "permission denied"),
    })
    result = init_repo_with_remote("/folder", "https://github.com/o/r.git", runner=runner)
    assert result.ok is False
    assert "repository" in result.message.lower()


# --- sync_folder_via_git ---------------------------------------------------


def test_sync_folder_via_git_declines_when_not_a_repo() -> None:
    runner = _FakeGit({"rev-parse": (128, "fatal: not a git repository")})
    result = sync_folder_via_git("/folder", runner=runner)
    assert result.ok is False
    assert "not set up" in result.message.lower()


def test_sync_folder_via_git_declines_when_no_remote() -> None:
    class _Runner:
        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            sub = command[3]
            if sub == "rev-parse" and "--is-inside-work-tree" in command:
                out, code = "true\n", 0
            elif sub == "rev-parse":
                out, code = "main\n", 0
            elif sub == "remote":
                out, code = "", 1
            else:
                out, code = "", 0

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

    result = sync_folder_via_git("/folder", runner=_Runner())
    assert result.ok is False
    assert "no remote" in result.message.lower()


def test_sync_folder_via_git_uses_the_repos_actual_branch_not_hardcoded_main() -> None:
    calls: list[list[str]] = []

    class _Runner:
        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            calls.append(list(command))
            sub = command[3]
            if sub == "rev-parse" and "--is-inside-work-tree" in command:
                out, code = "true\n", 0
            elif sub == "rev-parse":
                out, code = "master\n", 0  # not "main"
            elif sub == "remote":
                out, code = "https://github.com/o/r.git\n", 0
            elif sub == "status":
                out, code = " M file.md\n", 0  # something to commit, no conflicts
            else:
                out, code = "", 0

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

    result = sync_folder_via_git("/folder", runner=_Runner())
    assert result.ok is True
    assert result.message == "Folder synced."
    # The push/pull steps used the detected branch, not a hardcoded "main".
    push_calls = [c for c in calls if c[3] == "push"]
    assert push_calls and push_calls[0][-1] == "master"


def test_sync_folder_via_git_reports_conflicts_generically() -> None:
    class _Runner:
        def __init__(self) -> None:
            self._status_calls = 0

        def __call__(self, command, *, timeout_seconds):  # noqa: ANN001
            sub = command[3]
            if sub == "rev-parse" and "--is-inside-work-tree" in command:
                out, code = "true\n", 0
            elif sub == "rev-parse":
                out, code = "main\n", 0
            elif sub == "remote":
                out, code = "https://github.com/o/r.git\n", 0
            elif sub == "status":
                self._status_calls += 1
                out = " M file.md\n" if self._status_calls == 1 else "UU file.md\n"
                code = 0
            else:
                out, code = "", 0

            class R:
                returncode = code
                stdout = out
                stderr = ""

            return R()

    result = sync_folder_via_git("/folder", runner=_Runner())
    assert result.ok is False
    assert result.conflicts == ("file.md",)
    assert "file(s) changed in both places" in result.message
