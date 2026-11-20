"""Tools > Plain-Language Batch in the GitHub Workbench (GitHub PRD 22.6, GH-R-086).

A real Workbench frame over a fake GitHub Items provider, background work
inline. The two dialogs (the sentence, the checklist) are the WordPress
Workbench's own, answered here; the batch itself is the several-items
Properties batch, recorded rather than sent, since its sending is tested in
``test_github_workbench_properties.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.workbench.properties import ListDelta  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."


def _issue(number: int, labels: tuple[str, ...] = ()) -> GitHubItem:
    return GitHubItem(
        number, f"Issue {number}", "open", f"https://github.com/{REPO}/issues/{number}", False,
        created_at=f"2026-0{number}-01", labels=labels,
    )  # fmt: skip


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def __init__(self) -> None:
        self.searched: list[str] = []
        self.found = [_issue(1, ("duplicate",)), _issue(2, ("duplicate",)), _issue(3)]

    def search_items(self, repo: str, query: str, *, limit: int = 50) -> list[GitHubItem]:
        self.searched.append(f"{repo} {query}")
        return [i for i in self.found if "label:duplicate" not in query or i.labels]

    def fetch_issues(self, *_a: Any, **_kw: Any) -> list[GitHubItem]:
        return []

    def fetch_pulls(self, *_a: Any, **_kw: Any) -> list[GitHubItem]:
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


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    monkeypatch.setattr(provider, "account_name", lambda: "me-login")
    monkeypatch.setattr(provider, "github_api", lambda: object())
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    ref = NodeRef("repository", "issues_and_pulls", REPO)
    frame._show_node(ref, remember=True)
    yield frame
    frame.frame.Destroy()


def _answer(monkeypatch, sentences: list[str], uncheck: tuple[int, ...] = ()) -> dict[str, Any]:
    seen: dict[str, Any] = {"asked": [], "rows": None}

    def ask_text(_parent, _show, *, value: str = "", **_kw: Any) -> str | None:
        seen["asked"].append(value)
        return sentences.pop(0) if sentences else None

    def ask_checks(_parent, _show, *, rows, checked, prompt: str, **_kw: Any) -> list[int]:
        seen["rows"], seen["prompt"] = list(rows), prompt
        return [i for i in checked if i not in uncheck]

    monkeypatch.setattr("quill.ui.wordpress_dialogs.ask_text", ask_text)
    monkeypatch.setattr("quill.ui.wordpress_workbench_dialogs.ask_checks", ask_checks)
    return seen


def _record_batch(bench, monkeypatch) -> list[tuple[Any, ...]]:
    sent: list[tuple[Any, ...]] = []

    class _Loaded:
        values: dict[str, object] = {"state": "open", "labels": ()}

    monkeypatch.setattr("quill.core.github.sheet_engine.load", lambda api, sheet, ident: _Loaded())
    monkeypatch.setattr("quill.core.github.sheet_engine.load_options", lambda *a: {})
    monkeypatch.setattr(
        bench.provider,
        "_apply_many",
        lambda kind, noun, items, changes, choices, view, close: sent.append((
            kind,
            noun,
            [i.ident["number"] for i in items],
            list(changes),
            view,
        )),
    )
    return sent


def test_the_command_is_on_tools_with_a_key_and_a_requirement() -> None:
    from quill.core.github.workbench_window_menu import WORKBENCH_KEYS
    from quill.core.github.write_requirements import requirement_for

    assert WORKBENCH_KEYS[f"{_P}plain_batch"] == "Ctrl+Shift+S"
    assert requirement_for(f"{_P}plain_batch") is not None


def test_a_sentence_finds_the_items_previews_them_and_sends_what_is_checked(
    bench, monkeypatch
) -> None:
    seen = _answer(monkeypatch, ["close every issue labelled duplicate older than 90 days"], (1,))
    sent = _record_batch(bench, monkeypatch)
    reloaded: list[bool] = []
    monkeypatch.setattr(bench, "reload", lambda **_kw: reloaded.append(True))
    bench.run(f"{_P}plain_batch")
    (search,) = bench.provider.items.searched
    assert search.startswith(f"{REPO} is:issue is:open label:duplicate created:<")
    assert seen["rows"] == ["#1 Issue 1 (labels: duplicate)", "#2 Issue 2 (labels: duplicate)"]
    assert "2 issues found" in seen["prompt"]
    ((kind, noun, numbers, changes, view),) = sent
    assert (kind, noun, numbers) == ("issue", "issues", ["1"])  # #2 was unchecked
    assert changes[0].key == "state" and changes[0].after == "closed as completed"
    view.saved({}, "1 done", close=True)  # the batch's end fills the list again
    assert reloaded == [True]


def test_a_sentence_it_does_not_read_is_said_and_asked_again(bench, monkeypatch) -> None:
    seen = _answer(
        monkeypatch, ["frobnicate issues", "assign me to every issue labelled duplicate"]
    )
    sent = _record_batch(bench, monkeypatch)
    bench.run(f"{_P}plain_batch")
    assert any("Start with close" in text for text in bench.said)
    assert seen["asked"] == ["", "frobnicate issues"]  # the words come back to correct
    ((_kind, _noun, _numbers, changes, _view),) = sent
    assert changes[0].after == ListDelta(("me-login",), ())  # "me" is the account


def test_a_question_changes_nothing(bench, monkeypatch) -> None:
    _answer(monkeypatch, ["how many issues are labelled duplicate?"])
    sent = _record_batch(bench, monkeypatch)
    bench.run(f"{_P}plain_batch")
    assert sent == []
    assert bench.said[-1] == "2 issues match: is:issue is:open label:duplicate."


def test_read_only_refuses_a_change_before_searching(bench, monkeypatch) -> None:
    from quill.core.github.permissions import AccessLevel

    _answer(monkeypatch, ["close every issue labelled duplicate"])
    sent = _record_batch(bench, monkeypatch)
    monkeypatch.setattr(bench.provider, "access_level", lambda: AccessLevel.READ_ONLY)
    bench.run(f"{_P}plain_batch")
    assert sent == [] and bench.provider.items.searched == []
    assert "Read Only" in bench.said[-1] or "read only" in bench.said[-1].lower()
