"""Self-lockout guards, stale-claim detection, ACF and QUILL Site Types (complete.md WP-A, WP-B).

Pure core: every request goes to a small fake site, nothing reaches a network.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import field_plugins as fp
from quill.core.wordpress import site_types_plugin as qst
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import Account, SiteInfo
from quill.core.wordpress.workbench_across_ops import revoke_plan
from quill.core.wordpress.workbench_edit import EditRefused, body_for, undo_body, verify
from quill.core.wordpress.workbench_permissions import (
    deactivate_refusal,
    deactivate_warning,
    remove_problem,
    revoke_refusal,
    role_change_preview,
    role_change_problem,
    setting_preview,
    setting_refusal,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import sheet_for
from quill.core.wordpress.workbench_site_stamp import read_stamp, stamp_changes, stamp_of
from quill.core.workbench.properties import FieldChange

EDITOR = Account(5, "Ann", "ann", ("editor",), frozenset({"edit_posts", "promote_users"}))
ADMIN = Account(1, "Jeff", "jeff", ("administrator",), frozenset({"manage_options"}))
USERS = [{"id": 1, "roles": ["administrator"]}, {"id": 2, "roles": ["administrator"]}]


# -- self-lockout -------------------------------------------------------------------------


def test_you_cannot_change_your_own_role_whatever_it_is() -> None:
    assert "your own Administrator role" in role_change_problem(ADMIN, 1, "editor", USERS)
    said = role_change_problem(EDITOR, 5, "author", USERS)
    assert "your own role" in said and "change it back" in said
    assert role_change_problem(EDITOR, 9, "author", USERS) == ""


def test_you_cannot_remove_yourself_or_the_last_administrator() -> None:
    assert "your own account" in remove_problem(EDITOR, 5, USERS)
    assert "only Administrator" in remove_problem(
        EDITOR, 1, [{"id": 1, "roles": ["administrator"]}]
    )


def test_the_connection_plugin_is_refused_and_forms_only_warned() -> None:
    said = deactivate_refusal("application-passwords/application-passwords.php", "Radio")
    assert "signs in to Radio through this plugin" in said and "wp-admin" in said
    assert deactivate_refusal("quill-accessible-forms/qaf.php", "Radio") == ""
    assert "Forms commands" in deactivate_warning("quill-accessible-forms/qaf.php")
    assert deactivate_refusal("akismet/akismet.php", "Radio") == ""


def test_the_password_quill_signs_in_with_is_never_revoked_from_here() -> None:
    said = revoke_refusal(True, "Radio")
    assert "signs in to Radio with this application password" in said
    assert "Make a new password and reconnect" in said
    assert revoke_refusal(False, "Radio") == ""


def test_revoke_everywhere_leaves_the_signed_in_password_alone() -> None:
    objects = {
        "Radio": {"route": "wp/v2/users/me/application-passwords/a", "current": True},
        "Choir": {"route": "wp/v2/users/me/application-passwords/b", "current": False},
    }
    plan, refused = revoke_plan("Laptop, you", objects, {})
    assert plan == [("Choir", "wp/v2/users/me/application-passwords/b")]
    assert [o.site for o in refused] == ["Radio"] and "lock the Workbench out" in refused[0].line


def test_settings_that_lock_people_out_are_refused_and_others_previewed() -> None:
    assert "not changed from the Workbench" in setting_refusal("url", "https://x.example")
    assert "Administrators by default" in setting_refusal("default_role", "administrator")
    assert setting_refusal("default_role", "subscriber") == ""
    assert setting_refusal("title", "New name") == ""
    summary, lines = setting_preview("Site title", "title", "Old", "", "Radio")
    assert "Ctrl+Z puts it back" in summary
    assert lines == ["Site title (title): Old becomes (empty)"]


def test_a_role_change_preview_names_what_is_gained_and_lost() -> None:
    summary, lines = role_change_preview("Ann", "author", "editor", "Radio")
    assert summary.startswith("Change Ann's role on Radio")
    assert lines[0] == "Ann: Author becomes Editor"
    assert any(line.startswith("Can now:") and "Moderating comments" in line for line in lines)
    _summary, down = role_change_preview("Ann", "editor", "author", "Radio")
    assert any(line.startswith("Can no longer:") and "Publishing pages" in line for line in down)


# -- Advanced Custom Fields: read and write ---------------------------------------------

ACF_PROPS = {
    "title": {"type": "object"},
    "meta": {"type": "object", "properties": {"rating": {"type": "integer"}}},
    "acf": {
        "type": "object",
        "properties": {
            "venue": {"type": "string", "description": "Where it happens"},
            "seats": {"type": ["integer", "null"]},
        },
    },
}


def test_acf_fields_get_their_own_page_values_and_checks() -> None:
    row = WbRow("item", "Radio", "7", {}, "", subkind="post", route="wp/v2/posts/7")
    acf = fp.acf_schema(ACF_PROPS)
    assert fp.meta_from_properties(ACF_PROPS) == {"rating": {"type": "integer"}}
    sheet = fp.with_acf_page(sheet_for(row, meta=fp.meta_from_properties(ACF_PROPS)), acf)
    page = sheet.pages[-1]
    assert page.title == "Advanced Custom Fields"
    assert [f.key for f in page.fields] == ["acf.seats", "acf.venue"]
    assert fp.acf_values({"acf": {"venue": "The Hall", "seats": 40}}) == {
        "acf.venue": "The Hall",
        "acf.seats": 40,
    }
    assert fp.acf_values({"acf": []}) == {}  # ACF's answer for an item with nothing saved
    assert fp.with_acf_page(sheet, None) is sheet


def test_acf_changes_go_back_as_acf_coerced_verified_and_undoable() -> None:
    row = WbRow("item", "Radio", "7", {}, "", subkind="post", route="wp/v2/posts/7")
    acf = fp.acf_schema(ACF_PROPS)
    sheet = fp.with_acf_page(sheet_for(row), acf)
    lookup = {"rating": {"type": "integer"}, **fp.acf_lookup(acf)}
    body = body_for(
        sheet,
        row,
        [
            FieldChange("acf.seats", "Seats", 40, "60"),
            FieldChange("acf.venue", "Venue", "Hall", "Barn"),
        ],
        meta_schema=lookup,
    )
    assert body == {"acf": {"seats": 60, "venue": "Barn"}}
    assert verify(body, {"acf": {"seats": 60, "venue": "Barn"}}) == ()
    assert verify(body, {"acf": {"seats": 40, "venue": "Barn"}}) == ("acf.seats",)
    assert undo_body(body, {"acf": {"seats": 40, "venue": "Hall"}}) == {
        "acf": {"seats": 40, "venue": "Hall"}
    }
    with pytest.raises(EditRefused):
        body_for(sheet, row, [FieldChange("acf.seats", "Seats", 40, "many")], meta_schema=lookup)


def test_every_field_plugin_the_prd_names_is_classified_honestly() -> None:
    scope = {s.plugin: s for s in fp.FIELD_PLUGIN_SCOPE}
    assert {"Advanced Custom Fields", "Meta Box", "Pods", "CMB2"} <= set(scope)
    assert scope["Advanced Custom Fields"].status == "read and write"
    assert scope["CMB2"].status == "not integrated"
    assert all("No adapter" in scope[p].workbench or "no adapter" in scope[p].workbench
               for p in ("Meta Box", "Pods", "CMB2"))  # fmt: skip
    assert any(s.plugin.startswith("Registered meta") for s in fp.FIELD_PLUGIN_SCOPE)


# -- stale claims after plugin, theme or version changes ----------------------------------


def _info(version: str = "6.9", namespaces: tuple[str, ...] = ("wp/v2",)) -> SiteInfo:
    return SiteInfo("Radio", "", "https://radio.example", version, namespaces, "", ("/wp/v2",))


def test_a_stamp_says_what_changed_and_nothing_when_nothing_did() -> None:
    plugins = [{"plugin": "akismet/akismet", "version": "5.0", "status": "active"}]
    old = stamp_of(_info(), ADMIN, plugins=plugins, theme={"stylesheet": "twentyfive"})
    assert stamp_changes(old, stamp_of(_info(), ADMIN, plugins=plugins,
                                       theme={"stylesheet": "twentyfive"})) == []  # fmt: skip
    assert stamp_changes(None, old) == []
    moved = stamp_of(
        _info("7.0", ("wp/v2", "acf/v1")),
        Account(1, "Jeff", "jeff", ("editor",), frozenset({"edit_posts"})),
        plugins=[
            {"plugin": "akismet/akismet", "version": "5.1", "status": "inactive"},
            {"plugin": "acf/acf", "version": "6.3", "status": "active"},
        ],
        theme={"stylesheet": "radio-child"},
    )
    said = stamp_changes(old, moved)
    assert "WordPress went from 6.9 to 7.0" in said
    assert "akismet is now inactive" in said and "acf was installed" in said
    assert "the theme is now radio-child" in said
    assert "the site's REST namespaces changed" in said
    assert "your role is now editor" in said


class _StampApi:
    def __init__(self, admin: bool) -> None:
        self.admin = admin
        self.asked: list[str] = []

    def get(self, route: str, **_p: Any) -> Any:
        self.asked.append(route)
        if route == "":
            return {"name": "Radio", "namespaces": ["wp/v2"], "routes": {"/wp/v2": {}}}
        if route == "wp/v2/users/me":
            caps = {"activate_plugins": True, "switch_themes": True} if self.admin else {}
            return {"id": 1, "roles": ["administrator" if self.admin else "author"],
                    "capabilities": caps}  # fmt: skip
        if route == "wp/v2/plugins":
            return [{"plugin": "acf/acf", "version": "6.3", "status": "active"}]
        if route == "wp/v2/themes":
            return [{"stylesheet": "radio", "version": "1.2"}]
        raise WordPressApiError("not here", status=404)

    def request(self, *_a: Any, **_k: Any) -> Any:
        raise WordPressApiError("not here", status=404)


def test_read_stamp_reads_plugins_and_theme_only_where_the_account_may() -> None:
    api = _StampApi(admin=True)
    stamp, info, account = read_stamp(api)  # type: ignore[arg-type]
    assert stamp.plugins == (("acf/acf", "6.3", "active"),) and stamp.theme == "radio 1.2"
    assert info.namespaces == ("wp/v2",) and account.roles == ("administrator",)
    author = _StampApi(admin=False)
    stamp, _info2, _account = read_stamp(author)  # type: ignore[arg-type]
    assert stamp.plugins is None and stamp.theme is None
    assert "wp/v2/plugins" not in author.asked


# -- QUILL Site Types ---------------------------------------------------------------------


class _QstApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []
        self.forbidden = False

    def get(self, route: str, **params: Any) -> Any:
        self.calls.append(("GET", route, params))
        if self.forbidden:
            raise WordPressApiError("no", status=403)
        if route == f"{qst.NAMESPACE}/types":
            return [{"slug": "book", "name": "Books"}]
        if route == f"{qst.NAMESPACE}/taxonomies":
            return [{"slug": "genre", "name": "Genres"}]
        if route == f"{qst.NAMESPACE}/field-groups":
            return [{"id": "book_facts", "title": "Book facts",
                     "fields": [{"name": "isbn", "kind": "text"}]}]  # fmt: skip
        if route == f"{qst.NAMESPACE}/kinds":
            return [{"kind": "text"}, {"kind": "picture"}, {"kind": "stars"}]
        if route == f"{qst.NAMESPACE}/export":
            return {"format": params["format"], "filename": "quill-site-types-export.php",
                    "content": "<?php\nregister_post_type( 'book' );\n"}  # fmt: skip
        if route == "wp/v2/types":
            return {"post": {"name": "Posts", "rest_base": "posts"},
                    "book": {"name": "Books", "rest_base": "book"}}  # fmt: skip
        if route == "wp/v2/taxonomies":
            return {"genre": {"name": "Genres", "rest_base": "genre"}}
        return []

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.calls.append(("POST", route, body))
        return dict(body or {})

    def delete(self, route: str, **_p: Any) -> Any:
        self.calls.append(("DELETE", route, None))
        return {"deleted": True, "previous": {"slug": "book", "name": "Books"}}


def test_site_types_definitions_kinds_and_bodies() -> None:
    api = _QstApi()
    found = qst.read_definitions(api)  # type: ignore[arg-type]
    assert set(found.types) == {"book"} and set(found.groups) == {"book_facts"}
    kinds = qst.read_kinds(api)  # type: ignore[arg-type]
    assert "stars" in kinds  # the site's own kind counts
    fields = qst.parse_fields("isbn: text, cover: picture\nrating", kinds)
    assert [(f["name"], f["kind"]) for f in fields] == [
        ("isbn", "text"), ("cover", "picture"), ("rating", "text")
    ]  # fmt: skip
    body = qst.define_body("field_group", "Book_Facts", "", attach="book", fields=fields)
    assert body["id"] == "book_facts" and body["attach"] == {"post_types": ["book"]}
    with pytest.raises(EditRefused, match="no field kind called colourwheel"):
        qst.parse_fields("tint: colourwheel", kinds)
    with pytest.raises(EditRefused, match="underscore"):
        qst.parse_fields("_secret: text", kinds)
    with pytest.raises(EditRefused, match="at least one field"):
        qst.define_body("field_group", "empty", "Empty")
    with pytest.raises(EditRefused, match="small letters"):
        qst.define_body("type", "Has Spaces!", "Nope")
    summary, lines = qst.define_preview("Radio", "taxonomy", qst.define_body(
        "taxonomy", "genre", "Genres", attach="book, post"))  # fmt: skip
    assert "Define the taxonomy Genres on Radio" in summary
    assert lines == ["Taxonomy: Genres (genre)", "For: book, post"]


def test_site_types_define_stop_put_back_and_export() -> None:
    api = _QstApi()
    qst.define(api, "type", {"slug": "film", "name": "Films"})  # type: ignore[arg-type]
    assert api.calls[-1] == ("POST", f"{qst.NAMESPACE}/types", {"slug": "film", "name": "Films"})
    previous = qst.stop_defining(api, "type", "book")  # type: ignore[arg-type]
    assert api.calls[-1] == ("DELETE", f"{qst.NAMESPACE}/types/book", None)
    assert qst.put_back(api, "type", previous) == "book is defined again."  # type: ignore[arg-type]
    assert api.calls[-1][2] == {"slug": "book", "name": "Books"}
    name, content = qst.export_code(api, "php")  # type: ignore[arg-type]
    assert name == "quill-site-types-export.php" and "register_post_type" in content


def test_a_non_administrator_is_told_why_definitions_are_out_of_reach() -> None:
    api = _QstApi()
    api.forbidden = True
    found = qst.read_definitions(api)  # type: ignore[arg-type]
    assert "Administrator role" in found.reason and not found.types


def test_the_content_model_marks_site_types_definitions_editable() -> None:
    from quill.core.wordpress.workbench_discovered import (
        EDITABLE,
        READ_ONLY,
        SITE_TYPES_NAMESPACE,
        model_rows,
    )

    rows = {
        r.key: r for r in model_rows(_QstApi(), "Radio", namespaces=("wp/v2", SITE_TYPES_NAMESPACE))
    }  # type: ignore[arg-type]  # noqa: E501
    assert rows["post"].cell("definition") == READ_ONLY
    assert rows["book"].cell("definition") == EDITABLE
    assert rows["book"].cell("registered_by") == "QUILL Site Types"
    assert rows["book"].raw["editable_definition"] is True
    assert rows["genre"].subkind == "taxonomy" and rows["genre"].raw["editable_definition"]
    group = rows["book_facts"]
    assert group.subkind == "field_group" and "isbn (text)" in group.detail
    # Without the plugin's namespace nothing is asked of it and nothing is editable.
    plain = _QstApi()
    assert all(r.cell("definition") == READ_ONLY for r in model_rows(plain, "Radio"))  # type: ignore[arg-type]
    assert not any("quill-site-types" in c[1] for c in plain.calls)


def test_coverage_names_site_types_as_covered_and_field_plugins_honestly() -> None:
    from quill.core.wordpress.workbench_coverage import classify

    found = classify("/quill-site-types/v1/field-groups", ["GET", "POST"])
    assert found.status == "covered" and "Content Model" in found.home
    for route, name in (("/pods/v1/pods", "Pods"), ("/cmb2/v1/boxes", "CMB2")):
        assert classify(route, ["GET"]).home.startswith(f"{name}: deferred"), route


# -- settings explained with the site's own example (WP-R-047) ----------------------------


def test_every_listed_setting_has_an_example_from_the_sites_own_value() -> None:
    from quill.core.wordpress.site_admin import SETTINGS_FIELDS
    from quill.core.wordpress.workbench_settings_help import EXPLAINED, explain

    assert {key for key, _label, _kind in SETTINGS_FIELDS} == set(EXPLAINED)
    site = {"date_format": "F j, Y", "time_format": "g:i a", "start_of_week": 1,
            "show_on_front": "posts", "page_on_front": 3,
            "default_comment_status": "closed"}  # fmt: skip
    pages = {3: ("Welcome", "https://radio.example/welcome/")}
    assert explain("date_format", site) == "F j, Y: a date reads November 9, 2026."
    assert explain("time_format", site) == "g:i a: a time reads 2:05 pm."
    assert explain("start_of_week", site) == "Calendars start their week on Monday."
    assert "so it is unused" in explain("page_on_front", site, pages=pages)
    assert explain("show_on_front", site, site_url="https://radio.example/") == (
        "Your home page, https://radio.example, lists your latest posts."
    )
    assert "no comments" in explain("default_comment_status", site)
    assert explain("not_a_setting", site) == ""


# -- QUILL Site Types: one field at a time, and a kind of the site's own -------------------

GROUP = {"id": "facts", "title": "Facts", "attach": {"post_types": ["book"]},
         "fields": [{"name": "isbn", "label": "ISBN", "kind": "text", "required": False,
                     "choices": []},
                    {"name": "tone", "kind": "choice", "choices": ["a", "b"]}]}  # fmt: skip


def test_a_field_change_keeps_the_rest_of_the_group_and_is_checked() -> None:
    kinds = ("text", "choice", "picture")
    after = qst.apply_field(GROUP, "isbn", {"label": "ISBN-13", "required": True,
                                             "name": "renamed"}, kinds)  # fmt: skip
    assert after["fields"][0] == {"name": "isbn", "label": "ISBN-13", "kind": "text",
                                  "required": True, "choices": []}  # fmt: skip
    assert after["fields"][1] == GROUP["fields"][1] and after["attach"] == GROUP["attach"]
    summary, lines = qst.field_preview("Radio", GROUP, "isbn", after)
    assert summary.startswith("Change the field isbn in Facts on Radio")
    assert lines == ["label: ISBN becomes ISBN-13", "required: False becomes True"]
    with pytest.raises(EditRefused, match="one of its choices"):
        qst.apply_field(GROUP, "tone", {"default": "c"}, kinds)
    with pytest.raises(EditRefused, match="no field kind called stars"):
        qst.apply_field(GROUP, "isbn", {"kind": "stars"}, kinds)
    added = qst.apply_field(GROUP, "", {"name": "cover", "kind": "picture"}, kinds)
    assert added["fields"][-1]["name"] == "cover" and added["fields"][-1]["label"] == "Cover"
    with pytest.raises(EditRefused, match="already"):
        qst.apply_field(GROUP, "", {"name": "isbn"}, kinds)
    values = qst.field_values(GROUP["fields"][1])
    assert values["choices"] == ("a", "b") and values["required"] is False
    assert [f.key for f in qst.field_sheet(kinds, new=False).pages[0].fields][:2] == [
        "name", "kind"]  # fmt: skip


def test_a_site_kind_is_checked_before_it_is_sent() -> None:
    body = qst.kind_body("Stars", "Stars", "integer")
    assert body == {"kind": "stars", "label": "Stars", "schema": {"type": "integer"}}
    with pytest.raises(EditRefused, match="built-in"):
        qst.kind_body("email", "Mail", "string")
    with pytest.raises(EditRefused, match="Only a kind stored as text"):
        qst.kind_body("n", "N", "number", "^1$")
    with pytest.raises(EditRefused, match="not a regular expression"):
        qst.kind_body("bad", "Bad", "string", "([")
    summary, lines = qst.kind_preview("Radio", qst.kind_body("isbn13", "", "string", r"^\d+$"))
    assert "cannot be undone" in summary and lines[-1].startswith("Values must match")
