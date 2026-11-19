"""Redirect Groups, Export Redirects and Import Redirects (complete.md 2.3, Redirects)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import workbench_redirect_files as files  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_sweep import (  # noqa: E402
    _posts_to,
    bench,
)
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go  # noqa: E402

__all__ = ["bench"]

_GROUPS = NodeRef("site", "redirect_groups", SITE)


def _quiet(monkeypatch: pytest.MonkeyPatch, *texts: str | None) -> list[dict]:
    queue, previews = list(texts), []
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: queue.pop(0))
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (previews.append(k), True)[1])
    return previews


# -- the wx-free half ----------------------------------------------------------------


def test_a_group_row_says_its_module_count_and_state() -> None:
    row = files.group_row(
        SITE, {"id": 6, "name": "Old shop", "module_id": 2, "redirects": 1, "enabled": False}
    )
    assert row.cells == {"name": "Old shop", "module": "Apache", "redirects": "1", "state": "off"}
    assert row.detail == "Old shop: 1 redirect, run by Apache, turned off."


def test_group_routes_and_bodies() -> None:
    assert files.group_body("  Old   shop ") == {"name": "Old shop", "moduleId": 1}
    assert files.group_route() == "redirection/v1/group"
    assert files.group_route(6) == "redirection/v1/group/6"
    assert files.group_route(action="disable") == "redirection/v1/bulk/group/disable"
    with pytest.raises(ValueError, match="needs a name"):
        files.group_body("  ")


def test_csv_round_trips_through_export_and_import() -> None:
    redirects = [{"url": "/a/", "action_data": {"url": "/b/"}, "action_code": 302, "regex": False}]
    text = files.export_csv(redirects)
    assert text.splitlines()[0].startswith("source,target,regex,code")
    plan = files.parse_import(text, "r.csv")
    assert plan.adds == [("/a/", "/b/", 302, False)]


def test_import_names_every_line_it_cannot_use_and_skips_what_is_there() -> None:
    text = "/one/,/two/\n/three/,,0,301\n/four/,/five/,0,200\n/one/,/six/\n/old/,/new/\n"
    plan = files.parse_import(text, "r.csv", existing=["/old/"])
    assert plan.adds == [("/one/", "/two/", 301, False)]
    assert plan.problems == [
        "Line 2: /three/ has no address to lead to.",
        "Line 3: 200 is not a redirect code (301, 302, 307 or 308).",
        "Line 4: /one/ is in the file twice; the first is used.",
        "/old/: the site already redirects it.",
    ]


def test_a_redirection_json_export_is_read() -> None:
    text = json.dumps({
        "redirects": [
            {"url": "^/x/(.*)", "action_data": {"url": "/y/$1"}, "action_code": 301, "regex": True}
        ]
    })
    assert files.parse_import(text, "export.json").adds == [("^/x/(.*)", "/y/$1", 301, True)]
    assert files.parse_import("{oops", "bad.json").problems == [
        "bad.json is not JSON QUILL can read."
    ]


# -- in the Workbench ----------------------------------------------------------------


def test_groups_list_under_redirects_and_ctrl_n_makes_one(bench, monkeypatch) -> None:
    _go(bench, _GROUPS)
    assert [r.cell("name") for r in bench.rows] == ["Redirections", "Moved posts"]
    _quiet(monkeypatch, "Campaigns")
    bench.run(command("new_here"))
    assert _posts_to(bench.api, "redirection/v1/group") == [{"name": "Campaigns", "moduleId": 1}]


def test_rename_and_turn_off_a_group_each_undo(bench, monkeypatch) -> None:
    _go(bench, _GROUPS)
    moved = bench.rows[1]
    _quiet(monkeypatch, "Moved")
    bench.provider.do_rename_redirect_group(None, moved)
    assert _posts_to(bench.api, "redirection/v1/group/6") == [{"name": "Moved", "moduleId": 1}]
    bench.provider.history.entries[-1].undo()
    assert _posts_to(bench.api, "redirection/v1/group/6")[-1] == {
        "name": "Moved posts",
        "moduleId": 1,
    }
    bench.provider.do_toggle_redirect_group(None, moved)
    assert _posts_to(bench.api, "redirection/v1/bulk/group/disable") == [{"items": [6]}]
    assert (
        bench.provider.history.entries[-1].undo() == "The redirect group Moved posts is on again."
    )


def test_deleting_a_group_needs_its_name_typed(bench, monkeypatch) -> None:
    _go(bench, _GROUPS)
    _quiet(monkeypatch, "moved")
    bench.provider.do_delete_redirect_group(None, bench.rows[1])
    assert _posts_to(bench.api, "redirection/v1/bulk/group/delete") == []
    assert bench.said[-1] == "The name did not match. Nothing was deleted."
    _quiet(monkeypatch, "Moved posts")
    bench.provider.do_delete_redirect_group(None, bench.rows[1])
    assert _posts_to(bench.api, "redirection/v1/bulk/group/delete") == [{"items": [6]}]


def test_export_saves_the_redirects_to_a_file(bench, monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "redirects.json"
    monkeypatch.setattr(bench.provider, "_file", lambda *a, **k: target)
    _go(bench, NodeRef("site", "redirects", SITE))
    bench.provider.do_export_redirects(NodeRef("site", "redirects", SITE), None)
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert [r["url"] for r in saved["redirects"]] == ["/old/"]
    assert [g["name"] for g in saved["groups"]] == ["Redirections", "Moved posts"]
    assert bench.said[-1] == f"Saved 1 redirects from {SITE} to redirects.json."


def test_import_previews_then_adds_each_into_the_chosen_group(
    bench, monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "moves.csv"
    source.write_text("source,target\n/a/,/b/\n/old/,/elsewhere/\n", encoding="utf-8")
    monkeypatch.setattr(bench.provider, "_file", lambda *a, **k: source)
    previews = _quiet(monkeypatch)
    _go(bench, NodeRef("site", "redirects", SITE))
    bench.provider.do_import_redirects(NodeRef("site", "redirects", SITE), None)
    assert previews[-1]["summary"] == f"Add 1 redirect from moves.csv to {SITE}."
    assert previews[-1]["lines"][-1] == "/old/: the site already redirects it."
    (body,) = _posts_to(bench.api, "redirection/v1/redirect")
    assert body["url"] == "/a/" and body["group_id"] == 2
    assert bench.said[-1] == f"Added 1 of 1 redirects to {SITE}."
