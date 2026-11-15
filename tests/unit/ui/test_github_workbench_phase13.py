"""GitHub Workbench Phase 13 in the window: Watches, Read as Document, the API Console.

A real frame over a fake GitHub Items provider and a recorded API door, with
background work run inline, in a data directory of the test's own. Dialogs are
answered by patching the provider's own ask helpers, so every command is
called the way a key or a menu row calls it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.explore_models import ExploreRow  # noqa: E402
from quill.core.github.item_actions import DELETE_COMMANDS, GITHUB_ACTIONS, NEW_HERE  # noqa: E402
from quill.core.github.items_provider import GitHubItem  # noqa: E402
from quill.core.github.permissions import AccessLevel  # noqa: E402
from quill.core.github.rest_transport import RestResponse  # noqa: E402
from quill.core.github.watches import WatchStore  # noqa: E402
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS  # noqa: E402
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."


class FakeApi:
    """Recorded answers by path; records every call. Never reaches GitHub."""

    def __init__(self, answers: dict[str, Any], graph: dict[str, Any] | None = None) -> None:
        self.answers = answers
        self.graph = graph or {}
        self.calls: list[tuple[str, str, dict[str, str] | None]] = []

    def rest(self, method: str, path: str, *, body=None, query=None) -> RestResponse:
        self.calls.append((method, path, dict(query) if query else None))
        data = self.answers.get(path, [])
        if isinstance(data, list) and query and query.get("page", "1") != "1":
            data = []
        return RestResponse(200, {}, data)

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        self.calls.append(("GRAPHQL", "", dict(variables)))
        return self.graph


def _pull_api() -> FakeApi:
    return FakeApi({
        "/repos/o/r/issues/3": {
            "title": "Speed up start",
            "state": "open",
            "html_url": "https://github.com/o/r/pull/3",
            "user": {"login": "ann"},
            "created_at": "2026-11-01T10:00:00Z",
            "body": "Makes it faster.",
            "pull_request": {"merged_at": None},
        },
        "/repos/o/r/issues/3/comments": [
            {"user": {"login": "bob"}, "created_at": "2026-11-02T09:00:00Z", "body": "Nice."}
        ],
        "/repos/o/r/pulls/3/reviews": [
            {
                "id": 77,
                "user": {"login": "cy"},
                "state": "COMMENTED",
                "submitted_at": "2026-11-01T12:00:00Z",
                "body": "One thing.",
            }
        ],
        "/repos/o/r/pulls/3/comments": [
            {
                "pull_request_review_id": 77,
                "user": {"login": "cy"},
                "path": "app.py",
                "line": 12,
                "created_at": "2026-11-01T12:00:00Z",
                "body": "Rename this.",
            },
            {"user": {"login": "dan"}, "path": "b.py", "created_at": "2026-11-04", "body": "?"},
        ],
    })


class _Items:
    is_authenticated = True
    token = "test-token-not-real"

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(3, "Speed up start", "open", "https://github.com/o/r/pull/3", True)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
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
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    said: list[str] = []
    opened: list[Path] = []
    provider = GitHubWorkbenchProvider(
        _Items(), REPO, announce=said.append, open_document=opened.append
    )
    provider.api = FakeApi({})
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.opened = opened  # type: ignore[attr-defined]
    yield frame
    provider.stop_watch_timer()
    frame.frame.Destroy()


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _answers(monkeypatch, *, choose: list[int], text: list[str]) -> None:
    mixin = "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin"
    monkeypatch.setattr(f"{mixin}._choose", lambda _s, _t, _p, _l: choose.pop(0))
    monkeypatch.setattr(f"{mixin}._ask_text", lambda _s, _t, _p, **_k: text.pop(0))


# -- Watches -----------------------------------------------------------------------


def test_watches_is_a_place_now_not_a_placeholder(bench) -> None:
    _go(bench, NodeRef("", "watches"))
    assert "later release" not in bench.details.GetValue()
    assert NEW_HERE["watches"] == f"{_P}add_watch"
    assert DELETE_COMMANDS["watch"] == f"{_P}remove_watch"
    assert WORKBENCH_KEYS[f"{_P}go_watches"] == "Ctrl+7"
    for verb in ("pause_watch", "remove_watch"):
        assert COMMAND_REQUIREMENTS[f"{_P}{verb}"][0] == "local"
    assert GITHUB_ACTIONS.rows_for("watch")[0].command_id == f"{_P}edit_watch"


def test_add_edit_pause_check_and_remove_a_watch(bench, monkeypatch) -> None:
    _go(bench, NodeRef("", "watches"))
    _answers(monkeypatch, choose=[2], text=["not a repo", "owner/repo"])  # releases; retry once
    bench.run(f"{_P}new_here")
    assert "Type the repository as owner/name." in bench.said
    assert bench.said[-1].startswith("Watching: New releases in owner/repo.")
    assert len(bench.rows) == 1 and "not checked yet" in bench.rows[0].label
    # Check Now: the first check learns, and the row says when it was checked.
    bench.provider.api.answers["/repos/owner/repo/releases"] = [{"id": 1, "name": "One"}]
    bench.list.Select(0)
    bench.run(f"{_P}check_watches")
    assert bench.said[-1] == "Checked 1 watches. Nothing new."
    assert "checked just now" in bench.rows[0].label
    bench.provider.api.answers["/repos/owner/repo/releases"] = [
        {"id": 2, "name": "Two"},
        {"id": 1, "name": "One"},
    ]
    bench.run(f"{_P}check_watches")
    assert bench.said[-1] == "New release in owner/repo: Two."
    assert not any("notifications" in p for _m, p, _q in bench.provider.api.calls)
    # Edit (Enter) moves it to another repository and starts afresh.
    _answers(monkeypatch, choose=[], text=["other/place"])
    bench.list.Select(0)
    bench.default_action()
    assert bench.said[-1] == "Watch changed: New releases in other/place."
    assert "not checked yet" in bench.rows[0].label
    # Pause, then the round skips it.
    bench.list.Select(0)
    bench.run(f"{_P}pause_watch")
    assert bench.said[-1] == "Paused: New releases in other/place."
    assert "Paused." in bench.rows[0].label
    bench.run(f"{_P}check_watches")
    assert bench.said[-1] == "There are no active watches. Ctrl+N in Watches adds one."
    # Remove (what Delete does on a watch row).
    bench.list.Select(0)
    bench.run(f"{_P}remove_watch")
    assert bench.said[-1] == "Watch removed: New releases in other/place."
    assert bench.rows == []
    assert WatchStore.load(_account_key()).watches == []


def _account_key() -> str:
    from quill.core.github.navigation_state import account_key_for_token

    return account_key_for_token("test-token-not-real")


def test_the_timer_round_waits_for_its_interval_and_for_consent(bench, monkeypatch) -> None:
    store = WatchStore.load(_account_key())
    store.add("release", "owner/repo")
    store.save()
    provider = bench.provider
    assert provider.run_watch_round() is True  # never run before: due
    assert provider.run_watch_round() is False  # just ran: not due yet
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: False)
    assert "network access" in provider.watch_round_blocked()
    assert provider.run_watch_round(forced=True) is False
    assert "network access" in bench.said[-1]
    provider.start_watch_timer()
    assert provider._watch_timer is not None and provider._watch_timer.IsRunning()
    provider.stop_watch_timer()
    assert provider._watch_timer is None


# -- Read as Document --------------------------------------------------------------


def test_read_as_document_opens_the_thread_in_the_editor(bench, monkeypatch) -> None:
    bench.provider.api = _pull_api()
    row = GitHubItem(3, "Speed up start", "open", "https://github.com/o/r/pull/3", True)
    ref = NodeRef("repository", "pulls", "o/r")
    _answers(monkeypatch, choose=[0], text=[])  # Open in Editor
    assert bench.provider.supports(f"{_P}read_as_document") is False  # nothing selected
    bench.provider._do_read_as_document(ref, row)
    assert bench.said[-1] == "Opened #3 in the editor, 5 posts."
    written = bench.opened[-1]
    assert written.name == "o-r-pr-3.md"
    text = written.read_text(encoding="utf-8")
    assert text.startswith("# Pull request o/r#3: Speed up start")
    assert "### Line comment by cy, 2026-11-01" in text


def test_read_as_document_saves_html_from_a_discussion_row(bench, monkeypatch, tmp_path) -> None:
    graph = {
        "repository": {
            "discussion": {
                "number": 9,
                "title": "How?",
                "body": "Question.",
                "author": {"login": "dee"},
                "comments": {"nodes": []},
            }
        }
    }
    bench.provider.api = FakeApi({}, graph)
    row = ExploreRow(
        "#9 How?", "", "https://github.com/o/r/discussions/9", "o/r", "discussion", "9"
    )
    _answers(monkeypatch, choose=[2], text=[])  # Save as HTML...
    target = tmp_path / "thread.html"
    monkeypatch.setattr(
        "quill.ui.github_workbench_reading.GitHubWorkbenchReadingMixin._save_path",
        lambda _s, name, html: target if html and name == "o-r-discussion-9.html" else None,
    )
    bench.provider._do_read_as_document(NodeRef("repository", "discussions", "o/r"), row)
    assert bench.said[-1] == "Saved thread.html, 1 posts."
    assert "<h1" in target.read_text(encoding="utf-8")


# -- API Console -------------------------------------------------------------------


def _console(bench, monkeypatch, level: AccessLevel = AccessLevel.FULL) -> Any:
    from quill.ui.github_api_console import GitHubApiConsole

    monkeypatch.setattr(GitHubWorkbenchProvider, "access_level", lambda _s: level)
    monkeypatch.setattr(GitHubWorkbenchProvider, "account_name", lambda _s: "alice")
    return GitHubApiConsole(bench.provider, REPO)


def test_the_console_reads_explains_and_shows_a_tree(bench, monkeypatch) -> None:
    console = _console(bench, monkeypatch)
    try:
        assert WORKBENCH_KEYS[f"{_P}api_console"] == "Ctrl+Shift+J"
        console.path.ChangeValue("/repos/owner/repo/issues/5?per_page=1")
        console.refresh()
        bench.provider.api.answers["/repos/owner/repo/issues/5"] = {
            "title": "Bug",
            "labels": [{"name": "crash"}],
        }
        console.send()
        assert ("GET", "/repos/owner/repo/issues/5", {"per_page": "1"}) in (
            bench.provider.api.calls
        )
        assert bench.said[-1] == "GET /repos/owner/repo/issues/5: answered."
        node = console.selected_node()
        assert node is not None and node.label == "Answer: object, 2 fields"
        copied: list[tuple[str, str]] = []
        monkeypatch.setattr(console, "_copy", lambda text, what: copied.append((what, text)))
        console.copy_path()
        console.copy_value()
        assert copied[0] == ("Path", "$")
        assert '"title": "Bug"' in copied[1][1]
    finally:
        console.dialog.Destroy()


def test_a_console_write_needs_full_access_and_the_method_typed(bench, monkeypatch) -> None:
    console = _console(bench, monkeypatch, AccessLevel.ORGANIZE)
    try:
        console.method.SetSelection(1)  # POST
        console.path.ChangeValue("/repos/owner/repo/issues")
        console.body.ChangeValue("title=From the console")
        console.refresh()
        assert "type POST" in console.explanation.GetValue()
        console.send()
        assert "need Full access" in bench.said[-1]
        assert bench.provider.api.calls == []
    finally:
        console.dialog.Destroy()
    console = _console(bench, monkeypatch, AccessLevel.FULL)
    typed: list[str] = ["post"]

    def answer(dialog: Any, _label: str, **_kw: Any) -> int:
        dialog.SetValue(typed.pop(0))
        return wx.ID_OK

    monkeypatch.setattr("quill.ui.github_api_console.show_modal_dialog", answer)
    try:
        console.method.SetSelection(1)
        console.path.ChangeValue("/repos/owner/repo/issues")
        console.body.ChangeValue("title=From the console")
        bench.provider.api.answers["/repos/owner/repo/issues"] = {"number": 12}
        console.send()
        assert bench.provider.api.calls[-1][:2] == ("POST", "/repos/owner/repo/issues")
        from quill.core.github.change_log import ChangeLog

        assert ChangeLog.load().entries[-1].target == "POST /repos/owner/repo/issues"
    finally:
        console.dialog.Destroy()


def test_saved_console_commands_fill_the_console(bench, monkeypatch) -> None:
    from quill.core.github.api_console import ConsoleCommand, SavedCommands

    console = _console(bench, monkeypatch)
    try:
        console.fill(ConsoleCommand("me", "GET", "/user"))
        monkeypatch.setattr(
            "quill.ui.github_api_console.show_modal_dialog",
            lambda dialog, _label, **_k: dialog.SetValue("who am i") or wx.ID_OK,
        )
        console.save_command()
        assert SavedCommands.load("alice").commands == [ConsoleCommand("who am i", "GET", "/user")]
        console.path.ChangeValue("/elsewhere")
        monkeypatch.setattr(
            "quill.ui.github_api_console.show_modal_dialog",
            lambda dialog, _label, **_k: dialog.SetSelection(0) or wx.ID_OK,
        )
        console.load_command()
        assert console.path.GetValue() == "/user"
    finally:
        console.dialog.Destroy()


def test_the_console_opens_from_its_menu_row(bench, monkeypatch) -> None:
    shown: list[str] = []
    monkeypatch.setattr(
        "quill.ui.github_api_console.GitHubApiConsole.show",
        lambda self: shown.append(self.path.GetValue()) or self.dialog.Destroy() or 0,
    )
    _go(bench, NodeRef("repository", "issues", REPO))
    bench.run(f"{_P}api_console")
    assert shown == [f"/repos/{REPO}"]
