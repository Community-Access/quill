"""The quick commands: one table, real calls through the Workbench's API, tokens never said."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubCommit, GitHubItem
from quill.core.github.quick_actions import QuickError, call, fill, plain
from quill.core.github.quick_tables import (
    QUICK,
    QUICK_ENDPOINTS,
    QUICK_LIVE,
    QUICK_REQUIREMENTS,
    QUICK_ROWS,
)
from quill.core.github.rest_transport import GitHubRestError
from quill.ui.github_workbench_quick import GitHubWorkbenchQuickMixin, quick_context


class _Reply:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Api:
    def __init__(self, replies: dict[str, Any]) -> None:
        self.replies, self.sent = replies, []

    def rest(self, method: str, path: str, **kw: Any) -> _Reply:
        self.sent.append((method, path, kw.get("body"), kw.get("query")))
        found = self.replies.get(f"{method} {path}")
        if isinstance(found, Exception):
            raise found
        return _Reply(found)

    def graphql(self, _q: str, _v: Any) -> dict[str, Any]:
        return self.replies.get("graphql", {})


class _Frame:
    def __init__(self, key: str, instance: str) -> None:
        self.current = type("Ref", (), {"key": key, "instance": instance})()
        self.copied: list[str] = []
        self.reloads = 0
        self.frame = None

    def copy_text(self, text: str) -> None:
        self.copied.append(text)

    def reload(self) -> None:
        self.reloads += 1


class _Host(GitHubWorkbenchQuickMixin):
    def __init__(self, api: _Api, answers: list[Any], node: str = "", instance: str = "") -> None:
        self.api, self.answers, self.said, self.signed_in = api, answers, [], True
        self.frame = _Frame(node, instance)
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _w, work, done: done(work())  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._confirm = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._ask_text = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]

    def github_api(self) -> Any:
        return self.api


def test_every_table_agrees_with_the_commands() -> None:
    verbs = [q.verb for q in QUICK]
    assert len(verbs) == len(set(verbs))
    for q in QUICK:
        assert callable(getattr(_Host, f"_do_{q.verb}"))
        assert q.endpoints and all(e in QUICK_ENDPOINTS for e in q.endpoints)
        assert any(r.command_id.endswith(q.verb) for t in q.menu for r in QUICK_ROWS[t])
        if q.writes:
            assert q.live.startswith(("needs Jeff:", "not here:")), q.verb
            assert f"github.workbench.{q.verb}" in QUICK_REQUIREMENTS
    assert set(QUICK_LIVE) == {q.verb for q in QUICK if q.writes}


def test_paths_quote_every_part_but_the_repository() -> None:
    assert fill("/repos/{repo}/labels/{key}", {"repo": "o/r", "key": "a b/c"}) == (
        "/repos/o/r/labels/a%20b%2Fc"
    )


def test_a_query_in_the_path_is_sent_as_the_query() -> None:
    api = _Api({"GET /orgs/acme/actions/runners": {"runners": []}})
    call(api, "GET", "/orgs/{org}/actions/runners?per_page=100", {"org": "acme"})
    assert api.sent == [("GET", "/orgs/acme/actions/runners", None, {"per_page": "100"})]


def test_a_refusal_is_said_plainly() -> None:
    api = _Api({"GET /repos/o/r/languages": GitHubRestError("nope", status=404)})
    with pytest.raises(QuickError, match="does not show"):
        call(api, "GET", "/repos/{repo}/languages", {"repo": "o/r"})


def test_plain_reads_any_reply() -> None:
    assert plain({"name": "x", "enabled": True, "url": "u", "owner": {"login": "jo"}}) == (
        "name: x\nenabled: yes\nowner: login: jo"
    )


def test_languages_on_a_repository_row() -> None:
    api = _Api({"GET /repos/o/r/languages": {"Python": 75, "Shell": 25}})
    host = _Host(api, [])
    host._do_languages(None, ExploreRow("o/r", "d", "u", "o/r", "repo", "o/r"))
    assert host.said == ["Languages: Python 75 percent, Shell 25 percent."]


def test_a_runner_token_goes_to_the_clipboard_and_is_never_said() -> None:
    api = _Api({"POST /orgs/acme/actions/runners/remove-token": {"token": "AAAA-SECRET"}})
    host = _Host(api, [], node="org_runners", instance="acme")
    row = ExploreRow("box", "d", "u", "acme", "resource", "org_runners:7")
    assert host._fits_org_runner_removal(row)
    host._do_org_runner_removal(None, row)
    assert "AAAA-SECRET" in host.frame.copied[0]
    assert not any("AAAA-SECRET" in s for s in host.said)


def test_a_pick_then_a_question_then_the_call() -> None:
    api = _Api({
        "GET /repos/o/r/commits/abc/comments": [{"id": 5, "body": "Nice", "user": {"login": "jo"}}],
        "POST /repos/o/r/comments/5/reactions": {"id": 1},
    })  # fmt: skip
    commit = GitHubCommit(sha="abc", short_sha="abc", message="m")
    host = _Host(api, [0, 4], instance="o/r")
    host._do_react_commit_comment(None, commit)
    assert api.sent[-1][:3] == ("POST", "/repos/o/r/comments/5/reactions", {"content": "heart"})
    assert host.said == ["Reacted."]


def test_a_destructive_command_asks_first_and_cancel_sends_nothing() -> None:
    api = _Api({"DELETE /orgs/acme/teams/core": None})
    team = ExploreRow("Core", "d", "u", "acme", "team", "core")
    host = _Host(api, [False])
    host._do_delete_team_now(None, team)
    assert api.sent == []
    host = _Host(api, [True])
    host._do_delete_team_now(None, team)
    assert api.sent == [("DELETE", "/orgs/acme/teams/core", None, None)]
    assert host.frame.reloads == 1


def test_commands_fit_only_their_own_rows_and_node() -> None:
    host = _Host(_Api({}), [], node="runners", instance="o/r")
    view = None
    assert host._fits_repo_jit_runner(view)
    assert not host._fits_org_jit_runner(view)
    host.signed_in = False
    assert not host._fits_repo_jit_runner(view), "a write needs you signed in"
    group = ExploreRow("g", "d", "u", "acme", "resource", "runner_groups:3")
    other = ExploreRow("v", "d", "u", "acme", "resource", "org_variables:X")
    host = _Host(_Api({}), [], node="runner_groups", instance="acme")
    assert host._fits_group_runners(group) and not host._fits_group_runners(other)


def test_a_project_row_knows_its_owner_and_number() -> None:
    row = ExploreRow("Board (#3)", "d", "https://github.com/orgs/acme/projects/3", "acme",
                     "project", "PVT_1")  # fmt: skip
    ctx = quick_context("acme", "projects", row)
    assert (ctx["owner_kind"], ctx["owner"], ctx["pnumber"], ctx["key"]) == (
        "orgs",
        "acme",
        "3",
        "PVT_1",
    )


def test_re_request_review_names_the_reviewers() -> None:
    api = _Api({"POST /repos/o/r/pulls/9/requested_reviewers/rerequest": {}})
    item = GitHubItem(number=9, title="Fix", state="open", url="u", is_pr=True)
    host = _Host(api, ["@ann, bo"], instance="o/r")
    host._do_rerequest_review(None, item)
    assert api.sent[0][2] == {"reviewers": ["ann", "bo"]}
