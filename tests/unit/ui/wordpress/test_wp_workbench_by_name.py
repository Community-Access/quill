"""By Name and Across Sites operations in the real frame, on a fake site (15.12)."""

from __future__ import annotations

import time
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.workbench_across import SiteScan  # noqa: E402
from quill.core.wordpress.workbench_actions import WINDOW_MENU, WORDPRESS_ACTIONS  # noqa: E402
from quill.core.wordpress.workbench_places import KEYLESS  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_scope_matrix import matrix  # noqa: E402
from quill.core.workbench.menus import rows as menu_rows  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go  # noqa: E402

bench = _bench

_VERBS = (
    "where_used",
    "rename_value",
    "split_value",
    "merge_value",
    "reassign_value",
    "replace_value",
    "find_missing",
    "make_same",
    "promote_network",
    "compare_styles",
    "revoke_everywhere",
    "convert_shortcode",
    "update_pattern",
    "detach_pattern",
    "plugin_block_uses",
    "merge_everywhere",
    "remove_everywhere",
)


def _scan(bench) -> SiteScan:
    scan = SiteScan(SITE)
    scan.items = [dict(p) for p in bench.api.posts]
    scan.items[0].update(
        meta={"venue": "Main Hall"},
        content={"raw": '<a href="https://old.example">x</a>'},
        categories=[5],
    )
    scan.items[1].update(meta={}, content={"raw": ""}, categories=[5])
    scan.terms = [
        ("category", {"id": 5, "name": "Shows", "slug": "shows", "count": 2}),
        ("category", {"id": 6, "name": "News", "slug": "news", "count": 0}),
    ]
    scan.users = {3: "Jeff", 4: "Ann"}
    bench.provider.__dict__.setdefault("_scans", {})[SITE] = (time.time(), scan)
    return scan


def _value(kind: str, key: str) -> WbRow:
    return WbRow("value", SITE, key, {"value": key}, "", subkind=kind)


def _previews(monkeypatch, answer: bool = True) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (seen.append(k), answer)[1])
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: seen.append(k))
    return seen


def test_every_new_command_has_help_a_written_reason_for_no_chord_and_a_handler(bench) -> None:
    bound = {row.command_id for _menu, row in menu_rows(WINDOW_MENU)}
    offered = {
        a.command_id: a for k in WORDPRESS_ACTIONS.row_types for a in WORDPRESS_ACTIONS.rows_for(k)
    }
    for verb in _VERBS:
        command = f"wordpress.workbench.{verb}"
        assert offered[command].help, verb
        assert command in bound or KEYLESS.get(command), verb
        assert callable(getattr(bench.provider, f"do_{verb}", None)), verb
    for key, cell in matrix().items():
        if cell.supported:
            assert callable(getattr(bench.provider, f"do_{cell.handler}", None)), key


def test_rename_a_field_value_everywhere_previews_sends_and_undoes(bench, monkeypatch) -> None:
    _scan(bench)
    seen = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Studio")
    bench.provider.do_rename_value(None, _value("fields", "venue: Main Hall"))
    assert seen[0]["lines"] == [f"{SITE}: Hello: venue changes from Main Hall to Studio"]
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"meta": {"venue": "Studio"}})
    assert bench.provider.history.undo() == "Put 1 back as they were."
    assert bench.api.writes[-1] == ("POST", "wp/v2/posts/1", {"meta": {"venue": "Main Hall"}})


def test_a_cancelled_preview_sends_nothing(bench, monkeypatch) -> None:
    _scan(bench)
    _previews(monkeypatch, answer=False)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Studio")
    bench.provider.do_rename_value(None, _value("fields", "venue: Main Hall"))
    assert bench.api.writes == []


def test_split_a_term_makes_the_new_term_and_moves_only_the_checked_items(
    bench, monkeypatch
) -> None:
    _scan(bench)
    _previews(monkeypatch)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [1])
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Archive")
    post = bench.api.post
    monkeypatch.setattr(
        bench.api,
        "post",
        lambda route, body=None, **kw: {"id": 77, **post(route, body, **kw)},
    )
    bench.provider.do_split_value(None, _value("terms", "category:5"))
    made = bench.api.writes[0]
    assert made == ("POST", "wp/v2/categories", {"name": "Archive"})
    assert bench.api.writes[1] == ("POST", "wp/v2/posts/2", {"categories": [77]})
    bench.provider.history.undo()
    assert bench.api.writes[-1] == ("DELETE", "wp/v2/categories/77", {"force": True})
    assert "Archive" in bench.said[-1] or "Split" in bench.said[-1]


