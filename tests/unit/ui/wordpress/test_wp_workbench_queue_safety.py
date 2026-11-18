"""Send Back and Approve and Schedule never take a published post off a site
unannounced (how.md review, safety 8)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import ChangeHistory
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_bold_queue as queue
from quill.ui import wordpress_workbench_dialogs as wdlg


class _Api:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def post(self, route: str, body: dict[str, Any]) -> dict[str, Any]:
        self.posts.append((route, body))
        return {}


def _row(number: int, status: str) -> WbRow:
    return WbRow(
        kind="item",
        site="Blog",
        key=str(number),
        cells={"title": f"Post {number}"},
        detail="",
        route=f"wp/v2/posts/{number}",
        status=status,
        raw={"id": number, "title": {"rendered": f"Post {number}"}},
    )


class _Host(queue.WorkbenchQueueCommands):
    def __init__(self, rows: list[WbRow]) -> None:
        self.api = _Api()
        self.rows = rows
        self.parent = None
        self.history = ChangeHistory()
        self.said: list[str] = []
        self.say = self.said.append  # type: ignore[assignment]
        self.background = lambda _label, work, done: done(work())  # type: ignore[assignment]
        self.ctx = lambda _site: SimpleNamespace(api=self.api)  # type: ignore[assignment]
        self.show_modal = lambda *_a: 0  # type: ignore[assignment]
        self.refresh = lambda: None  # type: ignore[assignment]
        self.selected_rows = lambda: self.rows  # type: ignore[assignment]


@pytest.fixture
def previews(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    def ask_preview(*_a: Any, **kwargs: Any) -> bool:
        seen.append(kwargs)
        return bool(seen[-1].get("answer", True))

    monkeypatch.setattr(wdlg, "ask_preview", ask_preview)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "Tighten the opening.")
    monkeypatch.setattr(queue.notes, "add_note", lambda *_a, **_k: None)
    return seen


def test_send_back_previews_and_warns_about_a_published_post(previews) -> None:
    host = _Host([_row(1, "publish"), _row(2, "pending")])
    host.do_send_back(None, None)
    assert previews and previews[0]["yes"] == "Send Back"
    assert any("1 published item comes off the site" in line for line in previews[0]["lines"])
    assert host.api.posts == [
        ("wp/v2/posts/1", {"status": "draft"}),
        ("wp/v2/posts/2", {"status": "draft"}),
    ]


def test_undo_puts_each_post_back_as_it_was(previews) -> None:
    host = _Host([_row(1, "publish"), _row(2, "pending")])
    host.do_send_back(None, None)
    host.api.posts.clear()
    said = host.history.undo()
    assert host.api.posts == [
        ("wp/v2/posts/1", {"status": "publish"}),
        ("wp/v2/posts/2", {"status": "pending"}),
    ]
    assert said.startswith("Put 2 back as they were on Blog.")


def test_cancelling_the_preview_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: False)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "Note")
    host = _Host([_row(1, "publish")])
    host.do_send_back(None, None)
    assert host.api.posts == []
    assert host.history.entries == ()


def _plugin(key: str, status: str = "active") -> WbRow:
    return WbRow(
        kind="plugin",
        site="Blog",
        key=key,
        cells={"plugin": key.split("/")[0]},
        detail="",
        route=f"wp/v2/plugins/{key}",
        status=status,
    )


def test_properties_cannot_switch_off_the_plugin_quill_signs_in_through(previews) -> None:
    """how.md review, safety 5: the same refusal Deactivate gives."""
    from quill.ui.wordpress_workbench_sheet_guards import plugin_status_cleared

    said: list[str] = []
    provider = SimpleNamespace(say=said.append, parent=None, show_modal=None)
    row = _plugin("application-passwords/application-passwords")
    assert not plugin_status_cleared(provider, row, {"status": "inactive"})
    assert said and "lock the Workbench out" in said[0]
    assert previews == []


def test_properties_asks_before_switching_off_any_other_plugin(monkeypatch) -> None:
    from quill.ui.wordpress_workbench_sheet_guards import plugin_status_cleared

    asked: list[dict[str, Any]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: asked.append(k) or False)
    provider = SimpleNamespace(say=lambda _s: None, parent=None, show_modal=None)
    row = _plugin("akismet/akismet")
    assert not plugin_status_cleared(provider, row, {"status": "inactive"})
    assert asked[0]["yes"] == "Deactivate"
    assert plugin_status_cleared(provider, row, {"status": "active"})
    assert plugin_status_cleared(
        provider, _plugin("akismet/akismet", "inactive"), {"status": "inactive"}
    )
