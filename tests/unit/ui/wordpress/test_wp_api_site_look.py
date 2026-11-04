"""Style Variations, Site Styles, the Pattern Directory and pattern categories (9.15)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.core.wordpress import site_styles as ss
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui.wordpress_look_commands import WordPressLookCommands
from quill.ui.wordpress_pattern_commands import WordPressPatternCommands

API = "/wp-json/wp/v2"
MIXINS = (WordPressLookCommands, WordPressPatternCommands)

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "roles": ["administrator"],
    "capabilities": {"edit_theme_options": True, "edit_posts": True, "manage_options": True},
}
AUTHOR = {"id": 9, "name": "Ann", "roles": ["author"], "capabilities": {"edit_posts": True}}

ROUTES = {
    # The route as WordPress lists it, with its regular expression.
    "/wp/v2/global-styles/themes/(?P<stylesheet>[\\/\\s%\\w\\.\\(\\)\\[\\]\\@_\\-]+)"
    "/variations": {},
    "/wp/v2/global-styles/(?P<id>[\\/\\w-]+)": {},
    "/wp/v2/pattern-directory/patterns": {},
}


@pytest.fixture
def site(wp: Any) -> Any:
    """The shared commands with this area's mixins, until the coordinator wires them."""
    extra = tuple(m for m in MIXINS if not issubclass(type(wp), m))
    if extra:
        wp.__class__ = type("Wired", (type(wp), *extra), {})
    return wp


def _index(wp_site: Any, routes: dict[str, Any] | None = None, account: Any = ADMIN) -> None:
    wp_site.on(
        "GET",
        "/wp-json/",
        {"namespaces": ["wp/v2"], "routes": ROUTES if routes is None else routes},
    )
    wp_site.on("GET", f"{API}/users/me", account)


def _theme(wp_site: Any, styles_id: int = 7) -> None:
    links = {
        "wp:user-global-styles": [
            {"href": f"https://radio.example/wp-json/wp/v2/global-styles/{styles_id}"}
        ]
    }
    wp_site.on(
        "GET",
        f"{API}/themes",
        [
            {
                "name": {"raw": "Twenty Twenty-Five"},
                "stylesheet": "tt5",
                "is_block_theme": True,
                "_links": links,
            }
        ],
    )


BASE = {
    "settings": {
        "color": {
            "palette": [
                {"slug": "base", "name": "Base", "color": "#ffffff"},
                {"slug": "contrast", "name": "Contrast", "color": "#111111"},
                {"slug": "accent", "name": "Accent", "color": "#ffee88"},
            ]
        },
        "typography": {"fontSizes": [{"slug": "small", "name": "Small", "size": "0.875rem"}]},
    },
    "styles": {
        "color": {"background": "var:preset|color|base", "text": "var:preset|color|contrast"}
    },
}


# --------------------------------------------------------------------------- #
# Style Variations


def test_variations_are_refused_in_a_sentence_when_the_site_has_none(site, wp_site, wp_dialogs):
    _index(wp_site, routes={})
    site.cmd_style_variations()
    assert "has no style variations to offer" in wp_site_said(site)
    assert not wp_dialogs.list_windows


def test_variations_need_a_role_that_can_change_the_look(site, wp_site, wp_dialogs):
    _index(wp_site, account=AUTHOR)
    site.cmd_style_variations()
    assert "is an Author, which cannot change the site's look" in wp_site_said(site)


def test_a_classic_theme_is_said_plainly(site, wp_site, wp_dialogs):
    _index(wp_site)
    wp_site.on(
        "GET",
        f"{API}/themes",
        [{"name": "Classic", "stylesheet": "classic", "is_block_theme": False}],
    )
    site.cmd_style_variations()
    assert "is not a block theme" in wp_site_said(site)


def test_a_theme_with_no_variations_says_so(site, wp_site, wp_dialogs):
    _index(wp_site)
    _theme(wp_site)
    wp_site.on("GET", f"{API}/global-styles/themes/tt5/variations", [])
    wp_site.on("GET", f"{API}/global-styles/themes/tt5", BASE)
    site.cmd_style_variations()
    assert "has no style variations" in wp_site_said(site)


