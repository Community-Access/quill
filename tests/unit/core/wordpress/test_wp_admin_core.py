"""The wx-free halves of Running the Site: trees, threads, sentences (wordpress.md 9.8 to 9.13)."""

from __future__ import annotations

from quill.core.wordpress import comments as cm
from quill.core.wordpress import navigation as nav
from quill.core.wordpress import site_admin as sa
from quill.core.wordpress import site_library as lib
from quill.core.wordpress import site_structure as ss
from quill.core.wordpress.site import Account, Term


def _nodes() -> list[nav.MenuNode]:
    return [
        nav.MenuNode("Home", "page", 1),
        nav.MenuNode("About", "page", 2, children=[nav.MenuNode("Team", "page", 3)]),
        nav.MenuNode("Donate", "link", url="https://x.example"),
    ]


def test_menu_tree_moves() -> None:
    nodes = _nodes()
    team = nodes[1].children[0]
    assert nav.move_up(nodes, nodes[0]) == ""
    assert nav.move_in(nodes, nodes[0]) == ""
    assert nav.move_out(nodes, nodes[0]) == ""
    assert nav.move_out(nodes, team) == "Team moved out, after About."
    assert [n.title for n in nodes] == ["Home", "About", "Team", "Donate"]
    assert nav.move_down(nodes, nodes[3]) == ""
    assert nav.move_in(nodes, nodes[3]) == "Donate is now under Team."
    nav.remove(nodes, nodes[2])
    assert [r.spoken() for r in nav.rows(nodes)] == [
        "Home, page, level 1, 1 of 3",
        "About, page, level 1, 2 of 3",
        "Donate, link, level 1, 3 of 3",
    ]


def test_navigation_round_trip_keeps_unknown_blocks() -> None:
    content = (
        '<!-- wp:navigation-submenu {"label":"About","type":"page","id":2,"kind":"post-type"} -->'
        '<!-- wp:navigation-link {"label":"Team","type":"page","id":3,"kind":"post-type"} /-->'
        "<!-- /wp:navigation-submenu -->"
        '<!-- wp:search {"label":"Search"} /-->'
    )
    nodes = nav.navigation_nodes(content)
    assert [r.spoken() for r in nav.rows(nodes)][:2] == [
        "About, page, level 1, 1 of 2",
        "Team, page, level 2, 1 of 1",
    ]
    out = nav.serialize_navigation(nodes)
    assert out.startswith("<!-- wp:navigation-submenu ")
    assert '<!-- wp:search {"label":"Search"} /-->' in out
    nav.move_out(nodes, nodes[0].children[0])
    out = nav.serialize_navigation(nodes)
    assert "navigation-submenu" not in out
    assert out.count("<!-- wp:navigation-link ") == 2


def test_classic_positions_number_in_reading_order() -> None:
    nodes = _nodes()
    for i, n in enumerate(nav.rows(nodes), start=10):
        n.node.item_id = i
    assert [(n.title, p, o) for n, p, o in nav.classic_positions(nodes)] == [
        ("Home", 0, 1),
        ("About", 0, 2),
        ("Team", 11, 3),
        ("Donate", 0, 4),
    ]


def test_menu_problems() -> None:
    menu = nav.Menu(
        1, "Main", "classic", nodes=[nav.MenuNode("", "page", 5), nav.MenuNode("Gone", "post", 6)]
    )
    assert nav.problems(menu, {5: "publish"}) == [
        "An item at level 1 has no name.",
        "Gone points to a post that is gone: a dead link.",
    ]
    assert menu.spoken() == "Main, menu, 2 items"


def test_threads_keep_orphans_visible() -> None:
    rows = cm.threaded([
        cm.Comment(1, 5, 0, "Ann", "2026-11-01T10:00:00", "hold", "<p>first</p>"),
        cm.Comment(2, 5, 99, "Bob", "2026-11-02T10:00:00", "hold", "orphan"),
        cm.Comment(3, 5, 1, "Cy", "2026-11-03T10:00:00", "hold", "reply"),
    ])
    assert [(d, c.id) for d, c in rows] == [(0, 2), (0, 1), (1, 3)]
    assert cm.waiting_sentence("Radio", 1) == "Radio: 1 comment waiting."


def test_cannot_sentence_uses_the_right_article() -> None:
    admin = Account(1, "A", "a", ("administrator",), frozenset({"manage_options"}))
    editor = Account(2, "E", "e", ("editor",), frozenset())
    assert sa.can(admin, "site_check")
    assert sa.cannot_sentence("Radio", editor, "users") == (
        "Your account on Radio is an Editor, which cannot manage users."
    )
    contributor = Account(3, "C", "c", ("contributor",), frozenset())
    assert sa.cannot_sentence("Radio", contributor, "plugins").startswith(
        "Your account on Radio is a Contributor"
    )


def test_settings_values_in_words() -> None:
    assert sa.settings_value_text("start_of_week", 1, {}) == "Monday"
    assert sa.settings_value_text("page_for_posts", 0, {}) == "none"
    assert sa.settings_value_text("page_for_posts", 7, {}) == "page 7"
    assert sa.settings_value_text("title", "", {}) == "(empty)"
    assert sa.settings_value_text("site_icon", 9, {}) == "picture 9"


def test_check_text_counts() -> None:
    text = sa.check_text("Radio", [sa.CheckLine("good", "Fine."), sa.CheckLine("critical", "Bad.")])
    assert text.startswith("Site Check for Radio: 1 critical, 0 recommended.")


def test_font_words_and_unused_terms() -> None:
    assert lib.describe_font("'Fira Code', monospace") == "monospace, suits code"
    assert lib.describe_font("Pacifico", ("handwriting",)).startswith("handwriting")
    assert lib.describe_font("Oswald", ("display",)) == "display, suits headings"
    assert lib.describe_font("Mystery") == "style not stated"
    terms = [Term(1, "category", "A", "a", 0), Term(2, "category", "B", "b", 3)]
    assert lib.unused(terms, keep=1) == []
    assert lib.bulk_fields("page")[-1] == ("parent", "Parent page")


def test_page_tree_and_outline() -> None:
    flat = [
        ss.PageNode(1, "A", 0, 0, "publish"),
        ss.PageNode(2, "B", 1, 0, "publish", loaded_parent=1),
        ss.PageNode(3, "C", 0, 1, "publish", loaded_order=1),
    ]
    tree = ss.build_tree(flat)
    assert ss.page_move(tree, tree[0], "up") == ""
    assert ss.page_move(tree, tree[0].children[0], "out") == "B moved out, after A."
    assert [(n.id, p, o) for n, p, o in ss.page_order_changes(tree)] == [(2, 0, 1), (3, 0, 2)]
    assert ss.template_outline([]) == ""
