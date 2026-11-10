"""The WordPress Workbench's wx-free half: tree, filters, sheets, saves, forms, permissions."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import Account, SiteInfo
from quill.core.wordpress.workbench_actions import WINDOW_MENU, WORDPRESS_ACTIONS, command
from quill.core.wordpress.workbench_attention import gather
from quill.core.wordpress.workbench_edit import (
    EditRefused,
    body_for,
    run_batch,
    trash,
    undo_body,
    verify,
)
from quill.core.wordpress.workbench_filter import local_matches, params_for
from quill.core.wordpress.workbench_flag import workbench_window_enabled
from quill.core.wordpress.workbench_forms import form_plugins, load_forms, set_entry_spam
from quill.core.wordpress.workbench_help import KEYS, WORDPRESS_HELP
from quill.core.wordpress.workbench_load import SiteContext
from quill.core.wordpress.workbench_people import create_app_password, remove_user
from quill.core.wordpress.workbench_permissions import (
    Access,
    AccessStore,
    account_as_role,
    deactivate_warning,
    refusal,
    remove_problem,
    role_change_problem,
    tier_allowed,
)
from quill.core.wordpress.workbench_rows import WbRow, item_row, media_row, tree_order
from quill.core.wordpress.workbench_sheets import schema_sheet, sheet_for, term_ids, values_for
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE, door_node
from quill.core.workbench.actions import Tier
from quill.core.workbench.filters import parse
from quill.core.workbench.menus import rows
from quill.core.workbench.properties import FieldChange, FieldKind

ADMIN = Account(1, "Jeff", "jeff", ("administrator",), frozenset({"manage_options"}))
AUTHOR = Account(2, "Ann", "ann", ("author",), frozenset({"publish_posts", "edit_posts"}))


class Api:
    """A tiny site: answers by route, records writes."""

    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        self.answers = answers or {}
        self.writes: list[tuple[str, str, Any]] = []
        self.batch_error: WordPressApiError | None = None

    def get(self, route: str, **params: Any) -> Any:
        found = self.answers.get(route, [])
        return found(params) if callable(found) else found

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        found = self.get(route, **dict(params or {}))
        yield from found if isinstance(found, list) else []

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body))
        return {"id": 1, **(body or {})}

    def request(self, method: str, route: str, **kw: Any) -> Any:
        self.writes.append((method, route, kw.get("json_body")))
        return None

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {"id": 1, "status": "trash"}

    def batch(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.batch_error is not None:
            raise self.batch_error
        return [{"status": 200, "body": r["body"]} for r in requests]


def _ctx(api: Any, namespaces: tuple[str, ...] = ("wp/v2",)) -> SiteContext:
    info = SiteInfo("Radio", "", "https://radio.example", "7.1", namespaces, "")
    return SiteContext("Radio", api, url="https://radio.example", account=ADMIN, info=info)


# --------------------------------------------------------------------------- #
# tree, menu, help, flag


def test_the_tree_is_at_most_four_deep_and_names_every_site_part() -> None:
    assert WORDPRESS_TREE.depth("sites") <= 4
    keys = {node.key for node in WORDPRESS_TREE.template("site")}
    assert {
        "overview",
        "posts",
        "pages",
        "media",
        "comments",
        "categories",
        "tags",
        "menus",
        "themes",
        "forms",
        "users",
        "app_passwords",
        "plugins",
        "settings",
        "site_health",
        "abilities",
        "custom_type",
        "custom_taxonomy",
    } <= keys


def test_every_door_lands_on_a_site_node() -> None:
    keys = {node.key for node in WORDPRESS_TREE.template("site")}
    for door in ("wordpress.comments", "wordpress.media_library", "wordpress.users"):
        assert door_node(door) in keys
    assert door_node("wordpress.nothing") == ""


def test_every_key_the_help_teaches_is_on_the_menu_or_the_frame() -> None:
    bound = {row.key for _menu, row in rows(WINDOW_MENU)} | {"Enter", "F6", "Alt+1"}
    for key, _does in KEYS:
        first = key.split(" ")[0].rstrip(".")
        if first in ("Ctrl+Shift+1",):
            continue
        assert first in bound, key
    assert "start_here" in WORDPRESS_HELP


def test_delete_never_is_a_default_and_properties_ends_every_menu() -> None:
    for kind in WORDPRESS_ACTIONS.row_types:
        first = WORDPRESS_ACTIONS.default_for(kind)
        assert first.tier <= Tier.ORGANIZE or kind == "node", kind
        assert WORDPRESS_ACTIONS.rows_for(kind)[-1].command_id == command("sheet")


def test_the_workbench_is_the_default_and_classic_windows_are_a_choice(tmp_path) -> None:
    from quill.core.wordpress.workbench_options import (
        WorkbenchOptions,
        load_options,
        save_options,
    )

    assert workbench_window_enabled({}, base=tmp_path)
    save_options(WorkbenchOptions(classic_windows=True), tmp_path)
    assert load_options(tmp_path).classic_windows
    assert not workbench_window_enabled({}, base=tmp_path)
    assert workbench_window_enabled({"QUILL_WORDPRESS_WORKBENCH_WINDOW": "1"}, base=tmp_path)
    save_options(WorkbenchOptions(), tmp_path)
    assert not workbench_window_enabled({"QUILL_WORDPRESS_WORKBENCH_WINDOW": "0"}, base=tmp_path)


# --------------------------------------------------------------------------- #
# rows and filters


def test_pages_read_as_a_tree_by_parent() -> None:
    raw = [
        {"id": 1, "title": {"rendered": "About"}, "parent": 0},
        {"id": 2, "title": {"rendered": "Team"}, "parent": 1},
        {"id": 3, "title": {"rendered": "Contact"}, "parent": 0},
    ]
    ordered = tree_order([item_row(r, "page", "Radio") for r in raw])
    assert [(r.title, r.cell("level")) for r in ordered] == [
        ("About", "1"),
        ("Team", "2"),
        ("Contact", "1"),
    ]


def test_the_filter_is_the_rest_query() -> None:
    params = params_for(parse("status:draft,pending -tag:4 sticky:yes tax_relation:OR words"))
    assert params == {
        "status": ["draft", "pending"],
        "tags_exclude": [4],
        "sticky": True,
        "search": "words",
    }
    with pytest.raises(Exception, match="cannot be filtered"):
        params_for(parse("nonsense:1"))


def test_local_filtering_matches_cells_and_raw() -> None:
    row = WbRow("plugin", "Radio", "akismet", {"plugin": "Akismet", "status": "active"}, "")
    assert local_matches(row, parse("status:active").conditions)
    assert not local_matches(row, parse("-status:active").conditions)


# --------------------------------------------------------------------------- #
# sheets and saves


def test_media_rows_say_when_a_picture_has_no_alt_text() -> None:
    row = media_row({"id": 4, "mime_type": "image/png", "title": {"rendered": "Logo"}}, "Radio")
    assert "no alt text" in row.detail and row.cell("alt_text") == "none"


def test_terms_read_back_by_id_or_name_and_unknown_names_are_named() -> None:
    assert term_ids(["News (12)", "4", "shows"], {"Shows": 9}) == ([12, 4, 9], [])
    assert term_ids(["Nowhere"], {}) == ([], ["Nowhere"])


def test_an_item_body_carries_only_changes_by_wordpress_names() -> None:
    raw = {"id": 1, "title": {"raw": "Hi"}, "categories": [3], "type": "post", "meta": {"x": 1}}
    row = item_row(raw, "post", "Radio")
    sheet = sheet_for(row, taxonomies={"categories": "Categories"}, meta={"x": {"type": "integer"}})
    changes = (
        FieldChange("categories", "Categories", ("3",), ("News", "7")),
        FieldChange("meta.x", "x", 1, "2"),
    )
    body = body_for(sheet, row, changes, term_names={"categories": {"News": 5}})
    assert body == {"categories": [5, 7], "meta": {"x": "2"}}
    with pytest.raises(EditRefused, match="nothing on Radio is called Old"):
        body_for(sheet, row, (FieldChange("categories", "Categories", (), ("Old",)),))


def test_verify_names_what_the_site_did_not_keep_and_undo_puts_it_back() -> None:
    assert verify({"slug": "a-b", "password": "x"}, {"slug": "a-b-2"}) == ("slug",)
    assert undo_body({"title": "New"}, {"title": {"raw": "Old"}}) == {"title": "Old"}


def test_schema_built_sheets_map_types_to_controls() -> None:
    sheet = schema_sheet(
        "event",
        "Event",
        {
            "venue": {"type": "string"},
            "free": {"type": "boolean"},
            "seats": {"type": "integer"},
            "kind": {"type": "string", "enum": ["talk", "show"]},
            "starts": {"type": "string", "format": "date-time"},
            "id": {"type": "integer", "readonly": True},
            "where": {"type": "object"},
        },
    )
    kinds = {f.key: (f.kind, f.readonly) for f in sheet.fields()}
    assert kinds["venue"] == (FieldKind.TEXT, False)
    assert kinds["free"][0] is FieldKind.CHECK and kinds["seats"][0] is FieldKind.NUMBER
    assert kinds["kind"][0] is FieldKind.CHOICE and kinds["starts"][0] is FieldKind.DATE
    assert kinds["id"] == (FieldKind.NUMBER, True) and kinds["where"] == (FieldKind.MULTILINE, True)


def test_the_password_is_never_shown_back() -> None:
    row = item_row({"id": 1, "title": {"raw": "Hi"}, "password": "secret"}, "post", "Radio")
    assert values_for(row)["password"] == ""


def test_a_batch_falls_back_to_one_at_a_time_when_the_site_will_not_batch() -> None:
    api = Api()
    api.batch_error = WordPressApiError("no", status=404, wp_code="rest_no_route")
    row = item_row({"id": 1, "title": {"raw": "Hi"}}, "post", "Radio")
    results = run_batch(api, [row], [{"status": "publish"}])
    assert results[0].ok and api.writes == [("POST", "wp/v2/posts/1", {"status": "publish"})]


def test_only_posts_and_comments_go_to_the_trash() -> None:
    api = Api()
    with pytest.raises(EditRefused, match="no Trash"):
        trash(api, media_row({"id": 4, "mime_type": "image/png"}, "Radio"))
    trash(api, item_row({"id": 1}, "post", "Radio"))
    assert api.writes == [("DELETE", "wp/v2/posts/1", {})]


# --------------------------------------------------------------------------- #
# Needs My Attention, forms and spam


def test_an_unreachable_site_is_one_row_and_does_not_hide_the_others() -> None:
    class Down(Api):
        def iter_collection(self, route: str, params: Any = None, **_kw: Any):
            raise WordPressApiError("Radio did not answer.")
            yield  # pragma: no cover

    good = Api({"wp/v2/comments": [{"id": 9, "author_name": "Ann", "status": "hold"}]})
    rows_found = gather("waiting", [_ctx(Down()), SiteContext("Other", good)])
    assert rows_found[0].key == "unreachable:Radio"
    assert [r.cell("author") for r in rows_found[1:]] == ["Ann"]


def test_forms_are_found_by_namespace_only() -> None:
    assert form_plugins(_ctx(Api())) == ()
    assert form_plugins(_ctx(Api(), ("wp/v2", "qaf/v1", "gf/v2"))) == ("qaf", "gravity")
    with pytest.raises(WordPressApiError, match="no forms plugin"):
        load_forms(_ctx(Api()), "all")


def test_qaf_spam_entries_and_not_spam() -> None:
    api = Api({
        "qaf/v1/forms": [{"id": 3, "title": "Contact", "entry_count": 1}],
        "qaf/v1/entries": lambda p: [
            {
                "id": 11,
                "form_id": 3,
                "status": p["status"],
                "created_at": "2026-11-09 10:00:00",
                "fields": {"name": "Spammer"},
            }
        ],
    })
    ctx = _ctx(api, ("qaf/v1",))
    held = load_forms(ctx, "spam")
    assert held[0].status == "spam" and held[0].cell("status") == "Held as spam"
    assert set_entry_spam(ctx, held, False) == []
    assert api.writes[-1] == ("POST", "qaf/v1/entries/11", {"status": "active"})


def test_gravity_forms_entries_and_spam_send_the_whole_entry() -> None:
    entry = {
        "id": "5",
        "form_id": "1",
        "status": "active",
        "date_created": "2026-11-09",
        "1": "Ann",
    }
    api = Api({
        "gf/v2/forms": {"1": {"id": "1", "title": "Signup", "entries": "1"}},
        "gf/v2/entries": {"entries": [entry]},
    })
    ctx = _ctx(api, ("gf/v2",))
    assert load_forms(ctx, "all")[0].cell("form") == "Signup"
    found = load_forms(ctx, "entries")
    assert found[0].cell("plugin") == "Gravity Forms"
    set_entry_spam(ctx, found, True)
    assert api.writes[-1] == ("PUT", "gf/v2/entries/5", {**entry, "status": "spam"})


# --------------------------------------------------------------------------- #
# permissions and people


def test_access_levels_and_their_store(tmp_path) -> None:
    assert tier_allowed(Tier.READ, Access.READ_ONLY)
    assert not tier_allowed(Tier.ORGANIZE, Access.READ_ONLY)
    assert tier_allowed(Tier.ORGANIZE, Access.ORGANIZE)
    assert not tier_allowed(Tier.DESTRUCTIVE, Access.ORGANIZE)
    store = AccessStore(tmp_path)
    assert store.get("s1") is Access.FULL
    store.set("s1", Access.ORGANIZE)
    assert AccessStore(tmp_path).get("s1") is Access.ORGANIZE


def test_refusals_name_the_role_needed_and_the_role_you_have() -> None:
    assert refusal("publish_posts", AUTHOR, "Radio") == ""
    said = refusal("moderate_comments", AUTHOR, "Radio")
    assert said == (
        "Moderating comments needs the Editor role or higher. You are an Author on Radio."
    )
    assert account_as_role(ADMIN, "contributor").can("edit_posts")
    assert not account_as_role(ADMIN, "contributor").can("manage_options")


USERS = [{"id": 1, "roles": ["administrator"]}, {"id": 2, "roles": ["author"]}]


def test_nobody_locks_themselves_out() -> None:
    assert "your own Administrator role" in role_change_problem(ADMIN, 1, "editor", USERS)
    other_admin = Account(5, "Bo", "bo", ("administrator",), frozenset())
    assert "only Administrator" in role_change_problem(other_admin, 1, "editor", USERS)
    assert role_change_problem(ADMIN, 2, "editor", USERS) == ""
    assert "your own account" in remove_problem(ADMIN, 1, USERS)
    assert "only Administrator" in remove_problem(other_admin, 1, USERS)
    with pytest.raises(EditRefused, match="someone else"):
        remove_user(Api(), ADMIN, 2, 2, USERS)


def test_deactivating_quills_own_plugin_warns() -> None:
    assert "Forms" in deactivate_warning("quill-accessible-forms/quill-accessible-forms.php")
    assert deactivate_warning("akismet/akismet.php") == ""


def test_a_new_application_password_keeps_its_secret_out_of_repr() -> None:
    class Made(Api):
        def post(self, route: str, body: Any = None, **params: Any) -> Any:
            return {"uuid": "u1", "name": body["name"], "password": "abcd efgh"}

    made = create_app_password(Made(), "  QUILL  laptop ")
    assert made.name == "QUILL laptop" and made.secret == "abcd efgh"
    assert "abcd" not in repr(made)
    with pytest.raises(EditRefused):
        create_app_password(Made(), "   ")