def test_merge_a_term_moves_every_item_then_deletes_it_and_is_final(bench, monkeypatch) -> None:
    _scan(bench)
    seen = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    bench.provider.do_merge_value(None, _value("terms", "category:5"))
    assert "cannot be undone" in seen[0]["summary"]
    assert [w[1] for w in bench.api.writes] == [
        "wp/v2/posts/1",
        "wp/v2/posts/2",
        "wp/v2/categories/5",
    ]
    assert bench.api.writes[-1][0] == "DELETE"
    assert not bench.provider.history.can_undo()


def test_reassign_an_authors_items_to_another_person(bench, monkeypatch) -> None:
    _scan(bench)
    _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    bench.provider.do_reassign_value(None, _value("authors", "3"))
    assert ("POST", "wp/v2/posts/1", {"author": 4}) in bench.api.writes
    assert bench.provider.history.can_undo()


def test_replace_a_link_everywhere_and_refuse_what_the_kind_does_not_allow(
    bench, monkeypatch
) -> None:
    _scan(bench)
    _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "https://new.example")
    bench.provider.do_replace_value(None, _value("links", "https://old.example"))
    assert bench.api.writes[-1][2]["content"] == '<a href="https://new.example">x</a>'
    bench.provider.do_rename_value(None, _value("links", "https://old.example"))
    assert bench.said[-1] == "Replace changes the address on every page."


def test_find_items_missing_a_field(bench, monkeypatch) -> None:
    _scan(bench)
    seen = _previews(monkeypatch)
    bench.provider.do_find_missing(None, _value("fields", "venue: Main Hall"))
    assert seen[0]["text"] == "News"


def test_read_only_access_refuses_by_name_changes_with_the_reason(bench, monkeypatch) -> None:
    _scan(bench)
    monkeypatch.setattr(bench.provider, "write_refusal", lambda *_a: "Read Only access.")
    bench.provider.do_rename_value(None, _value("fields", "venue: Main Hall"))
    assert bench.said[-1] == "Read Only access." and bench.api.writes == []


def _across(kind: str, key: str, variants: dict[str, list[str]], objects: dict[str, Any]):
    return WbRow(
        "across",
        "",
        key,
        {},
        "",
        subkind=kind,
        raw={"variants": variants, "missing": [], "objects": objects},
    )


def test_make_people_the_same_changes_their_role_and_can_be_undone(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 1)
    row = _across(
        "users",
        "ann@x",
        {"author": [SITE], "editor": ["Other"]},
        {SITE: {"id": 4, "roles": ["author"]}, "Other": {"id": 9, "roles": ["editor"]}},
    )
    get = bench.api.get
    roles = {"wp/v2/users/4": {"roles": ["author"]}}
    monkeypatch.setattr(bench.api, "get", lambda route, **kw: roles.get(route) or get(route, **kw))
    bench.provider.do_make_same(None, row)
    assert seen[0]["lines"] == [f"{SITE}: ann@x: role author becomes editor"]
    assert bench.api.writes[-1] == ("POST", "wp/v2/users/4", {"roles": ["editor"]})
    bench.provider.history.undo()
    assert bench.api.writes[-1] == ("POST", "wp/v2/users/4", {"roles": ["author"]})


def test_make_themes_the_same_opens_wp_admin_and_says_why(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    opened: list[tuple[str, str, dict[str, str]]] = []
    monkeypatch.setattr(
        bench.provider, "_open_screen", lambda site, key, **q: opened.append((site, key, q))
    )
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 1)
    row = _across(
        "themes",
        "Twenty Twenty-Five",
        {"version 1, inactive": [SITE], "version 1, active": ["Other"]},
        {SITE: {"stylesheet": "tt5"}, "Other": {"stylesheet": "tt5", "status": "active"}},
    )
    bench.provider.do_make_same(None, row)
    assert "cannot activate a theme" in seen[0]["summary"]
    assert opened == [(SITE, "theme_activate", {"theme": "tt5"})]
    assert bench.api.writes == []


