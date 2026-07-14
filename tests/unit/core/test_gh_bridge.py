"""Unit tests for quill.core.github.gh_bridge.

Uses a fake subprocess runner (mirroring test_git_sync.py / test_local_git.py's
convention) rather than a real `gh` install -- these tests prove the argument
building and JSON parsing are correct; they do NOT prove `gh` itself behaves
this way against a real Codespaces-enabled repository or real Copilot CLI
access, which is exactly the "needs live-device verification" gap the module
docstring calls out.
"""

from __future__ import annotations

import json

import pytest

from quill.core.github import gh_bridge as gb


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.responses: list[_Result] = []

    def __call__(self, args: list[str], *, timeout_seconds: float = 30.0) -> _Result:
        self.calls.append(args)
        if self.responses:
            return self.responses.pop(0)
        return _Result()


@pytest.fixture
def runner() -> _FakeRunner:
    return _FakeRunner()


# ---------------------------------------------------------------------------
# Codespaces
# ---------------------------------------------------------------------------


def test_list_codespaces_parses_json(runner: _FakeRunner) -> None:
    payload = [
        {
            "name": "improved-guacamole-abc123",
            "displayName": "improved guacamole",
            "repository": "owner/repo",
            "state": "Available",
            "gitStatus": {"ahead": 1, "behind": 0},
            "createdAt": "2026-01-01T00:00:00Z",
        }
    ]
    runner.responses.append(_Result(stdout=json.dumps(payload)))
    result = gb.list_codespaces(gh_path="gh", runner=runner)
    assert len(result) == 1
    assert result[0].name == "improved-guacamole-abc123"
    assert result[0].git_status_ahead == 1
    assert runner.calls[0][:3] == ["gh", "codespace", "list"]


def test_list_codespaces_empty_output_is_empty_list(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout=""))
    assert gb.list_codespaces(gh_path="gh", runner=runner) == []


def test_list_codespaces_raises_on_nonzero_exit(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(returncode=1, stderr="not authenticated"))
    with pytest.raises(gb.GhBridgeError, match="not authenticated"):
        gb.list_codespaces(gh_path="gh", runner=runner)


def test_list_codespaces_raises_on_malformed_json(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout="not json"))
    with pytest.raises(gb.GhBridgeError, match="Could not parse"):
        gb.list_codespaces(gh_path="gh", runner=runner)


def test_create_codespace_builds_correct_args_and_returns_info(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout=json.dumps({"name": "new-codespace-xyz"})))
    runner.responses.append(
        _Result(
            stdout=json.dumps([
                {
                    "name": "new-codespace-xyz",
                    "displayName": "new codespace",
                    "repository": "owner/repo",
                    "state": "Provisioning",
                    "gitStatus": {},
                    "createdAt": "",
                }
            ])
        )
    )
    info = gb.create_codespace("owner/repo", branch="feature", gh_path="gh", runner=runner)
    assert info.name == "new-codespace-xyz"
    assert info.repository == "owner/repo"
    create_call = runner.calls[0]
    assert create_call[:4] == ["gh", "codespace", "create", "--repo"]
    assert "--branch" in create_call and "feature" in create_call


def test_create_codespace_without_branch(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout=json.dumps({"name": "cs1"})))
    runner.responses.append(_Result(stdout="[]"))
    info = gb.create_codespace("owner/repo", gh_path="gh", runner=runner)
    assert info.name == "cs1"
    assert "--branch" not in runner.calls[0]


def test_create_codespace_raises_without_a_name(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout=json.dumps({})))
    with pytest.raises(gb.GhBridgeError, match="did not report"):
        gb.create_codespace("owner/repo", gh_path="gh", runner=runner)


def test_stop_codespace(runner: _FakeRunner) -> None:
    gb.stop_codespace("cs1", gh_path="gh", runner=runner)
    assert runner.calls[0] == ["gh", "codespace", "stop", "--codespace", "cs1"]


def test_delete_codespace_uses_force_flag(runner: _FakeRunner) -> None:
    gb.delete_codespace("cs1", gh_path="gh", runner=runner)
    assert runner.calls[0] == ["gh", "codespace", "delete", "--codespace", "cs1", "--force"]


def test_codespace_ssh_config_returns_raw_output(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout="Host cs1\n  HostName ...\n"))
    result = gb.codespace_ssh_config("cs1", gh_path="gh", runner=runner)
    assert "Host cs1" in result
    assert runner.calls[0] == ["gh", "codespace", "ssh", "--codespace", "cs1", "--config"]


# ---------------------------------------------------------------------------
# Copilot suggest / explain
# ---------------------------------------------------------------------------


def test_copilot_suggest_passes_query(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout="git reset --soft HEAD~1"))
    result = gb.copilot_suggest("undo my last commit but keep changes", gh_path="gh", runner=runner)
    assert result == "git reset --soft HEAD~1"
    assert runner.calls[0] == [
        "gh",
        "copilot",
        "suggest",
        "-t",
        "shell",
        "undo my last commit but keep changes",
    ]


def test_copilot_explain_passes_command(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(stdout="This resets your branch..."))
    result = gb.copilot_explain("git reset --soft HEAD~1", gh_path="gh", runner=runner)
    assert "resets" in result
    assert runner.calls[0] == ["gh", "copilot", "explain", "git reset --soft HEAD~1"]


def test_copilot_suggest_raises_on_failure(runner: _FakeRunner) -> None:
    runner.responses.append(_Result(returncode=1, stderr="copilot extension not installed"))
    with pytest.raises(gb.GhBridgeError, match="not installed"):
        gb.copilot_suggest("anything", gh_path="gh", runner=runner)
