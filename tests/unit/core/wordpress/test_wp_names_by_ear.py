"""Review item 28: what the WordPress Workbench says is a name, not a stored code."""

from __future__ import annotations

import pytest

from quill.core.counted import a_or_an
from quill.core.wordpress.gravity_build_save import change_lines
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import sheet_for, values_for
from quill.core.workbench.properties import FieldKind, as_text, say_value


@pytest.mark.parametrize(
    ("word", "said"),
    [
        ("event", "an event"),
        ("page", "a page"),
        ("hour", "an hour"),
        ("user", "a user"),
        ("URL", "a URL"),
        ("SEO title", "an SEO title"),
        ("image/png", "an image/png"),
    ],
)
def test_the_article_agrees_with_the_word(word: str, said: str) -> None:
    assert a_or_an(word) == said


def test_a_row_with_only_a_number_is_named_by_its_kind() -> None:
    assert WbRow("comment", "Site", "12", {}, "").title == "Comment 12"
    assert WbRow("sidebar", "Site", "sidebar-1", {"sidebar": "Footer"}, "").title == "Footer"
    assert WbRow("menu", "Site", "4", {"menu": "Main"}, "").title == "Main"


def test_a_list_value_is_said_with_commas_not_as_a_tuple() -> None:
    assert say_value(("News",)) == "News"
    assert say_value(("News", "Events")) == "News, Events"


def test_the_week_starts_on_a_day_not_a_number() -> None:
    row = WbRow(
        "setting",
        "Site",
        "start_of_week",
        {"setting": "First day of the week", "value": "Monday"},
        "",
        raw={"key": "start_of_week", "value": 1},
    )
    sheet = sheet_for(row)
    spec = sheet.field("value")
    assert spec.kind is FieldKind.CHOICE
    assert spec.word_for(1) == "Monday"
    assert spec.value_for("Saturday") == "6"
    assert "Value: Monday" in as_text(sheet, values_for(row))


def test_an_item_status_is_said_as_wordpress_says_it() -> None:
    row = WbRow("item", "Site", "5", {"title": "Hello"}, "", subkind="posts")
    spec = sheet_for(row).field("status")
    assert spec.word_for("publish") == "Published"
    assert spec.word_for("future") == "Scheduled"
    assert spec.value_for("Draft") == "draft"


def test_label_placement_changes_are_said_in_words() -> None:
    before = {"title": "Signup", "labelPlacement": "top_label", "fields": []}
    after = {**before, "labelPlacement": "left_label"}
    assert "Label placement: Left aligned (was Top aligned)." in change_lines(before, after)
