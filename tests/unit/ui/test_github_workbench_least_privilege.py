"""Account > Roles and Access > Least Privilege Advice, in a real frame (complete.md 1.3).

A recorded ``GET /user`` (with or without ``X-OAuth-Scopes``), the observed-use
record and Change History; the results window is replaced by a recorder.
The report reads once and sends nothing else: no token is changed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github import observed_use  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.observed_use import ObservedUseTracker  # noqa: E402
from quill.core.github.rest_transport import RestResponse  # noqa: E402
from quill.core.github.workbench_view_menu import ROLES_SUB  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
COMMAND = "github.workbench.least_privilege"
TOKEN = "test-token-not-real"


class _Items:
    is_authenticated = True
    token = TOKEN

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(1, "One", "open", "https://github.com/owner/repo/issues/1", False)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def close(self) -> None:
        pass


class _Api:
    def __init__(self, scopes: str | None) -> None:
        self.scopes = scopes
        self.sent: list[tuple[str, str]] = []

    def rest(self, method: str, path: str, **_kw: Any) -> RestResponse:
        self.sent.append((method, path))
        headers = {} if self.scopes is None else {"x-oauth-scopes": self.scopes}
        return RestResponse(200, headers, {"login": "jo"})


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch, tmp_path: Path):
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    tracker = ObservedUseTracker(tmp_path / "use.json")
    monkeypatch.setattr(observed_use, "OBSERVED_USE", tracker)
    said: list[str] = []
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.github_workbench_results.show_results",
        lambda _parent, title, text, **_k: shown.append((title, text)),
    )
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    monkeypatch.setattr(provider, "account_name", lambda: "jo")
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said, frame.shown, frame.tracker = said, shown, tracker  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    assert frame.select(ref)
    yield frame
    provider.stop_watch_timer()
    frame.frame.Destroy()


def test_the_report_is_under_account_with_an_access_key_and_only_reads(bench) -> None:
    row = next(r for r in ROLES_SUB.rows if r is not None and r.command_id == COMMAND)
    assert "&P" in row.label and "Changes nothing" in row.help
    from quill.core.github.write_gate import gated_tier

    assert gated_tier(COMMAND) is None  # a read: never refused, never recorded as a write
    assert bench.provider.supports(COMMAND)


def test_a_classic_token_hears_what_it_never_used(bench) -> None:
    bench.provider.api = api = _Api("repo, admin:org, delete_repo")
    bench.tracker.observe_reply(TOKEN, "GET", "/repos/owner/repo/issues", 200, {})
    # the one gate every command passes (GitHubWorkbenchProvider.run) records a passed write
    assert bench.provider.refused("github.workbench.labels") is False
    bench.run(COMMAND)
    assert api.sent[-1] == ("GET", "/user") and all(m == "GET" for m, _p in api.sent)
    ((title, text),) = bench.shown
    assert title == "Least Privilege Advice"
    assert "Least privilege advice for jo" in text
    assert "This token has: repo, admin:org, delete_repo." in text
    assert "Never used here: admin:org, delete_repo." in text
    assert "What QUILL cannot know" in text
    use = bench.tracker.use_for(TOKEN)
    assert "github.workbench.labels" in use.commands


def test_a_fine_grained_token_is_said_to_list_no_permissions(bench) -> None:
    bench.provider.api = _Api(None)
    bench.run(COMMAND)
    text = bench.shown[-1][1]
    assert "This token sends no scopes, so it is a fine-grained token or an app's." in text
    assert "GitHub does not list a fine-grained token's exact permissions" in text
