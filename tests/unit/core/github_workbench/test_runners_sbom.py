"""Self-hosted runners and the software bill of materials (GitHub PRD 14.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.github import runners_sbom as rs
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class FakeApi:
    def __init__(self, data: Any = None, status: int = 0) -> None:
        self.data, self.status = data, status
        self.sent: list[str] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append(path)
        if self.status:
            raise GitHubRestError("no", status=self.status)
        return RestResponse(200, {}, self.data)

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_runners_say_state_system_and_labels() -> None:
    api = FakeApi({
        "runners": [
            {
                "id": 3,
                "name": "lab-1",
                "os": "Linux",
                "status": "online",
                "busy": True,
                "labels": [{"name": "self-hosted"}, {"name": "gpu"}],
            },
            {"id": 4, "name": "old", "os": "Windows", "status": "offline", "busy": False},
        ]
    })
    rows = rs.fetch_runners(api, "o/r")
    assert [row.label for row in rows] == ["lab-1: online, busy, Linux", "old: offline, Windows"]
    assert rows[0].detail == "Runner lab-1, online, busy, on Linux. Labels: self-hosted, gpu."
    assert rows[0].kind == "runner" and rows[0].url.endswith("/o/r/settings/actions/runners")


def test_runners_need_an_administrator_and_say_so() -> None:
    with pytest.raises(rs.RunnersError, match="only to its administrators"):
        rs.fetch_runners(FakeApi(status=403), "o/r")


def test_the_bill_of_materials_is_saved_as_spdx(tmp_path: Path) -> None:
    sbom = {"spdxVersion": "SPDX-2.3", "packages": [{"name": "a"}, {"name": "b"}]}
    target = tmp_path / rs.sbom_name("o/r")
    said = rs.save_sbom(FakeApi({"sbom": sbom}), "o/r", target)
    assert said == "Saved o-r.spdx.json: 2 packages, in SPDX format."
    assert json.loads(target.read_text(encoding="utf-8")) == sbom
    with pytest.raises(rs.RunnersError, match="no dependency graph"):
        rs.save_sbom(FakeApi(status=404), "o/r", target)
    assert rs.RunnersError.code == "QUILL-GITHUB-RUNNERS-SBOM"
