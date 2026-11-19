"""Reusing the GitHub CLI's sign-in: exactly one fixed command, through safe_subprocess.

The table is frozen here on purpose: running any other ``gh`` command, or ``gh``
with other arguments, from the sign-in path is a deliberate change to this test
(as the syntax checkers' ``CHECKER_TOOLS`` is in ``test_problems_outside.py``).
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import gh_sign_in
from quill.core.github.gh_sign_in import GhSignInError, read_gh_token

_TOKEN = "gho_" + "a" * 36


def test_the_one_command_is_frozen() -> None:
    assert gh_sign_in.GH_ARGUMENTS == ("auth", "token", "--hostname", "{host}")
    assert gh_sign_in.TIMEOUT_SECONDS == 15.0


def _runner(stdout: str = _TOKEN, returncode: int = 0, seen: list[Any] | None = None) -> Any:
    def run(args: list[str], *, timeout_seconds: float) -> Any:
        if seen is not None:
            seen.append((list(args), timeout_seconds))
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    return run


def test_it_runs_gh_auth_token_for_the_checked_host_and_returns_the_token() -> None:
    seen: list[Any] = []
    token = read_gh_token("https://GHE.example.com/", gh_path="gh.exe", runner=_runner(seen=seen))
    assert token == _TOKEN
    assert seen == [(["gh.exe", "auth", "token", "--hostname", "ghe.example.com"], 15.0)]


def test_a_host_that_is_not_a_server_name_never_becomes_an_argument() -> None:
    seen: list[Any] = []
    with pytest.raises(GhSignInError):
        read_gh_token("github.com --with-token", gh_path="gh", runner=_runner(seen=seen))
    assert seen == []


def test_gh_not_signed_in_is_said_plainly() -> None:
    with pytest.raises(GhSignInError, match="not signed in to github.com"):
        read_gh_token("github.com", gh_path="gh", runner=_runner("", returncode=1))


def test_an_answer_that_is_not_a_token_is_refused() -> None:
    with pytest.raises(GhSignInError, match="not a GitHub token"):
        read_gh_token("github.com", gh_path="gh", runner=_runner("hello world"))


def test_no_gh_found_says_sign_in_works_without_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.git_binaries.resolve_gh", lambda: None)
    with pytest.raises(GhSignInError, match="did not find the GitHub CLI"):
        read_gh_token("github.com", runner=_runner())


def test_the_default_runner_is_safe_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []
    monkeypatch.setattr("quill.core.git_binaries.resolve_gh", lambda: Path("C:/tools/gh.exe"))
    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", _runner(seen=seen))
    assert read_gh_token("github.com") == _TOKEN
    assert seen[0][0][1:] == ["auth", "token", "--hostname", "github.com"]


def test_the_module_never_opens_gh_files_itself() -> None:
    """It asks gh; it never reads gh's hosts.yml or keyring (no open, no Path reads)."""
    source = Path(gh_sign_in.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "open" not in names
    assert not {"read_text", "read_bytes", "open"} & attrs
    assert "hosts.yml" not in source


def test_the_confirmation_names_the_account_and_host() -> None:
    said = gh_sign_in.confirm_question("kelly", "ghe.example.com", "Windows Credential Manager")
    assert "kelly on ghe.example.com" in said
    assert "does not sign QUILL out" in said
