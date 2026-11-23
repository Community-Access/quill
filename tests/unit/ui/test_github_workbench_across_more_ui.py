"""PRD 22.11 and GX16 in the window: the by-name places grouped category first, Set Secret
Everywhere, Release Train, and what each row offers or says it cannot do.

A real frame over a recorded fake of the Workbench's GitHubApi; nothing leaves the machine.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.navigation_state import account_key_for_token  # noqa: E402
from quill.core.github.repository_sets import RepositorySets  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

TOKEN = "test-token-not-real"


class _Items:
    is_authenticated = True
    token = TOKEN

    def close(self) -> None:
        pass


class FakeApi:
    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
            return SimpleNamespace(status=200, data={}, headers={})
        answer = self.answers.get((method, path))
        if answer is None:
            raise RuntimeError(f"404 Not Found: {path}")
        return SimpleNamespace(status=200, data=answer, headers={})


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), "", announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _choose(*repos: str) -> None:
    sets = RepositorySets.load(account_key_for_token(TOKEN))
    sets.set_repositories("My Repositories", list(repos))
    sets.save()


def _repo(admin: bool = True) -> dict[str, Any]:
    return {"id": 1, "default_branch": "main", "permissions": {"push": True, "admin": admin}}


def test_the_by_name_places_are_grouped_category_first() -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE

    parents = {n.key: n.parent for n in GITHUB_TREE._nodes.values()}
    assert parents["across_by_labels"] == "across_planning"
    assert parents["across_by_tags"] == parents["across_by_rules"] == "across_code"
    assert parents["across_by_secrets"] == "across_actions"
    assert parents["across_by_autolinks"] == "across_settings"
    assert {parents[g] for g in ("across_planning", "across_code", "across_fleet")} == {"across"}


def test_set_secret_everywhere_asks_once_and_never_shows_the_value(bench, monkeypatch) -> None:
    pytest.importorskip("nacl")
    import base64

    from nacl.public import PrivateKey

    key = base64.b64encode(bytes(PrivateKey.generate().public_key)).decode("ascii")
    provider = bench.provider
    _choose("o/one", "o/two")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/actions/secrets"): {"secrets": [{"name": "TOKEN"}]},
        ("GET", "/repos/o/two/actions/secrets"): {"secrets": []},
        ("GET", "/repos/o/one/actions/secrets/public-key"): {"key": key, "key_id": "1"},
        ("GET", "/repos/o/two/actions/secrets/public-key"): {"key": key, "key_id": "2"},
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_secrets"))
    (row,) = bench.rows
    assert row.label == "TOKEN: in 1 of 2 repositories, missing from 1"
    assert provider._fits_across_set_secret(row) and not provider._fits_across_make_same(row)
    assert provider._fits_across_promote_org(row) and provider._fits_across_delete_name(row)
    offered: list[Any] = []
    monkeypatch.setattr(
        provider, "_choose_many", lambda _t, _p, labels, checked: offered.append(checked) or labels
    )
    asked: list[str] = []
    monkeypatch.setattr(provider, "_ask_secret", lambda _t, p: asked.append(p) or "s3cret")
    monkeypatch.setattr(provider, "_across_preview", lambda *_a: True)
    provider._do_across_set_secret(None, row)
    assert offered == [["o/one"]] and len(asked) == 1
    assert [p for _m, p, _b in api.sent] == [
        "/repos/o/one/actions/secrets/TOKEN",
        "/repos/o/two/actions/secrets/TOKEN",
    ]
    assert "s3cret" not in bench.details.GetValue()
    assert bench.details.GetValue().startswith("2 of 2 repositories changed.")


def test_a_release_train_from_a_tag_row(bench, monkeypatch) -> None:
    provider = bench.provider
    _choose("o/one", "o/two")
    api = FakeApi({
        ("GET", "/repos/o/one"): _repo(),
        ("GET", "/repos/o/two"): _repo(),
        ("GET", "/repos/o/one/tags"): [{"name": "v2", "commit": {"sha": "abcdef12"}}],
        ("GET", "/repos/o/two/tags"): [],
        ("GET", "/repos/o/two/git/matching-refs/tags/v2"): [],
    })
    monkeypatch.setattr(provider, "github_api", lambda: api)
    _go(bench, NodeRef("", "across_by_tags"))
    (row,) = bench.rows
    assert provider._fits_across_release_train(row) and not provider._fits_across_add_missing(row)
    monkeypatch.setattr(provider, "_ask_text", lambda *_a, **_kw: "v2")
    monkeypatch.setattr(provider, "_choose", lambda *_a: 2)  # the tag and a published release
    monkeypatch.setattr(provider, "_choose_many", lambda _t, _p, _labels, checked: checked)
    shown: list[Any] = []
    monkeypatch.setattr(
        provider, "_across_preview", lambda _t, plan, _y: shown.append(plan) or True
    )
    provider._do_across_release_train(None, row)
    (plan,) = shown
    assert [s.repository for s in plan.runnable] == ["o/two"]
    ((method, path, body),) = api.sent
    assert (method, path) == ("POST", "/repos/o/two/releases") and body["draft"] is False


def test_a_read_only_account_sets_no_secret(bench, monkeypatch) -> None:
    from quill.core.github.permissions import AccessLevel

    provider = bench.provider
    monkeypatch.setattr(provider, "access_level", lambda: AccessLevel.ORGANIZE)
    from quill.core.github.across_changes import Plan, Step

    plan = Plan("secrets", "TOKEN", "Set the secret", (Step("o/one", "set_secret"),))
    provider._run_plan("across_set_secret", plan, "Set", secret="x")
    assert "needs Full" in bench.said[-1]