def test_make_menus_the_same_copies_items_and_says_it_is_final(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    winner = {
        "id": 1,
        "home": "https://other.example",
        "items": [
            {
                "id": 1,
                "title": "About",
                "url": "https://other.example/about",
                "order": 1,
                "parent": 0,
            }
        ],
        "value": "1 item: About",
    }
    row = _across(
        "menus",
        "Footer",
        {"1 item: About": ["Other"], "no items": [SITE]},
        {
            "Other": winner,
            SITE: {"id": 5, "items": [], "value": "no items"},
        },
    )
    bench.provider.do_make_same(None, row)
    assert "cannot be undone" in seen[0]["summary"]
    posted = [w for w in bench.api.writes if w[1] == "wp/v2/menu-items"]
    assert posted[0][2]["url"] == "https://radio.example/about"
    assert not bench.provider.history.can_undo()


def test_compare_global_styles_reports_each_site(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    import quill.ui.wordpress_workbench_across as across

    monkeypatch.setattr(across, "site_styles", lambda _api: {"Colour Base": "#fff"})
    bench.provider.do_compare_styles(None, _across("themes", "TT5", {}, {}))
    assert seen[0]["title"] == "Compare Global Styles"
    assert "0 of 1 styles differ across 1 sites" in seen[0]["text"]


def test_promote_to_network_says_a_single_site_is_not_a_network(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    row = _across("plugins", "Akismet", {"version 5, active": [SITE]}, {SITE: {"plugin": "a/a"}})
    bench.provider.do_promote_network(None, row)
    assert "not a multisite network" in bench.said[-1] and seen == [] and bench.api.writes == []


def test_the_fleet_rows_carry_each_aspects_state(bench) -> None:
    _go(bench, NodeRef("", "fleet"))
    row = bench.rows[0]
    assert row.site == SITE
    assert row.cell("backups") == "unavailable: WordPress has no backups API"
    assert row.cell("updates").startswith("unavailable:")


def test_rename_a_template_part_by_title(bench, monkeypatch) -> None:
    scan = _scan(bench)
    scan.template_parts = [{"id": "tt5//header", "slug": "header", "title": "Header"}]
    seen = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Site Header")
    get = bench.api.get
    monkeypatch.setattr(
        bench.api,
        "get",
        lambda route, **kw: {"title": "Header"} if "template-parts" in route else get(route, **kw),
    )
    row = WbRow("value", SITE, "tt5//header", {"value": "Header"}, "", subkind="template_parts")
    bench.provider.do_rename_value(None, row)
    assert "its slug header stays" in seen[0]["lines"][0]
    assert bench.api.writes[-1] == (
        "POST",
        "wp/v2/template-parts/tt5//header",
        {"title": "Site Header"},
    )
    assert bench.provider.history.can_undo()


def test_revoke_a_password_everywhere_previews_and_says_there_is_no_undo(
    bench, monkeypatch
) -> None:
    seen = _previews(monkeypatch)
    row = _across(
        "app_passwords",
        "Phone, you",
        {"last used never": [SITE]},
        {SITE: {"route": "wp/v2/users/me/application-passwords/u1", "user": "me"}},
    )
    bench.provider.do_revoke_everywhere(None, row)
    assert "cannot be undone" in seen[0]["summary"]
    assert bench.api.writes[-1] == ("DELETE", "wp/v2/users/me/application-passwords/u1", {})
    assert "revoked on 1 of 1 sites" in bench.said[-1]
    assert not bench.provider.history.can_undo()
    bench.provider.do_revoke_everywhere(None, _across("plugins", "x", {}, {}))
    assert bench.said[-1].startswith("Revoke Everywhere works on")


def test_a_list_the_site_refused_is_named_in_the_by_name_preview_and_result(
    bench, monkeypatch
) -> None:
    scan = _scan(bench)
    scan.unread = ["wp/v2/pages: The site had a critical error."]
    seen = _previews(monkeypatch)
    said: list[str] = []
    monkeypatch.setattr(bench.provider, "say", said.append)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Studio")
    bench.provider.do_rename_value(None, _value("fields", "venue: Main Hall"))
    assert (
        seen[0]["lines"][-1] == f"Not read on {SITE}: wp/v2/pages: The site had a critical error."
    )
    assert f"On {SITE}, QUILL could not read wp/v2/pages" in seen[0]["summary"]
    assert any("could not read wp/v2/pages" in s for s in said)


def test_missing_from_names_a_site_whose_list_was_not_read(bench) -> None:
    from quill.core.wordpress.workbench_across import across_rows

    found = {"Events (tag)": {"A": {"id": 4, "slug": "events"}}}
    unread = {"B": ["wp/v2/tags: Sorry, you are not allowed to do that."]}
    rows = across_rows("terms", found, ["A", "B", "C"], unread)
    row = next(r for r in rows if r.key == "Events (tag)")
    _sheet, values = bench.provider.across_sheet(row)
    assert values["missing"].splitlines() == [
        "C",
        "Not read on B: wp/v2/tags: Sorry, you are not allowed to do that.",
    ]
