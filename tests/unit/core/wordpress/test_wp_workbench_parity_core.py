"""wp-admin parity for Posts, Pages and Media, the wx-free half (wordpress.md 9.18, 1 to 3)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import workbench_parity as wpp
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_edit import EditRefused
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import sheet_for


class _Answer:
    def __init__(self, total: int | None, payload: Any = None) -> None:
        self.total = total
        self.payload = payload or []


class CountingApi:
    def __init__(self) -> None:
        self.asked: list[dict[str, Any]] = []

    def request(self, method: str, route: str, **kw: Any) -> _Answer:
        params = dict(kw.get("params") or {})
        self.asked.append({"route": route, **params})
        if params.get("status") == "private":
            raise WordPressApiError("Sorry, you are not allowed.", status=403)
        if params.get("author") == 3:
            return _Answer(2)
        return _Answer(
            {"any": 12, "publish": 8, "draft": 3, "trash": 1}.get(params.get("status"), 0)
        )


def test_counts_follow_wp_admins_views_and_leave_out_a_refused_one() -> None:
    api = CountingApi()
    counts = wpp.status_counts(api, "wp/v2/posts", 3, wpp.ITEM_VIEWS)  # type: ignore[arg-type]
    labels = [label for label, _n in counts]
    assert labels == ["All", "Mine", "Published", "Drafts", "Pending", "Scheduled", "Trash"]
    assert dict(counts)["Mine"] == 2 and dict(counts)["All"] == 12
    assert all(a["per_page"] == 1 for a in api.asked)
    said = wpp.counts_text("Posts", "Radio", counts)
    assert said.startswith("Posts on Radio: All 12, Mine 2, Published 8, Drafts 3")
    assert "Private" not in said


def test_mine_is_skipped_when_the_site_has_not_said_who_you_are() -> None:
    counts = wpp.status_counts(CountingApi(), "wp/v2/media", 0, wpp.MEDIA_VIEWS)  # type: ignore[arg-type]
    assert "Mine" not in dict(counts)
    assert (
        wpp.counts_text("Media", "Radio", []) == "Radio would not count its media for this account."
    )


def _row(key: str, title: str) -> WbRow:
    return WbRow("item", "Radio", key, {"title": title}, "", route=f"wp/v2/posts/{key}")


def test_each_gives_every_row_its_own_outcome() -> None:
    def act(row: WbRow) -> None:
        if row.key == "2":
            raise WordPressApiError("Sorry, you are not allowed to delete this post.", status=403)
        if row.key == "3":
            raise EditRefused("WordPress keeps no Trash for this.")

    rows = [_row("1", "Hello"), _row("2", "News"), _row("3", "Logo"), _row("4", "Bye")]
    results = wpp.each(rows, act, "moved")
    assert [r.ok for r in results] == [True, False, False, True]
    said = wpp.outcome(results, "Moved {n} to the Trash", "Radio")
    assert said.startswith("Moved 2 of 4 items to the Trash on Radio. Not done: News: Sorry")
    assert "Logo: WordPress keeps no Trash" in said
    every = wpp.outcome(wpp.each(rows[:1], lambda _r: None, "moved"), "Moved {n}", "Radio")
    assert every == "Moved 1 item on Radio."


def test_crop_by_numbers_is_checked_and_read_back_in_words() -> None:
    box = wpp.parse_crop("10, 0, 80 100")
    assert box == {"left": 10.0, "top": 0.0, "width": 80.0, "height": 100.0}
    words = wpp.crop_words(box)
    assert "keeps 80 percent of the width, starting 10 percent from the left" in words
    for bad in ("10, 0, 80", "30, 0, 80, 100", "0, 0, 0, 100", "-1, 0, 50, 50"):
        with pytest.raises(EditRefused):
            wpp.parse_crop(bad)


def test_picture_choices_offer_only_what_the_site_takes() -> None:
    rows = wpp.picture_choices(("rotate",), 800, 600)
    assert rows and all(m[0]["type"] == "rotate" for _label, m in rows)
    crops = [label for label, _m in wpp.picture_choices(("crop",), 0, 0)]
    assert crops == []  # a crop to a shape needs the picture's size


class _ChoiceApi:
    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users":
            assert params["who"] == "authors"
            return [{"id": 3, "name": "Jeff"}, {"id": 4, "name": "Ann"}]
        if route == "wp/v2/templates":
            return [{"slug": "page-wide"}]
        return []

    def request(self, method: str, route: str, **kw: Any) -> Any:
        raise WordPressApiError("No OPTIONS here.", status=405)


def test_author_and_template_become_choices_and_default_is_said_in_words() -> None:
    api = _ChoiceApi()
    authors = wpp.author_choices(api)  # type: ignore[arg-type]
    templates = wpp.template_choices(api, "page")  # type: ignore[arg-type]
    assert authors == ("Jeff (3)", "Ann (4)") and templates == ("page-wide",)
    row = WbRow("item", "Radio", "5", {"title": "About"}, "", subkind="page", raw={"parent": 0})
    sheet = sheet_for(row)
    values: dict[str, Any] = {"author": "Jeff (3)", "template": ""}
    chosen = wpp.with_choices(sheet, values, authors=authors, templates=templates)
    assert chosen.field("author").choices == authors
    assert chosen.field("template").choices == (wpp.DEFAULT_TEMPLATE, "page-wide")
    assert values["template"] == wpp.DEFAULT_TEMPLATE
    assert wpp.clean_body({"template": wpp.DEFAULT_TEMPLATE}) == {"template": ""}
    empty: dict[str, Any] = {"author": ""}
    kept = wpp.with_choices(sheet, empty, authors=authors)
    assert not kept.field("author").choices  # never silently the first name in the list


def test_what_rest_cannot_do_opens_the_exact_wp_admin_screen() -> None:
    media = WbRow("media", "Radio", "9", {"title": "Sky"}, "")
    link, why = wpp.dashboard_screen("https://radio.example/", media)
    assert link == "https://radio.example/wp-admin/post.php?post=9&action=edit"
    assert "scales the original" in why
    fact = WbRow("fact", "Radio", "x", {}, "")
    assert wpp.dashboard_screen("https://radio.example", fact) == ("", "")


def test_every_new_command_has_help_a_written_reason_and_comes_before_properties() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command
    from quill.core.wordpress.workbench_parity_actions import (
        ITEM_ROWS,
        KEYLESS,
        MEDIA_ROWS,
        NODE_ROWS,
    )

    for kind, rows in (("item", ITEM_ROWS), ("media", MEDIA_ROWS), ("node", NODE_ROWS)):
        offered = WORDPRESS_ACTIONS.rows_for(kind)
        assert offered[-1].command_id == command("sheet")
        for row in rows:
            assert row in offered, row.command_id
            assert row.help and KEYLESS.get(row.command_id), row.command_id
            assert not row.default
