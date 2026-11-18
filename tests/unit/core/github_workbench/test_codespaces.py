"""Codespaces in the GitHub Workbench (GitHub PRD section 19)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import codespaces as cs
from quill.core.github.rest_transport import GitHubRestError, RestResponse

SPACE = {
    "name": "jeff-quill-abc",
    "display_name": "sturdy fiesta",
    "repository": {"full_name": "community-access/quill"},
    "git_status": {"ref": "main"},
    "state": "Available",
    "machine": {"display_name": "4 cores, 16 GB RAM"},
    "last_used_at": "2026-11-17T10:00:00Z",
    "web_url": "https://sturdy-fiesta.github.dev",
}


class Api:
    def __init__(self, answers: dict[str, Any] | None = None, fail: dict[str, int] | None = None):
        self.answers, self.fail = answers or {}, fail or {}
        self.sent: list[tuple[str, str, Any, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body, query))
        key = f"{method} {path}"
        if key in self.fail:
            raise GitHubRestError("no", status=self.fail[key])
        return RestResponse(200, {}, self.answers.get(key, {}))

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_a_codespace_reads_as_a_sentence_and_opens_its_sheet() -> None:
    from quill.core.github.sheet_catalog import target_for

    api = Api({"GET /user/codespaces": {"codespaces": [SPACE]}})
    row = cs.fetch(api)[0]
    assert row.label == (
        "sturdy fiesta: community-access/quill on main, Available, 4 cores, 16 GB RAM, "
        "used 2026-11-17."
    )
    assert row.kind == "codespace" and row.key == "jeff-quill-abc"
    target = target_for(row)
    assert target is not None and target.kind == "codespace"
    warnings: list[str] = []
    assert cs.fetch(Api(), "o/r", warnings) == [] and warnings == [
        "No codespaces yet. Ctrl+N makes one."
    ]


def test_making_one_reads_the_choices_and_github_s_defaults() -> None:
    api = Api({
        "GET /repos/o/r/codespaces/machines": {
            "machines": [{"name": "basicLinux32gb", "display_name": "2-core", "cpus": 2}]
        },
        "GET /repos/o/r/codespaces/devcontainers": {
            "devcontainers": [{"path": ".devcontainer/devcontainer.json", "name": "Default"}]
        },
        "GET /repos/o/r/codespaces/new": {
            "defaults": {"devcontainer_path": ".devcontainer/devcontainer.json"}
        },
        "GET /repos/o/r/codespaces/permissions_check": {"accepted": True},
        "POST /repos/o/r/codespaces": {"display_name": "sturdy fiesta"},
    })
    found = cs.new_choices(api, "o/r", "main")
    assert found.allowed and found.machines[0].label == "2-core (2 cores)"
    assert found.default_container == ".devcontainer/devcontainer.json"
    said = cs.create(api, "o/r", "main", "basicLinux32gb", found.default_container)
    assert said.startswith("Making the codespace sturdy fiesta for o/r on main.")
    assert api.sent[-1][2] == {
        "ref": "main",
        "machine": "basicLinux32gb",
        "devcontainer_path": ".devcontainer/devcontainer.json",
    }


def test_start_stop_delete_machine_export_and_publish() -> None:
    base = "/user/codespaces/jeff-quill-abc"
    api = Api({
        f"POST {base}/exports": {"id": "latest"},
        f"GET {base}/exports/latest": {"state": "succeeded", "branch": "codespace-abc"},
        f"POST {base}/publish": {"repository": {"full_name": "jeff/new-thing"}},
    })
    assert cs.start(api, "jeff-quill-abc") == "Starting jeff-quill-abc."
    assert cs.stop(api, "jeff-quill-abc").startswith("Stopping")
    assert cs.delete(api, "jeff-quill-abc").startswith("Deleted jeff-quill-abc.")
    said, export_id = cs.export(api, "jeff-quill-abc")
    assert (
        cs.export_status(api, "jeff-quill-abc", export_id)
        == "Exported to the branch codespace-abc."
    )
    assert (
        cs.publish(api, "jeff-quill-abc", "new-thing", True)
        == "Published jeff-quill-abc to jeff/new-thing."
    )
    machine = cs.Choice("premiumLinux", "8-core")
    assert (
        cs.set_machine(api, "jeff-quill-abc", machine)
        == "jeff-quill-abc will use 8-core from its next start."
    )
    assert api.sent[-1][:3] == ("PATCH", base, {"machine": "premiumLinux"})


def test_a_spending_limit_and_a_refusal_are_said_plainly() -> None:
    with pytest.raises(cs.CodespaceError, match="spending limit"):
        cs.start(Api(fail={"POST /user/codespaces/x/start": 402}), "x")
    with pytest.raises(cs.CodespaceError, match="codespace permission"):
        cs.fetch(Api(fail={"GET /user/codespaces": 403}))
