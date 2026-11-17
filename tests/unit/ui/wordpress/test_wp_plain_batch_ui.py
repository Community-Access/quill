"""Plain-Language Batch in the Workbench window (WP-R-021): Trash with Undo, and questions.

The real provider and frame over a fake site with drafts of different ages;
dialogs answer from queues and work runs inline. A question changes nothing;
a Trash batch shows its checklist first and Ctrl+Z (the history's Undo) puts
the items back.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from tests.unit.ui.wordpress.test_wp_qaf_spam_ui import REF, SITE, FakeApi, _make  # noqa: E402


class PostsApi(FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.posts = [
            {"id": 1, "type": "post", "status": "draft", "date": "2020-01-01T10:00:00",
             "modified_gmt": "2020-01-01T10:00:00", "title": {"raw": "Old draft"}},
            {"id": 2, "type": "post", "status": "draft", "date": "2099-01-01T10:00:00",
             "modified_gmt": "2099-01-01T10:00:00", "title": {"raw": "New draft"}},
        ]  # fmt: skip

    def _post(self, ident: int) -> dict[str, Any]:
        return next(p for p in self.posts if p["id"] == ident)

    def get(self, route: str, **params: Any) -> Any:
        if route.startswith("wp/v2/posts/"):
            return dict(self._post(int(route.rsplit("/", 1)[1])))
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        params = dict(params or {})
        if route != "wp/v2/posts":
            return
        for post in self.posts:
            if params.get("status") not in ("any", post["status"]):
                continue
            if "before" in params and not post["date"] < params["before"]:
                continue
            yield dict(post)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route.startswith("wp/v2/posts/"):
            self.sent.append(("POST", route, body))
            self._post(int(route.rsplit("/", 1)[1])).update(body or {})
            return dict(self._post(int(route.rsplit("/", 1)[1])))
        return super().post(route, body, **params)

    def delete(self, route: str, **params: Any) -> Any:
        if route.startswith("wp/v2/posts/"):
            self.sent.append(("DELETE", route, None))
            self._post(int(route.rsplit("/", 1)[1]))["status"] = "trash"
            return {"status": "trash"}
        return super().delete(route, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path, monkeypatch):
    frame = _make(monkeypatch, tmp_path, PostsApi())
    frame.checks = []  # type: ignore[attr-defined]

    def ask_checks(*_a: Any, **k: Any) -> list[int] | None:
        frame.checks.append(k)  # type: ignore[attr-defined]
        return list(k["checked"])

    monkeypatch.setattr(wdlg, "ask_checks", ask_checks)
    yield frame
    frame.frame.Destroy()


def test_a_question_is_answered_and_nothing_is_sent(bench) -> None:
    bench.answers.texts += ["how many drafts are older than a year?"]
    bench.provider.do_plain_batch(REF, None)
    assert bench.said[-1] == f"Draft posts older than a year: 1 on {SITE}."
    assert bench.checks == [] and bench.api.sent == []


def test_trash_shows_its_checklist_moves_the_old_draft_and_undo_puts_it_back(bench) -> None:
    api = bench.api
    bench.answers.texts += ["move every draft older than a year to Trash"]
    bench.provider.do_plain_batch(REF, None)
    checklist = bench.checks[-1]
    assert checklist["rows"] == [f"{SITE}: Old draft"]
    assert "Ctrl+Z puts them back" in checklist["help_text"]
    assert ("DELETE", "wp/v2/posts/1", None) in api.sent
    assert api.posts[0]["status"] == "trash" and api.posts[1]["status"] == "draft"
    assert any("1 of 1 moved to the Trash. Ctrl+Z puts them back." in s for s in bench.said)
    assert bench.provider.history.undo() == "Restored 1 item from the Trash."
    assert api.posts[0]["status"] == "draft"