def _variations(wp_site: Any) -> None:
    _index(wp_site)
    _theme(wp_site)
    wp_site.on("GET", f"{API}/global-styles/themes/tt5", BASE)
    wp_site.on(
        "GET",
        f"{API}/global-styles/themes/tt5/variations",
        [
            {
                "title": "Evening",
                "settings": {
                    "color": {
                        "palette": [
                            {"slug": "base", "name": "Base", "color": "#000000"},
                            {"slug": "contrast", "name": "Contrast", "color": "#ffffff"},
                        ]
                    }
                },
                "styles": {},
            },
            {"title": "Fonts only", "settings": {}, "styles": {}},
        ],
    )


def test_each_variation_is_listed_with_its_palette_report(site, wp_site, wp_dialogs):
    _variations(wp_site)
    site.cmd_style_variations()
    window = wp_dialogs.window
    assert window["rows"][0].startswith("Evening: 2 pairings, 0 below")
    assert window["rows"][1].startswith("Fonts only: 6 pairings")
    assert "Accent" in window["details"](1)
    assert "to 1" in window["details"](0)


def test_applying_a_variation_keeps_the_old_look_and_put_back_restores_it(
    site, wp_site, wp_dialogs
):
    _variations(wp_site)
    old = {"title": "Custom", "settings": {"color": {"palette": {"theme": []}}}, "styles": {"x": 1}}
    wp_site.on("GET", f"{API}/global-styles/7", old)
    wp_site.on("POST", f"{API}/global-styles/7", {"id": 7})
    wp_dialogs.answer("confirm", True, True)
    site.cmd_style_variations()
    wp_dialogs.press("&Apply...", 0)
    sent = wp_site.body(wp_site.sent("POST", f"{API}/global-styles/7")[0])
    assert sent["title"] == "Evening"
    assert sent["settings"]["color"]["palette"][0]["color"] == "#000000"
    assert "Evening applied on Community Radio" in wp_site_said(site)
    assert (
        "Change the look of Community Radio to Evening" in wp_dialogs.asked("confirm")[0]["message"]
    )
    wp_dialogs.press("Put &Back the Previous Look...")
    back = wp_site.body(wp_site.sent("POST", f"{API}/global-styles/7")[1])
    assert back == {"settings": old["settings"], "styles": {"x": 1}, "title": "Custom"}
    assert "The previous look is back on Community Radio." in wp_site_said(site)


def test_declining_the_variation_sends_nothing(site, wp_site, wp_dialogs):
    _variations(wp_site)
    site.cmd_style_variations()
    wp_dialogs.press("&Apply...", 0)
    assert not wp_site.sent("POST", f"{API}/global-styles/7")


def test_put_back_with_nothing_kept_says_so(site, wp_site, wp_dialogs):
    _variations(wp_site)
    site.cmd_style_variations()
    wp_dialogs.press("Put &Back the Previous Look...")
    assert "QUILL has no earlier look kept for Community Radio." in wp_site_said(site)


# --------------------------------------------------------------------------- #
# Site Styles


def _styles(wp_site: Any, user: Any = None) -> None:
    _index(wp_site)
    _theme(wp_site)
    wp_site.on("GET", f"{API}/global-styles/themes/tt5", BASE)
    wp_site.on("GET", f"{API}/global-styles/7", user or {"settings": {}, "styles": {}})
    wp_site.on("POST", f"{API}/global-styles/7", {"id": 7})


def test_site_styles_list_colours_with_their_contrast_then_sizes(site, wp_site, wp_dialogs):
    _styles(wp_site)
    site.cmd_site_styles()
    rows = wp_dialogs.window["rows"]
    assert rows[0].startswith("Colour: Base")
    assert "the page background" in rows[0]
    assert "on the page background, passes" in rows[1]
    assert "too faint for text" in rows[2]
    assert rows[3] == "Font size: Small, 0.875rem"


def test_changing_a_colour_says_its_contrast_before_saving_only_settings(site, wp_site, wp_dialogs):
    _styles(wp_site)
    wp_dialogs.answer("ask_text", "#1a4d2e").answer("confirm", True)
    site.cmd_site_styles()
    rows = wp_dialogs.press("&Change...", 2)
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "Change Accent on Community Radio from #ffee88 to #1a4d2e?" in message
    assert "on the page background, passes" in message
    body = wp_site.body(wp_site.sent("POST", f"{API}/global-styles/7")[0])
    assert set(body) == {"settings"}
    palette = body["settings"]["color"]["palette"]["theme"]
    assert [c["color"] for c in palette] == ["#ffffff", "#111111", "#1a4d2e"]
    assert "Accent changed on Community Radio." in wp_site_said(site)
    assert "passes" in rows[2]
    assert ss.previous(site.local.root, "radio") is not None


