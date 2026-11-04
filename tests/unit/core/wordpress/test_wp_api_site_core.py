"""The wx-free 9.15 core: site styles, the directory, plugins, abilities, health tests."""

from __future__ import annotations

import pytest

from quill.core.wordpress import abilities as ab
from quill.core.wordpress import pattern_directory as pd
from quill.core.wordpress import plugin_events as ev
from quill.core.wordpress import plugin_shop_seo as shop
from quill.core.wordpress import site_health as sh
from quill.core.wordpress import site_styles as ss

# --------------------------------------------------------------------------- #
# site styles


def test_entries_prefer_the_sites_own_palette_over_the_themes() -> None:
    base = {"settings": {"color": {"palette": [{"slug": "a", "name": "A", "color": "#000"}]}}}
    user = {
        "settings": {"color": {"palette": {"theme": [{"slug": "a", "name": "A", "color": "#fff"}]}}}
    }
    assert ss.entries(base, user) == [ss.StyleEntry("colour", "a", "A", "#fff")]
    assert ss.entries(base, {}) == [ss.StyleEntry("colour", "a", "A", "#000")]


def test_page_colours_resolve_palette_references_and_fall_back() -> None:
    base = {
        "settings": {"color": {"palette": [{"slug": "base", "name": "Base", "color": "#222222"}]}},
        "styles": {"color": {"background": "var(--wp--preset--color--base)", "text": "nonsense"}},
    }
    assert ss.page_colours(base, {}) == ("#222222", "#000000")


@pytest.mark.parametrize("value", ["1rem", "18px", "1.125em", "clamp(1rem, 2vw, 2rem)"])
def test_font_sizes_quill_reads(value: str) -> None:
    assert ss.check_size(value) == value


def test_a_colour_that_is_not_one_says_the_shape() -> None:
    with pytest.raises(ss.StyleValueError, match="hex code"):
        ss.check_colour("blue-ish")


def test_contrast_sentence_for_a_colour_quill_cannot_read() -> None:
    assert ss.contrast_sentence("Odd", "var(--x)", "#fff", "#000").endswith("cannot read")


def test_report_summary_with_nothing_readable() -> None:
    assert ss.report_summary([]) == "no colours QUILL can read"


# --------------------------------------------------------------------------- #
# the directory


def test_block_list_counts_runs_and_pictures_count_missing_alt() -> None:
    content = (
        "<!-- wp:group --><!-- wp:image --><img src=a alt='A dog'><!-- /wp:image -->"
        "<!-- wp:image --><img src=b><!-- /wp:image --><!-- /wp:group -->"
    )
    assert pd.block_list(content) == ["Group", "Image (2)"]
    assert pd.pictures_without_alt(content) == (2, 1)


def test_describe_a_pattern_with_described_pictures() -> None:
    pattern = pd.DirectoryPattern(1, "Gallery", "", "<img alt='x'>")
    assert pd.describe(pattern).endswith("It brings 1 picture, each with alternative text.")


def test_categories_offer_nothing_when_no_pattern_is_in_one() -> None:
    cats = pd.PatternCategories(((3, "Headers"),), {})
    assert cats.choices([1, 2]) == [("All patterns, 2 patterns", [1, 2])]


# --------------------------------------------------------------------------- #
# events


def test_spoken_spans() -> None:
    assert ev.spoken_span("2026-11-21 00:00:00", "2026-11-21 23:59:59", all_day=True) == (
        "Saturday 21 November 2026, all day"
    )
    assert ev.spoken_span("2026-11-21 10:00:00", "2026-11-22 16:00:00") == (
        "from Saturday 21 November 2026 at 10:00 to Sunday 22 November 2026 at 16:00"
    )
    assert ev.spoken_span("", "") == "no date set"
    assert ev.spoken_moment("soon") == "soon"


def test_parse_when_takes_a_date_alone_and_refuses_a_false_one() -> None:
    assert ev.parse_when("2026-11-21") == "2026-11-21 00:00:00"
    assert ev.parse_when("2026-11-21T9:05") == "2026-11-21 09:05:00"
    with pytest.raises(ev.EventDateError, match="not a real date"):
        ev.parse_when("2026-02-30 10:00")


# --------------------------------------------------------------------------- #
# shop and SEO


def test_stock_words_and_length_notes() -> None:
    product = shop.product_from({"stock_status": "outofstock"})
    assert product.stock_words() == "out of stock"
    assert shop.length_note("SEO title", "abc", 60) == "SEO title: 3 characters of about 60"
    assert shop.seo_fields(None) == []


def test_negative_stock_is_refused() -> None:
    with pytest.raises(shop.ShopValueError, match="below nought"):
        shop.check_quantity("-1")


def test_an_order_with_no_items_or_customer() -> None:
    order = shop.order_from({"id": 7, "status": "on-hold"})
    assert order.spoken().startswith("Order 7, on hold, 0 items")
    assert "from a guest" in order.spoken()
    assert order.details() == "No items."


# --------------------------------------------------------------------------- #
# abilities


def _ability(**kw: object) -> ab.Ability:
    return ab.Ability(**{"name": "x/y", "label": "Y", "description": "", **kw})  # type: ignore[arg-type]


def test_parse_plan_refuses_bad_json_and_non_objects() -> None:
    known = [_ability()]
    assert ab.parse_plan("RUN x/y {nope}", known) is None
    assert ab.parse_plan("RUN x/y {}", known) == (known[0], {})
    assert ab.parse_plan("Here is the answer.", known) is None


def test_destructive_abilities_say_so() -> None:
    risky = _ability(destructive=True)
    assert "can delete or overwrite" in risky.spoken(False)
    assert "delete or overwrite things" in ab.approval_message("Site", risky, {"id": 1})


def test_long_results_are_cut_short() -> None:
    assert ab.result_text("a" * (ab.RESULT_LIMIT + 5)).endswith("(cut short)")


def test_an_entry_without_a_name_is_no_ability() -> None:
    assert ab.ability_from({"label": "No name"}) is None


# --------------------------------------------------------------------------- #
# health tests


def test_an_index_without_routes_runs_the_five_known_tests() -> None:
    assert sh.health_test_names({"namespaces": ["wp-site-health/v1"]}) == list(sh.FALLBACK_TESTS)


def test_a_passing_header_test_needs_no_explanation_and_unknown_status_is_a_note() -> None:
    lines = sh.health_test_lines("authorization-header", {"status": "good"})
    assert [(line.status, line.text) for line in lines] == [("good", "The authorization header.")]
    odd = sh.health_test_lines("new-test", {"status": "weird"})
    assert (odd[0].status, odd[0].text) == ("info", "New test.")
