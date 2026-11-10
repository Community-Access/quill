"""The W1 to W4 leftovers in the core: paging, columns, groups, New Here, terms, roles, spam, F1."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
from quill.core.wordpress.workbench_copy_sheet import (
    COPY_FIELDS,
    copy_answer,
    copy_sheet,
    copy_values,
)
from quill.core.wordpress.workbench_create import (
    allow_sender_words,
    creatable,
    create,
    empty_spam,
    merge_preview,
    merge_terms,
    password_reset_pointer,
    role_rows,
)
from quill.core.wordpress.workbench_listing import (
    ALL_PAGES,
    Paging,
    cut_words,
    extra_cell,
    group_instance,
    groups,
    page_limit,
    pages_for,
    parse_group,
)
from quill.core.wordpress.workbench_node_help import ROW_HELP, node_help
from quill.core.wordpress.workbench_rows import WbRow, item_row
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE


def _item(status: str, ident: int, **raw: Any) -> WbRow:
    return item_row(
        {"id": ident, "status": status, "title": {"raw": f"T{ident}"}, **raw}, "post", "S"
    )


def test_paging_grows_by_three_pages_and_load_all_stops_at_the_ceiling() -> None:
    paging = Paging(first=3)
    assert paging.pages("n") == 3
    assert paging.more("n") == 6
    assert paging.all("n") == ALL_PAGES
    assert paging.more("n") == ALL_PAGES


def test_page_limit_is_the_context_loaders_read() -> None:
    assert pages_for(3) == 3
    with page_limit(9):
        assert pages_for(3) == 9
    assert pages_for(3) == 3


def test_cut_words_say_when_a_list_stopped_short() -> None:
    assert cut_words(120, 3) == ""
    assert "Load More" in cut_words(300, 3)
    assert "the most" in cut_words(ALL_PAGES * 100, ALL_PAGES)


def test_extra_cells_come_from_the_object_the_site_sent() -> None:
    row = _item("draft", 4, slug="hello", comment_status="open", sticky=True)
    assert extra_cell(row, "slug") == "hello"
    assert extra_cell(row, "id") == "4"
    assert extra_cell(row, "comments") == "open"
    assert extra_cell(row, "sticky") == "yes"


def test_groups_count_each_value_in_order_and_the_instance_round_trips() -> None:
    rows = [_item("draft", 1), _item("publish", 2), _item("draft", 3)]
    assert groups(rows, "status") == [("Draft", 2), ("Published", 1)]
    instance = group_instance("S", "\x1f", "status", "Draft")
    kind = instance.partition("\x1f")[2]
    assert parse_group(kind) == ("status", "Draft")
    assert parse_group("event") is None


def test_every_grouped_node_has_a_group_child_within_four_levels() -> None:
    for parent in ("posts", "pages", "media", "comments", "plugins"):
        node = WORDPRESS_TREE.template_node("site", f"{parent}_group")
        assert node.dynamic and node.parent == parent and not node.home


def test_new_here_knows_every_creatable_kind() -> None:
    assert creatable("posts").kind == "post"  # type: ignore[union-attr]
    assert creatable("pages_drafts").kind == "page"  # type: ignore[union-attr]
    assert creatable("categories").family == "terms"  # type: ignore[union-attr]
    assert creatable("tags").kind == "post_tag"  # type: ignore[union-attr]
    assert creatable("menus").family == "menus"  # type: ignore[union-attr]
    event = creatable("custom_type", "event", dynamic_label="Events")
    assert event is not None and event.kind == "event" and event.noun == "event"
    assert creatable("custom_taxonomy", "genre").family == "terms"  # type: ignore[union-attr]
    assert creatable("settings") is None


class _Address:
    wpcom_site = ""
    site_url = "https://radio.example"


class _Auth:
    kind = "app_password"
    username = "jeff"


class _Api:
    address = _Address()
    auth = _Auth()

    def __init__(self) -> None:
        self.posts = {1: {"id": 1, "categories": [5, 6]}, 2: {"id": 2, "categories": [5]}}
        self.writes: list[tuple[str, str, Any]] = []

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route.startswith("wp/v2/posts/"):
            self.posts[int(route.rsplit("/", 1)[1])].update(body)
        return {"id": 99, **(body or {})}

    def get(self, route: str, **params: Any) -> Any:
        if route.startswith("wp/v2/posts/"):
            return dict(self.posts[int(route.rsplit("/", 1)[1])])
        if route == "wp/v2/settings":
            return {}
        return []

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {}

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Any:
        params = dict(params or {})
        if route == "wp/v2/posts" and "categories" in params:
            for post in self.posts.values():
                if params["categories"] in post["categories"]:
                    yield {"id": post["id"]}
        if route == "wp/v2/comments":
            yield {"id": 7}
            yield {"id": 8}


def test_create_sends_drafts_terms_and_menus() -> None:
    api = _Api()
    create(api, creatable("posts"), {"title": "Hi"})  # type: ignore[arg-type]
    create(api, creatable("categories"), {"name": "Shows", "parent": "5"})  # type: ignore[arg-type]
    create(api, creatable("menus"), {"name": "Footer"})  # type: ignore[arg-type]
    assert api.writes[0] == ("POST", "wp/v2/posts", {"title": "Hi", "status": "draft"})
    assert api.writes[1] == ("POST", "wp/v2/categories", {"name": "Shows", "parent": 5})
    assert api.writes[2] == ("POST", "wp/v2/menus", {"name": "Footer"})


def test_merge_previews_then_moves_every_item_and_deletes_the_old_term() -> None:
    api = _Api()
    preview = merge_preview(api, "category", (5, "News"), (6, "Shows"))
    assert len(preview.items) == 2 and "2 items filed under News" in preview.sentence
    assert merge_terms(api, "category", 5, 6, preview) == []
    assert api.posts[1]["categories"] == [6]
    assert api.posts[2]["categories"] == [6]
    assert ("DELETE", "wp/v2/categories/5", {"force": True}) in api.writes


def test_roles_read_in_plain_words_and_the_reset_is_a_wp_admin_pointer() -> None:
    rows = dict(role_rows())
    assert "publish pages" in rows["Editor"]
    assert rows["Subscriber"].startswith("Can read")
    address, sentence = password_reset_pointer("https://radio.example/", 4, "Ann")
    assert address == "https://radio.example/wp-admin/user-edit.php?user_id=4"
    assert "Send Reset Link" in sentence


def test_empty_spam_deletes_for_good_and_allow_sender_reads_the_settings() -> None:
    api = _Api()
    assert empty_spam(api, [7, 8]) == []
    assert ("DELETE", "wp/v2/comments/8", {"force": True}) in api.writes
    assert "lets their next comments" in allow_sender_words("Ann", {})
    assert "will wait too" in allow_sender_words("Ann", {"comment_previously_approved": False})


def test_the_editor_properties_sheet_is_the_workbench_item_sheet() -> None:
    sheet = copy_sheet("post")
    keys = {spec.key for spec in sheet.fields()}
    assert {"title", "slug", "categories", "tags", "sticky", "format"} <= keys
    assert keys - {"about"} <= COPY_FIELDS
    values = copy_values(
        title="Hi",
        status="draft",
        properties={"categories": [5], "slug": "hi"},
        facts="Site: Radio",
        categories=[(5, "News")],
    )
    assert values["categories"] == ("News (5)",)
    answer = copy_answer(
        {"categories": ("News", "Nope"), "parent": "3", "title": " New "},
        categories=[(5, "News")],
    )
    assert answer.properties == {"categories": [5], "parent": 3}
    assert answer.title == "New" and answer.unknown_terms == ["Nope"]
    assert "parent" in {s.key for s in copy_sheet("page").fields()}


def test_every_node_and_row_type_has_f1_help() -> None:
    for _template, node in WORDPRESS_TREE.all_nodes():
        assert node_help(node.key), node.key
    for kind in WORDPRESS_ACTIONS.row_types:
        if kind != "node":
            assert kind in ROW_HELP, kind


# -- W5: what a site says about itself ------------------------------------------


def test_the_content_model_says_who_registered_each_type() -> None:
    from quill.core.wordpress.workbench_discovered import model_rows, registered_by

    assert registered_by("post") == "WordPress"
    assert registered_by("tribe_events") == "The Events Calendar"
    assert registered_by("product") == "WooCommerce"
    assert registered_by("event") == "a plugin or the theme"
    assert registered_by("book", "acme/v1") == "the plugin behind acme/v1"

    class _Types:
        def get(self, route: str, **_p: Any) -> Any:
            if route == "wp/v2/types":
                return {"post": {"name": "Posts", "rest_base": "posts"}, "event": {"name": "E"}}
            return {"genre": {"name": "Genres", "rest_base": "genres"}}

    rows = model_rows(_Types(), "S")  # type: ignore[arg-type]
    assert [(r.key, r.cell("registered_by")) for r in rows] == [
        ("post", "WordPress"),
        ("event", "a plugin or the theme"),
        ("genre", "a plugin or the theme"),
    ]
    assert "Read only" in rows[0].detail


def test_routes_list_by_namespace_with_where_each_is_reached() -> None:
    from quill.core.wordpress.workbench_discovered import namespace_rows, route_rows

    namespaces = ["wp/v2", "acme/v1"]
    routes = {"/wp/v2/posts": ["GET", "POST"], "/acme/v1/things": ["GET"]}
    ns = namespace_rows("S", namespaces, list(routes))
    assert [(r.key, r.cell("routes"), r.cell("reached")) for r in ns] == [
        ("wp/v2", "1", "1"),
        ("acme/v1", "1", "1"),
    ]
    rows = route_rows("S", "acme/v1", namespaces, routes)
    assert [r.key for r in rows] == ["/acme/v1/things"]
    assert rows[0].cell("coverage") == "built from what the site says"


def test_an_ability_runs_from_its_input_schema_after_a_preview() -> None:
    from quill.core.wordpress.abilities import Ability
    from quill.core.wordpress.workbench_discovered import (
        ability_input,
        ability_preview,
        ability_sheet,
        ability_values,
    )

    ability = Ability(
        "acme/count",
        "Count Things",
        "Counts things.",
        readonly=True,
        input_schema={
            "properties": {
                "limit": {"type": "integer", "default": 5},
                "kind": {"type": "string", "enum": ["a", "b"]},
            }
        },
    )
    keys = {spec.key for spec in ability_sheet(ability).fields()}
    assert {"limit", "kind"} <= keys
    assert ability_values(ability)["limit"] == 5
    given = ability_input(ability, {"limit": "12", "kind": "b", "about": "x"})
    assert given == {"limit": 12, "kind": "b"}
    summary, lines = ability_preview("Radio", ability, given)
    assert "only reads" in summary and lines == ["limit: 12", 'kind: "b"']
