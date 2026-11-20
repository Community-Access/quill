"""Roles and Access in the Workbench window: the commands show GitHub's answers, and Act As
sends one action as the account named, held to that account's own level.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.permissions import AccessLevel, AccessStore  # noqa: E402
from quill.core.github.rest_transport import RestResponse  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.github_api_fake import FakeGitHubApi  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."
_PR = GitHubItem(7, "Fix it", "open", "https://github.com/owner/repo/pull/7", True)


class _Items:
    is_authenticated = True
    token = "gho_mine"
    last_scopes_header = "repo"

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [_PR]

    def search_items(self, _repo: str, query: str, **_kw: Any) -> list[GitHubItem]:
        return []

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


_ME = SimpleNamespace(id="a" * 32, login="me", host="github.com", level_key="me")
_OTHER = SimpleNamespace(id="b" * 32, login="me-test", host="github.com", level_key="me-test")
for _account in (_ME, _OTHER):
    _account.display_name = f"{_account.login} ({_account.host})"


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    api = FakeGitHubApi()
    provider.api = api
    provider.batch_pace = 0
    other_api = FakeGitHubApi()
    monkeypatch.setattr(provider, "account_name", lambda: "me")
    monkeypatch.setattr(provider, "_accounts", lambda: ([_ME, _OTHER], _ME.id))
    monkeypatch.setattr(provider, "_account_api", lambda a: api if a is _ME else other_api)
    monkeypatch.setattr("quill.core.github.accounts.load_github_account_token", lambda _id: "gho_x")
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.github_workbench_results.show_results",
        lambda _parent, title, text, **_kw: shown.append((title, text)),
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    frame.said = said  # type: ignore[attr-defined]
    frame.shown = shown  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.other_api = other_api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _answers(provider: Any, monkeypatch, choices: list[int], confirm: bool = True) -> list[str]:
    asked: list[str] = []

    def choose(title: str, prompt: str, labels: list[str]) -> int:
        asked.append(prompt)
        return choices.pop(0)

    monkeypatch.setattr(provider, "_choose", choose)
    monkeypatch.setattr(provider, "_confirm", lambda title, q: asked.append(q) or confirm)
    return asked


def test_my_access_shows_what_github_said(bench) -> None:
    bench.api.answer(
        "GET",
        f"/repos/{REPO}",
        {"permissions": {"push": True, "pull": True}, "owner": {"type": "User"}},
    )
    bench.run(f"{_P}my_access")
    title, text = bench.shown[-1]
    assert title == "My Access Here"
    assert f"You have write access to {REPO}. (GitHub: /repos/{REPO} permissions)" in text
    assert "scopes are repo" in text


def test_act_as_approves_as_the_named_account_and_says_so(bench, monkeypatch) -> None:
    bench.other_api.answer("GET", "/user", {"login": "me-test"})
    monkeypatch.setattr(bench, "selected_row", lambda: _PR)
    asked = _answers(bench.provider, monkeypatch, [0, 0])  # me-test, then Approve
    bench.run(f"{_P}act_as")
    assert ("POST", f"/repos/{REPO}/pulls/7/reviews", {"event": "APPROVE"}) in bench.other_api.calls
    assert bench.api.writes() == []  # the Workbench's own account sent nothing
    assert asked[-1].startswith("As me-test on github.com, not as you")
    assert bench.said[-1] == f"Approved pull request #7 in {REPO} as me-test."


def test_act_as_sends_nothing_when_the_token_is_somebody_elses(bench, monkeypatch) -> None:
    bench.other_api.answer("GET", "/user", {"login": "mallory"})
    monkeypatch.setattr(bench, "selected_row", lambda: _PR)
    _answers(bench.provider, monkeypatch, [0, 0])
    bench.run(f"{_P}act_as")
    assert bench.other_api.writes() == []
    assert bench.said[-1].startswith("Cannot act as me-test on github.com")


def test_act_as_is_held_to_the_other_accounts_own_level(bench, monkeypatch) -> None:
    AccessStore.load().set("me-test", AccessLevel.READ_ONLY)
    monkeypatch.setattr(bench, "selected_row", lambda: _PR)
    asked = _answers(bench.provider, monkeypatch, [0, 0])
    bench.run(f"{_P}act_as")
    assert bench.other_api.calls == []
    assert bench.said[-1].startswith("Cannot approve pull request #7 in owner/repo as me-test")
    assert not any(q.startswith("As me-test") for q in asked)  # refused before asking


def test_compare_accounts_asks_each_account_with_its_own_sign_in(bench, monkeypatch) -> None:
    for api, login, role in ((bench.api, "me", "admin"), (bench.other_api, "me-test", "read")):
        api.answer("GET", "/user", RestResponse(200, {"x-oauth-scopes": "repo"}, {"login": login}))
        api.answer(
            "GET",
            f"/repos/{REPO}/collaborators/{login}/permission",
            {"permission": role, "role_name": role},
        )
    _answers(bench.provider, monkeypatch, [1])
    bench.run(f"{_P}compare_accounts")
    title, text = bench.shown[-1]
    assert title == f"Compare Accounts: {REPO}"
    assert "me (github.com): admin." in text and "me-test (github.com): read." in text
    assert "What me (github.com) may do that me-test (github.com) may not" in text


def test_bulk_access_previews_per_person_and_sends_only_real_changes(bench, monkeypatch) -> None:
    bench.api.answer(
        "GET",
        "/repos/o/a/collaborators/kelly/permission",
        {"permission": "write", "role_name": "write"},
    )
    bench.api.answer(
        "GET",
        "/repos/o/b/collaborators/kelly/permission",
        {"permission": "admin", "role_name": "maintain"},
    )
    texts = iter(["kelly", "o/a, o/b"])
    monkeypatch.setattr(bench.provider, "_ask_text", lambda *a, **k: next(texts))
    _answers(bench.provider, monkeypatch, [1, 3])  # person, maintain
    previews: list[str] = []
    monkeypatch.setattr(
        bench.provider, "confirm_tier", lambda tier, words, name: previews.append(words) or True
    )
    bench.run(f"{_P}bulk_access")
    assert previews == ["kelly on o/a: write now, maintain after."]
    assert bench.api.writes() == [
        ("PUT", "/repos/o/a/collaborators/kelly", {"permission": "maintain"})
    ]