def test_a_colour_qiull_cannot_read_is_refused_with_the_shape_it_takes(site, wp_site, wp_dialogs):
    _styles(wp_site)
    wp_dialogs.answer("ask_text", "greenish")
    site.cmd_site_styles()
    wp_dialogs.press("&Change...", 2)
    assert "Type it as a hex code" in wp_site_said(site)
    assert not wp_site.sent("POST", f"{API}/global-styles/7")


def test_changing_a_font_size_drops_its_old_fluid_range(site, wp_site, wp_dialogs):
    user = {
        "settings": {
            "typography": {
                "fontSizes": {
                    "theme": [
                        {
                            "slug": "small",
                            "name": "Small",
                            "size": "0.875rem",
                            "fluid": {"min": "1px"},
                        }
                    ]
                }
            }
        },
        "styles": {},
    }
    _styles(wp_site, user)
    wp_dialogs.answer("ask_text", "1rem").answer("confirm", True)
    site.cmd_site_styles()
    wp_dialogs.press("&Change...", 3)
    body = wp_site.body(wp_site.sent("POST", f"{API}/global-styles/7")[0])
    assert body["settings"]["typography"]["fontSizes"]["theme"] == [
        {"slug": "small", "name": "Small", "size": "1rem"}
    ]
    assert "Change the Small font size" in wp_dialogs.asked("confirm")[0]["message"]


def test_a_bad_font_size_is_refused(site, wp_site, wp_dialogs):
    _styles(wp_site)
    wp_dialogs.answer("ask_text", "big")
    site.cmd_site_styles()
    wp_dialogs.press("&Change...", 3)
    assert "as a font size" in wp_site_said(site)


def test_site_styles_without_the_route_are_refused(site, wp_site, wp_dialogs):
    _index(wp_site, routes={})
    site.cmd_site_styles()
    assert "does not offer its site styles" in wp_site_said(site)


def test_a_theme_with_no_colours_or_sizes_says_so(site, wp_site, wp_dialogs):
    _index(wp_site)
    _theme(wp_site)
    wp_site.on("GET", f"{API}/global-styles/themes/tt5", {"settings": {}})
    wp_site.on("GET", f"{API}/global-styles/7", {"settings": {}})
    site.cmd_site_styles()
    assert "sets no colours or font sizes" in wp_site_said(site)


def test_site_styles_on_a_theme_without_a_styles_record(site, wp_site, wp_dialogs):
    _index(wp_site)
    wp_site.on("GET", f"{API}/themes", [{"name": "Classic", "stylesheet": "classic"}])
    site.cmd_site_styles()
    assert "is not a block theme" in wp_site_said(site)


# --------------------------------------------------------------------------- #
# The Pattern Directory, from Insert Block

HERO = (
    '<!-- wp:cover --><div><img src="https://s.w.org/a.jpg" alt=""/>'
    "<!-- wp:heading --><h2>Hi</h2><!-- /wp:heading -->"
    "<!-- wp:paragraph --><p>a</p><!-- /wp:paragraph -->"
    "<!-- wp:paragraph --><p>b</p><!-- /wp:paragraph --></div><!-- /wp:cover -->"
)


def _page(site: Any) -> None:
    copy = lc.WorkingCopy(
        site_id="radio", kind="page", local_id=lc.new_local_id(), title="Home", text="Hello\n"
    )
    site.host.open_path(site.local.write_document(copy))


def test_insert_block_offers_the_directory_only_where_the_site_has_it(site, wp_site, wp_dialogs):
    _page(site)
    _index(wp_site, routes={})
    site.cmd_insert_block()
    assert [a.label for a in wp_dialogs.window["actions"]] == ["&Insert"]


def test_insert_block_still_opens_when_the_index_is_refused(site, wp_site, wp_dialogs):
    _page(site)
    site.cmd_insert_block()
    assert [a.label for a in wp_dialogs.window["actions"]] == ["&Insert"]


