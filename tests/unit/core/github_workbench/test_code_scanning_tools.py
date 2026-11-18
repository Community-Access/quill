"""Copilot Autofix, every place an alert was found, and SARIF uploads (GitHub PRD section 19)."""

from __future__ import annotations

import base64
import gzip
from pathlib import Path
from typing import Any

import pytest

from quill.core.github import code_scanning_tools as tools
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class Api:
    def __init__(self, answers: dict[str, Any], fail: dict[str, int] | None = None) -> None:
        self.answers, self.fail = answers, fail or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        key = f"{method} {path}"
        if key in self.fail:
            raise GitHubRestError("no", status=self.fail[key])
        return RestResponse(200, {}, self.answers.get(key, {}))

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError


FIX = "/repos/o/r/code-scanning/alerts/7/autofix"


def test_no_fix_yet_and_asking_for_one() -> None:
    api = Api({f"POST {FIX}": {"status": "pending"}}, fail={f"GET {FIX}": 404})
    assert tools.autofix(api, "o/r", 7).sentence() == "No fix has been asked for yet."
    made = tools.autofix(api, "o/r", 7, ask=True)
    assert made.sentence() == "Copilot Autofix is still making the fix. Ask again in a minute."


def test_a_ready_fix_is_committed_to_a_branch() -> None:
    api = Api({
        f"GET {FIX}": {"status": "success", "description": "Escapes the input."},
        f"POST {FIX}/commits": {"sha": "abcdef1234"},
    })
    fix = tools.autofix(api, "o/r", 7)
    assert fix.ready and fix.sentence() == "Copilot Autofix has a fix ready. Escapes the input."
    said = tools.commit_autofix(api, "o/r", 7, "fix-7", "Fix alert 7")
    assert said == "Committed the fix to fix-7 as abcdef1."
    assert api.sent[-1][2] == {"target_ref": "refs/heads/fix-7", "message": "Fix alert 7"}


def test_every_place_reads_as_a_sentence() -> None:
    api = Api({
        "GET /repos/o/r/code-scanning/alerts/7/instances": [
            {
                "ref": "refs/heads/main",
                "state": "open",
                "location": {"path": "app.py", "start_line": 12},
                "message": {"text": "Unsanitized input."},
            },
            {"state": "fixed", "location": {"path": "old.py"}},
        ]
    })
    assert tools.instances(api, "o/r", 7) == [
        "app.py, line 12 on main, open: Unsanitized input.",
        "old.py, fixed.",
    ]


def test_a_sarif_file_is_gzipped_and_sent_against_the_branch_head(tmp_path: Path) -> None:
    sarif = tmp_path / "eslint.sarif"
    sarif.write_text('{"version": "2.1.0", "runs": []}', encoding="utf-8")
    api = Api({
        "GET /repos/o/r/branches/main": {"commit": {"sha": "c0ffee"}},
        "POST /repos/o/r/code-scanning/sarifs": {"id": "up-1"},
        "GET /repos/o/r/code-scanning/sarifs/up-1": {"processing_status": "complete"},
    })
    said, upload = tools.upload_sarif(api, "o/r", sarif, "main")
    assert said == "Uploaded eslint.sarif for main. GitHub is processing it." and upload == "up-1"
    body = api.sent[-1][2]
    assert body["commit_sha"] == "c0ffee" and body["ref"] == "refs/heads/main"
    assert gzip.decompress(base64.b64decode(body["sarif"])).startswith(b'{"version"')
    assert tools.sarif_status(api, "o/r", "up-1").startswith("GitHub has processed the upload")


def test_a_failed_upload_says_why_and_refusals_are_plain(tmp_path: Path) -> None:
    api = Api({
        "GET /repos/o/r/code-scanning/sarifs/u": {
            "processing_status": "failed",
            "errors": ["bad schema"],
        }
    })
    assert tools.sarif_status(api, "o/r", "u") == "GitHub could not process the upload: bad schema."
    with pytest.raises(tools.CodeScanningError, match="not a file"):
        tools.upload_sarif(api, "o/r", tmp_path / "missing.sarif", "main")
    with pytest.raises(tools.CodeScanningError, match="write access"):
        tools.autofix(Api({}, fail={f"GET {FIX}": 403}), "o/r", 7)
