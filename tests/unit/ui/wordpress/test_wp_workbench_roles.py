"""Roles through a role plugin, and Who Has Never Signed In, in the real frame (15.11)."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.role_plugin import NO_SIGN_IN_TIMES  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS  # noqa: E402
from quill.core.wordpress.workbench_admin_actions import KEYLESS  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE  # noqa: E402

bench = _bench

ROLES = [
    {"slug": "editor", "name": "Editor", "capabilities": {"read": True, "edit_posts": True}},
    {"slug": "volunteer", "name": "Volunteer", "capabilities": {"read": True}},
]


def _person() -> WbRow:
    return WbRow("user", SITE, "3", {"name": "Jeff"}, "")


def _with(bench, monkeypatch, *, namespaces: list[str], users: list[dict] | None = None) -> None:
    get, walk = bench.api.get, bench.api.iter_collection

    def fake_get(route: str, **params: Any) -> Any:
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", *namespaces], "routes": {}}
        if route == "members/v1/roles":
            return ROLES
        return get(route, **params)

    def fake_walk(route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/users" and users is not None:
            yield from users
            return
        yield from walk(route, params, **kw)

    monkeypatch.setattr(bench.api, "get", fake_get)
    monkeypatch.setattr(bench.api, "iter_collection", fake_walk)


def _dialogs(monkeypatch, *, choice: int | None, texts: list[str | None], yes: bool = True):
    seen: dict[str, list[Any]] = {"preview": [], "report": [], "choice": []}
    answers = list(texts)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: (seen["choice"].append(k), choice)[1])
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: answers.pop(0) if answers else None)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (seen["preview"].append(k), yes)[1])
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: seen["report"].append(k))
    return seen


def test_the_command_has_help_a_reason_for_no_chord_and_a_handler(bench) -> None:
    offered = {a.command_id: a for a in WORDPRESS_ACTIONS.rows_for("user")}
    command = "wordpress.workbench.never_signed_in"
    assert offered[command].help and KEYLESS[command]
    assert callable(bench.provider.do_never_signed_in)


def test_without_a_role_plugin_roles_stay_the_read_only_report(bench, monkeypatch) -> None:
    _with(bench, monkeypatch, namespaces=[])
    seen = _dialogs(monkeypatch, choice=None, texts=[])
    bench.provider.do_roles(None, _person())
    assert seen["choice"] == []
    assert "cannot change what a role may do" in seen["report"][0]["text"]


def test_a_roles_capabilities_are_changed_after_a_preview_and_put_back(bench, monkeypatch) -> None:
    _with(bench, monkeypatch, namespaces=["members/v1"])
    seen = _dialogs(monkeypatch, choice=0, texts=["read\nupload_files"])
    bench.provider.do_roles(None, _person())
    assert seen["choice"][0]["rows"] == [
        "Editor (editor): 2 capabilities",
        "Volunteer (volunteer): 1 capability",
        "New Role...",
    ]
    assert seen["preview"][0]["lines"] == [
        "Editor may now also: upload_files",
        "Editor may no longer: edit_posts",
    ]
    assert bench.api.writes[-1] == (
        "POST",
        "members/v1/roles/editor",
        {"capabilities": {"read": True, "upload_files": True}},
    )
    assert "Editor on" in bench.said[-1]
    bench.provider.history.undo()
    assert bench.api.writes[-1] == (
        "POST",
        "members/v1/roles/editor",
        {"capabilities": {"edit_posts": True, "read": True}},
    )


def test_a_cancelled_preview_changes_no_role(bench, monkeypatch) -> None:
    _with(bench, monkeypatch, namespaces=["members/v1"])
    _dialogs(monkeypatch, choice=0, texts=["read"], yes=False)
    bench.provider.do_roles(None, _person())
    assert bench.api.writes == []


def test_a_new_role_is_made_and_undo_takes_it_away(bench, monkeypatch) -> None:
    _with(bench, monkeypatch, namespaces=["members/v1"])
    _dialogs(monkeypatch, choice=2, texts=["Board Member", "read\nedit_posts"])
    bench.provider.do_roles(None, _person())
    assert bench.api.writes[-1] == (
        "POST",
        "members/v1/roles",
        {
            "slug": "board_member",
            "name": "Board Member",
            "capabilities": {"edit_posts": True, "read": True},
        },
    )
    bench.provider.history.undo()
    assert bench.api.writes[-1][:2] == ("DELETE", "members/v1/roles/board_member")


def test_a_taken_slug_is_refused_before_anything_is_sent(bench, monkeypatch) -> None:
    _with(bench, monkeypatch, namespaces=["members/v1"])
    _dialogs(monkeypatch, choice=2, texts=["Volunteer"])
    bench.provider.do_roles(None, _person())
    assert bench.api.writes == []
    assert bench.said[-1] == "The site already has a role volunteer."


def test_never_signed_in_lists_people_only_where_the_site_gives_times(bench, monkeypatch) -> None:
    users = [
        {"id": 3, "name": "Jeff", "meta": {"last_login": "2026-11-01"}},
        {"id": 4, "name": "Ann", "meta": {"last_login": ""}},
    ]
    _with(bench, monkeypatch, namespaces=[], users=users)
    seen = _dialogs(monkeypatch, choice=None, texts=[])
    bench.provider.do_never_signed_in(None, _person())
    assert bench.said[-1] == (
        f"1 person has never signed in to {SITE}, as its meta.last_login field records it."
    )
    assert seen["report"][0]["text"].endswith("\n\nAnn")


def test_never_signed_in_says_when_the_site_gives_no_times(bench, monkeypatch) -> None:
    _with(bench, monkeypatch, namespaces=[], users=[{"id": 3, "name": "Jeff"}])
    _dialogs(monkeypatch, choice=None, texts=[])
    bench.provider.do_never_signed_in(None, _person())
    assert bench.said[-1] == NO_SIGN_IN_TIMES
