"""New Runner, Runner Labels and Remove Runner (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import runner_admin as ra
from quill.core.github.rest_transport import GitHubRestError, RestResponse

TOKEN = "AABBCCDDEEFF00112233"
DOWNLOADS = [
    {
        "os": "linux",
        "architecture": "x64",
        "download_url": "https://x/linux.tar.gz",
        "filename": "linux.tar.gz",
        "sha256_checksum": "abc",
    },
    {
        "os": "win",
        "architecture": "x64",
        "download_url": "https://x/win.zip",
        "filename": "win.zip",
        "sha256_checksum": "def",
    },
]


class FakeApi:
    def __init__(self, status: dict[str, int] | None = None) -> None:
        self.status = status or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        for part, code in self.status.items():
            if part in f"{method} {path}":
                raise GitHubRestError("no", status=code)
        if path.endswith("/downloads"):
            return RestResponse(200, {}, DOWNLOADS)
        if path.endswith("/registration-token"):
            return RestResponse(201, {}, {"token": TOKEN})
        if method == "GET" and path.endswith("/labels"):
            labels = [
                {"name": "self-hosted", "type": "read-only"},
                {"name": "gpu", "type": "custom"},
            ]
            return RestResponse(200, {}, {"labels": labels})
        return RestResponse(200, {}, {})

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


def test_setup_commands_check_the_download_and_carry_the_token_unspoken() -> None:
    from quill.stability.redaction import redact_known_secrets

    downloads = ra.fetch_downloads(FakeApi(), "o/r")
    assert [d.label for d in downloads] == ["Linux x64", "Windows x64"]
    linux = ra.setup_commands(FakeApi(), "o/r", downloads[0])
    assert 'echo "abc  linux.tar.gz" | shasum -a 256 -c' in linux
    assert f"./config.sh --url https://github.com/o/r --token {TOKEN}" in linux
    windows = ra.setup_commands(FakeApi(), "o/r", downloads[1])
    assert "Get-FileHash -Path win.zip" in windows and "./config.cmd" in windows
    assert TOKEN not in redact_known_secrets(f"the token was {TOKEN}")


def test_labels_and_removal() -> None:
    api = FakeApi()
    assert ra.custom_labels(api, "o/r", "3") == ["gpu"]
    assert ra.add_label(api, "o/r", "3", " gpu2 ") == "Added the label gpu2."
    assert api.sent[-1] == ("POST", "/repos/o/r/actions/runners/3/labels", {"labels": ["gpu2"]})
    assert ra.remove_label(api, "o/r", "3", "gpu") == "Removed the label gpu."
    with pytest.raises(ra.RunnerAdminError, match="cannot be removed"):
        ra.remove_label(FakeApi({"DELETE": 422}), "o/r", "3", "self-hosted")
    assert ra.remove_runner(api, "o/r", "3", "lab-1").startswith("Removed the runner lab-1.")
    assert api.sent[-1][:2] == ("DELETE", "/repos/o/r/actions/runners/3")
    with pytest.raises(ra.RunnerAdminError, match="administration"):
        ra.fetch_downloads(FakeApi({"GET": 403}), "o/r")
    assert ra.RunnerAdminError.code == "QUILL-GITHUB-RUNNER-ADMIN"