def test_a_directory_pattern_is_described_then_inserted(site, wp_site, wp_dialogs):
    _page(site)
    _index(wp_site)
    wp_site.on(
        "GET",
        f"{API}/pattern-directory/patterns",
        [{"id": 5, "title": "Hero", "description": "A big welcome", "content": HERO}],
    )
    wp_dialogs.answer("ask_text", "hero").answer("ask_choice", 0).answer("confirm", True)
    site.cmd_insert_block()
    assert wp_dialogs.press("&WordPress.org Patterns...") is not None
    query = wp_site.sent("GET", f"{API}/pattern-directory/patterns")[0].full_url
    assert "search=hero" in query
    assert wp_dialogs.asked("ask_choice")[0]["rows"] == ["Hero: A big welcome"]
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "Blocks, in order: Cover, Heading, Paragraph (2)." in message
    assert "1 with no alternative text" in message
    assert "::: block core/cover" in site.host.text
    assert "Hero inserted." in wp_site_said(site)


def test_a_directory_search_that_finds_nothing_says_so(site, wp_site, wp_dialogs):
    _page(site)
    _index(wp_site)
    wp_site.on("GET", f"{API}/pattern-directory/patterns", [])
    wp_dialogs.answer("ask_text", "zebra")
    site.cmd_insert_block()
    wp_dialogs.press("&WordPress.org Patterns...")
    assert "No WordPress.org patterns match zebra." in wp_site_said(site)


def test_declining_a_directory_pattern_inserts_nothing(site, wp_site, wp_dialogs):
    _page(site)
    _index(wp_site)
    wp_site.on(
        "GET", f"{API}/pattern-directory/patterns", [{"id": 5, "title": "Hero", "content": HERO}]
    )
    wp_dialogs.answer("ask_text", "hero").answer("ask_choice", 0)
    site.cmd_insert_block()
    wp_dialogs.press("&WordPress.org Patterns...")
    assert site.host.text == "Hello\n"


# --------------------------------------------------------------------------- #
# Pattern categories in Synced Patterns


def _patterns(wp_site: Any, with_categories: bool = True) -> None:
    wp_site.on("GET", f"{API}/users/me", ADMIN)

    def blocks(_request: Any, query: dict[str, list[str]]) -> Any:
        if "wp_pattern_category" in query.get("_fields", [""])[0]:
            return [{"id": 1, "wp_pattern_category": [3]}, {"id": 2, "wp_pattern_category": []}]
        return [
            {"id": 1, "title": {"raw": "Header"}, "content": {"raw": "x"}},
            {"id": 2, "title": {"raw": "Footer"}, "content": {"raw": "y"}},
        ]

    wp_site.on("GET", f"{API}/blocks", blocks)
    wp_site.on("GET", f"{API}/pages", [])
    wp_site.on("GET", f"{API}/posts", [])
    if with_categories:
        wp_site.on("GET", f"{API}/wp_pattern_category", [{"id": 3, "name": "Headers"}])


def test_synced_patterns_ask_which_category_and_show_only_those(site, wp_site, wp_dialogs):
    _patterns(wp_site)
    wp_dialogs.answer("ask_choice", 1)
    site.cmd_synced_patterns()
    assert wp_dialogs.asked("ask_choice")[0]["rows"] == [
        "All patterns, 2 patterns",
        "Headers, 1 pattern",
        "No category, 1 pattern",
    ]
    assert [r.split(",")[0] for r in wp_dialogs.window["rows"]] == ["Header"]


def test_cancelling_the_category_opens_nothing(site, wp_site, wp_dialogs):
    _patterns(wp_site)
    site.cmd_synced_patterns()
    assert not wp_dialogs.list_windows


def test_a_site_without_pattern_categories_opens_synced_patterns_directly(
    site, wp_site, wp_dialogs
):
    _patterns(wp_site, with_categories=False)
    site.cmd_synced_patterns()
    assert not wp_dialogs.asked("ask_choice")
    assert len(wp_dialogs.window["rows"]) == 2


def wp_site_said(site: Any) -> str:
    return site.host.said


# Keep the block form unscripted in this file: the directory inserts a pattern,
# which needs no form.
@pytest.fixture(autouse=True)
def _no_block_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bdlg, "ask_fields", lambda *a, **k: None)
