"""GitHub CLI codespace handoffs use bounded, argument-vector commands."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from quill.core.github.gh_bridge import (
    GhBridgeError,
    authenticated_login,
    create_codespace,
    list_codespaces,
    open_codespace,
    view_codespace,
)


class FakeRunner:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = iter(outputs)
        self.calls: list[tuple[list[str], float]] = []

    def __call__(self, args: list[str], *, timeout_seconds: float) -> SimpleNamespace:
        self.calls.append((args, timeout_seconds))
        return SimpleNamespace(returncode=0, stdout=next(self.outputs), stderr="")


def _row(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "name": "calm-planet-o1abc234",
        "displayName": "Review workspace",
        "repository": "owner/repo",
        "state": "Available",
        "gitStatus": {"ahead": 2, "behind": 1},
        "createdAt": "2026-11-01T12:00:00Z",
        "lastUsedAt": "2026-11-06T12:00:00Z",
        "machineDisplayName": "2 cores, 8 GB RAM",
        "location": "WestUs2",
    }
    values.update(changes)
    return values


def test_list_and_view_codespaces_preserve_health_and_repository_context() -> None:
    row = _row()
    runner = FakeRunner([json.dumps([row]), json.dumps(row)])

    listed = list_codespaces(gh_path="gh.exe", runner=runner)
    detailed = view_codespace("calm-planet-o1abc234", gh_path="gh.exe", runner=runner)

    assert listed[0].repository == "owner/repo"
    assert listed[0].git_status_ahead == 2
    assert listed[0].git_status_behind == 1
    assert listed[0].last_used_at.startswith("2026-11-06")
    assert detailed.machine_display_name == "2 cores, 8 GB RAM"
    assert detailed.location == "WestUs2"
    assert "--limit" in runner.calls[0][0]
    assert runner.calls[1][0][1:4] == ["codespace", "view", "--codespace"]


def test_codespace_open_targets_the_named_space_and_browser() -> None:
    runner = FakeRunner([""])

    open_codespace("calm-planet-o1abc234", gh_path="gh.exe", runner=runner)

    assert runner.calls[0][0] == [
        "gh.exe",
        "codespace",
        "code",
        "--codespace",
        "calm-planet-o1abc234",
        "--web",
    ]


def test_codespace_name_and_repository_are_validated_before_running() -> None:
    runner = FakeRunner([])

    with pytest.raises(GhBridgeError, match="invalid codespace name"):
        open_codespace("--codespace other", gh_path="gh.exe", runner=runner)
    with pytest.raises(GhBridgeError, match="owner/repo"):
        create_codespace("owner repo", gh_path="gh.exe", runner=runner)

    assert runner.calls == []


def test_authenticated_login_exposes_only_the_login_value() -> None:
    runner = FakeRunner(["my-account\n"])

    assert authenticated_login(gh_path="gh.exe", runner=runner) == "my-account"
    assert runner.calls[0][0] == ["gh.exe", "api", "user", "--jq", ".login"]


def test_authenticated_login_rejects_unexpected_output() -> None:
    runner = FakeRunner(["my account\n"])

    with pytest.raises(GhBridgeError, match="valid signed-in account"):
        authenticated_login(gh_path="gh.exe", runner=runner)
