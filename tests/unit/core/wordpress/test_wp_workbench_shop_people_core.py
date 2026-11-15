"""WP-A, WP-B and WP-G, wx-free: Shop, Shop Orders, Podcast, the seven orderings, and People.

Fakes stand in for the site; nothing here reaches a network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_load import SiteContext, load

SITE = "Radio"


@dataclass
class _Info:
    namespaces: tuple[str, ...]


class ShopApi:
    """A site with WooCommerce, a few posts (one an episode) and the types it lists."""

    def __init__(self, *, types: dict[str, Any] | None = None, refuse: int = 0) -> None:
        self.reads: list[tuple[str, dict[str, Any]]] = []
        self.types = types or {"post": {}, "page": {}}
        self.refuse = refuse

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/types":
            return self.types
        return []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        self.reads.append((route, dict(params or {})))
        if self.refuse:
            raise WordPressApiError("No.", status=self.refuse)
        if route == "wc/v3/products":
            yield {
                "id": 9,
                "name": "Mug",
                "price": "12.00",
                "stock_status": "instock",
                "status": "publish",
                "permalink": "https://radio.example/mug",
            }
        elif route == "wc/v3/orders":
            yield {
                "id": 77,
                "number": "1077",
                "status": "processing",
                "total": "24.00",
                "currency": "USD",
                "date_created_gmt": "2026-11-01T10:00:00",
                "billing": {
                    "first_name": "Ann",
                    "last_name": "Lee",
                    "email": "ann@example.com",
                    "phone": "555",
                },
                "shipping": {"address_1": "1 Main St", "city": "Town"},
                "line_items": [{"name": "Mug", "quantity": 2, "total": "24.00"}],
            }
        elif route in ("wp/v2/posts", "wp/v2/podcast"):
            yield {
                "id": 1,
                "title": {"raw": "Episode 4"},
                "status": "publish",
                "content": {"raw": '<!-- wp:audio {"id":5} -->\n<figure></figure>'},
            }
            yield {"id": 2, "title": {"raw": "News"}, "status": "publish", "content": {"raw": "Hi"}}


def _ctx(api: Any, *namespaces: str) -> SiteContext:
    ctx = SiteContext(SITE, api, url="https://radio.example")
    ctx.info = _Info(namespaces)  # type: ignore[assignment]
    return ctx


# -- Shop and Shop Orders ------------------------------------------------------------------


def test_the_shop_lists_woocommerce_products_read_only() -> None:
    api = ShopApi()
    rows = load(_ctx(api, "wp/v2", "wc/v3"), "shop:products", {}, {})
    assert [(r.kind, r.title, r.cell("price")) for r in rows] == [("shop_product", "Mug", "12.00")]
    assert rows[0].link == "https://radio.example/mug" and not rows[0].route
    assert api.reads[0][0] == "wc/v3/products"


def test_shop_orders_are_receipts_and_never_membership_orders() -> None:
    rows = load(_ctx(ShopApi(), "wc/v3"), "shop:orders", {}, {})
    (order,) = rows
    assert order.kind == "shop_order" and order.title == "Shop order 1077"
    assert order.cell("customer") == "Ann Lee" and order.cell("total") == "24.00 USD"
    assert "not a membership order" in order.raw["kind_of_order"]
    assert "Membership orders from Paid Memberships Pro" in order.detail
    assert "2 x Mug" in order.raw["items"]
    shown = repr(order.raw) + order.detail
    assert "ann@example.com" not in shown and "555" not in shown  # no contact details
    assert order.link == "https://radio.example/wp-admin/post.php?post=77&action=edit"


def test_a_site_without_woocommerce_says_so_and_asks_nothing() -> None:
    api = ShopApi()
    for loader in ("shop:products", "shop:orders"):
        with pytest.raises(WordPressApiError, match="does not list WooCommerce"):
            load(_ctx(api, "wp/v2"), loader, {}, {})
    assert api.reads == []


def test_a_role_that_cannot_read_the_shop_hears_why() -> None:
    with pytest.raises(WordPressApiError, match="manage_woocommerce"):
        load(_ctx(ShopApi(refuse=403), "wc/v3"), "shop:orders", {}, {})


# -- Podcast -------------------------------------------------------------------------------


def test_episode_posts_are_the_ones_with_an_episode_player() -> None:
    from quill.core.wordpress import episode as ep

    text, _islands = ep.episode_post(ep.Episode("Ep"), media_id=5, src="https://x/a.mp3")
    assert not ep.is_episode_post(text)  # the Markdown copy holds an island, not the block
    assert ep.is_episode_post('<!-- wp:audio {"id":5} -->')
    assert ep.is_episode_post('[audio src="a.mp3"]')
    assert not ep.is_episode_post("<p>No player</p>")


def test_podcast_lists_posts_with_a_player_when_the_site_has_no_podcast_type() -> None:
    api = ShopApi()
    rows = load(_ctx(api, "wp/v2"), "podcast:episodes", {}, {})
    assert [(r.kind, r.title) for r in rows] == [("item", "Episode 4")]
    assert api.reads[0][0] == "wp/v2/posts"


def test_podcast_lists_the_sites_own_podcast_type() -> None:
    api = ShopApi(
        types={"podcast": {"name": "Episodes", "rest_base": "podcast", "rest_namespace": "wp/v2"}}
    )
    rows = load(_ctx(api, "wp/v2"), "podcast:episodes", {}, {})
    assert api.reads[0][0] == "wp/v2/podcast"
    assert len(rows) == 2  # every item of the type, player or not


def test_a_site_with_no_podcast_says_so() -> None:
    class Plain(ShopApi):
        def iter_collection(self, route: str, params: Any = None, **_kw: Any):
            yield {"id": 2, "title": {"raw": "News"}, "content": {"raw": "Hi"}}

    with pytest.raises(WordPressApiError, match="has no podcast here"):
        load(_ctx(Plain(), "wp/v2"), "podcast:episodes", {}, {})


def test_shop_orders_and_podcast_are_real_nodes_with_help() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
    from quill.core.wordpress.workbench_node_help import NODE_HELP, ROW_HELP
    from quill.core.wordpress.workbench_tree import PLANNED_WORDS, WORDPRESS_TREE

    shop = WORDPRESS_TREE.template_node("site", "shop")
    orders = WORDPRESS_TREE.template_node("site", "shop_orders")
    podcast = WORDPRESS_TREE.template_node("site", "podcast")
    assert (shop.loader, orders.loader, podcast.loader) == (
        "shop:products",
        "shop:orders",
        "podcast:episodes",
    )
    assert orders.parent == "shop" and orders.label == "Shop Orders"
    assert PLANNED_WORDS == {}
    assert "not membership orders" in NODE_HELP["shop_orders"]
    assert "Shop orders are not membership orders" in NODE_HELP["orders"]
    for kind in ("shop_product", "shop_order"):
        assert kind in ROW_HELP and kind in WORDPRESS_ACTIONS.row_types


# -- WP-B: the seven orderings plugins add ------------------------------------------------


@pytest.mark.parametrize(
    "value", ["favorite_count", "popularity", "post__in", "price", "random", "rating", "sales"]
)
def test_each_plugin_ordering_is_said_in_words(value: str) -> None:
    from quill.core.wordpress.query import value_label

    said = value_label("orderby", value)
    assert said != value and said[:1].isupper()


def test_the_combination_test_has_no_planned_gaps_left() -> None:
    from quill.tools import wordpress_combination_audit as audit

    assert audit.gaps() == {}
    assert audit.load_snapshot() == {}


# -- WP-G: People > Users, the rest ----------------------------------------------------------


def test_sign_out_everywhere_points_at_wp_admin_and_says_rest_has_no_sessions() -> None:
    from quill.core.wordpress.workbench_people_admin import sign_out_pointer

    address, sentence = sign_out_pointer("https://radio.example/", 4, "Ann")
    assert address == "https://radio.example/wp-admin/user-edit.php?user_id=4"
    assert "no route that lists them" in sentence and "Log Out Everywhere" in sentence
    mine, said = sign_out_pointer("https://radio.example", 3, "Jeff", yourself=True)
    assert mine.endswith("/wp-admin/profile.php") and "Everywhere Else" in said


def test_others_passwords_need_edit_users_but_your_own_never_do() -> None:
    from quill.core.wordpress.site import Account
    from quill.core.wordpress.workbench_people_admin import passwords_refusal

    author = Account(3, "Jeff", "jeff", ("author",), frozenset({"edit_posts"}))
    admin = Account(1, "Al", "al", ("administrator",), frozenset({"edit_users"}))
    assert passwords_refusal(author, 3, "Jeff", SITE) == ""
    assert "edit_users" in passwords_refusal(author, 4, "Ann", SITE)
    assert passwords_refusal(admin, 4, "Ann", SITE) == ""


def test_invites_are_read_from_a_csv_with_every_row_left_out_said() -> None:
    from quill.core.wordpress.workbench_people_admin import parse_invites, preview_lines

    text = (
        "Email,Role,Name\n"
        "ann@example.com,Editor,Ann Lee\n"
        "bob@example.com,,Bob\n"
        "not-an-email,author,X\n"
        "cy@example.com,boss,Cy\n"
        "old@example.com,author,Old\n"
        "ANN@example.com,author,Again\n"
        "jeff@other.example,author,Jeff Two\n"
    )
    plan = parse_invites(text, existing_emails={"old@example.com"}, existing_usernames={"jeff"})
    assert [(i.email, i.role, i.username) for i in plan.invites] == [
        ("ann@example.com", "editor", "ann"),
        ("bob@example.com", "subscriber", "bob"),
        ("jeff@other.example", "author", "jeff2"),
    ]
    assert len(plan.problems) == 4
    lines = preview_lines(plan)
    assert lines[0] == "Add Ann Lee as Editor, signing in as ann, ann@example.com"
    assert any("already has an account" in line for line in lines)
    assert any("boss is not a role" in line for line in lines)


def test_a_csv_without_a_header_is_email_role_name() -> None:
    from quill.core.wordpress.workbench_people_admin import invite_body, parse_invites

    (invite,) = parse_invites("dee@example.com,author,Dee Day\n").invites
    body = invite_body(invite)
    assert body["roles"] == ["author"] and body["first_name"] == "Dee"
    assert len(body["password"]) >= 24  # REST requires one; nobody sees it


def test_send_invites_reports_each_row() -> None:
    from quill.core.wordpress.workbench_people_admin import parse_invites, send_invites

    class Api:
        def __init__(self) -> None:
            self.posts: list[dict[str, Any]] = []

        def post(self, route: str, body: Any = None, **_p: Any) -> Any:
            if body["email"].startswith("bad"):
                raise WordPressApiError("Sorry, that username already exists!", status=400)
            self.posts.append(body)
            return {"id": 9}

    api = Api()
    plan = parse_invites("a@example.com,author,A\nbad@example.com,author,B\n")
    results = send_invites(api, plan.invites)  # type: ignore[arg-type]
    assert [why for _i, why in results] == ["", "Sorry, that username already exists!"]
    assert api.posts[0]["email"] == "a@example.com"


def test_every_new_command_has_a_key_or_a_written_reason() -> None:
    from quill.core.wordpress.menu import layer_chord
    from quill.core.wordpress.workbench_admin_actions import KEYLESS, command

    verbs = ("user_app_passwords", "sign_out_everywhere", "invite_spreadsheet", "insert_picked")
    for verb in verbs:
        assert KEYLESS[command(verb)]
    assert layer_chord("wordpress.this_post_in_workbench") == "Ctrl+Alt+Shift+Grave, Shift+H"
