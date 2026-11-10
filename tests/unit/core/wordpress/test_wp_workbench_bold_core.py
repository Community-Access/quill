"""W7 in the core: copy, compare, snapshot, calendar, reading, lists, console, watches, practice."""

from __future__ import annotations

import json
from typing import Any

import pytest

from quill.core.wordpress.workbench_bold import (
    calendar_days,
    compare_sites,
    day_words,
    plan_copy,
    rewrite_links,
    run_copy,
    site_document,
    take_snapshot,
)
from quill.core.wordpress.workbench_io import (
    answer_tree,
    complete_route,
    export_rows,
    import_plan,
    needed_capability,
    parse_params,
    read_spreadsheet,
    send_import,
)
from quill.core.wordpress.workbench_practice import (
    PracticeTools,
    blueprint,
    missing_words,
    read_password,
    start_command,
)
from quill.core.wordpress.workbench_watches import WatchState, check, due


class _Address:
    wpcom_site = ""

    def __init__(self, url: str) -> None:
        self.site_url = url


class Site:
    """A small fake site: posts by slug, terms, and every write recorded."""

    def __init__(self, url: str, posts: list[dict[str, Any]] | None = None) -> None:
        self.address = _Address(url)
        self.site_name = url
        self.posts = posts or []
        self.writes: list[tuple[str, str, Any]] = []
        self.comments: list[int] = []

    def get(self, route: str, **params: Any) -> Any:
        if route in ("wp/v2/posts", "wp/v2/pages") and "slug" in params:
            return [p for p in self.posts if p.get("slug") == params["slug"]]
        if route in ("wp/v2/categories", "wp/v2/tags"):
            return []
        if route == "wp/v2/settings":
            return {"title": "T"}
        return []

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append(("POST", route, body))
        return {"id": 50, **(body or {})}

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        params = dict(params or {})
        if route == "wp/v2/posts":
            for post in self.posts:
                if params.get("status") in (None, "any", post.get("status")):
                    yield post
        if route == "wp/v2/comments" and params.get("status") == "hold":
            for ident in self.comments:
                yield {"id": ident}


def _post(slug: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": len(slug),
        "slug": slug,
        "type": "post",
        "status": "publish",
        "title": {"raw": slug.title()},
        "content": {"raw": f'<a href="https://a.example/x">x</a> {slug}'},
        **extra,
    }


def test_copy_to_site_plans_creates_and_replaces_then_rewrites_links() -> None:
    target = Site("https://b.example", [_post("about")])
    rows = [("item", "post", _post("about")), ("item", "post", _post("news")), ("font", "", {})]
    plan = plan_copy(target, rows, source_site="A", target_site="B", source_url="https://a.example")
    assert [line.action for line in plan.lines] == ["replace", "create", "skip"]
    assert "1 made, 1 replaced, 1 skipped" in plan.summary
    failed = run_copy(
        Site("https://a.example"),
        target,
        plan,
        source_url="https://a.example",
        target_url="https://b.example",
    )
    assert failed == []
    sent = [w for w in target.writes if w[1].startswith("wp/v2/posts")]
    assert sent[0][1] == "wp/v2/posts/5" and "https://b.example/x" in sent[0][2]["content"]
    assert sent[1][2]["status"] == "draft"
    assert rewrite_links("https://a.example/", "https://a.example", "https://a.example") == (
        "https://a.example/"
    )


def test_compare_sites_names_what_only_one_has_and_what_differs() -> None:
    first = Site("a", [_post("about"), _post("only")])
    second = Site("b", [_post("about", status="draft")])
    found = {
        (d.slug, d.words)
        for d in compare_sites(first, second, first_name="A", second_name="B", kinds=("post",))
    }
    assert ("only", "only on A") in found
    assert ("about", "publish here, draft there") in found


def test_a_snapshot_saves_every_part_with_its_counts(tmp_path) -> None:
    where, counts = take_snapshot(Site("a", [_post("x")]), tmp_path, site="A", clock=lambda: 0)
    assert counts["posts"] == 1 and (where / "posts.json").is_file()
    assert json.loads((where / "snapshot.json").read_text(encoding="utf-8"))["site"] == "A"


def test_the_calendar_groups_by_day_and_reads_in_words() -> None:
    site = Site("a", [_post("x", status="future", date="2026-11-12T09:00:00")])
    days = calendar_days([("A", site)], since="2026-11-01", kinds=("post",))
    assert list(days) == ["2026-11-12"]
    assert day_words("2026-11-12", 2, 1) == "Thursday 12 November: 2 scheduled, 1 published"


def test_read_site_as_document_has_a_heading_per_page() -> None:
    text = site_document(
        "Radio",
        [
            {
                "title": {"rendered": "About"},
                "link": "https://r/about",
                "content": {"rendered": "<p>Hi</p>"},
            }
        ],
    )
    assert text.startswith("# Radio") and "## About" in text and "Address: https://r/about" in text


def test_lists_go_out_as_csv_and_excel_and_come_back_in(tmp_path) -> None:
    pytest.importorskip("openpyxl")
    for name in ("out.csv", "out.xlsx"):
        path = tmp_path / name
        assert export_rows(path, ["Title", "Status"], [["Hi", "draft"]]) == 1
        assert read_spreadsheet(path) == [{"title": "Hi", "status": "draft"}]
    plan = import_plan([{"title": "A"}, {"status": "nonsense", "title": "B"}, {}])
    assert [p.problem == "" for p in plan] == [True, False, False]
    site = Site("a")
    assert send_import(site, "post", plan) == []
    assert site.writes == [
        ("POST", "wp/v2/posts", {"title": "A", "content": "", "status": "draft"})
    ]


def test_the_console_completes_parses_and_draws_the_answer() -> None:
    assert complete_route("wp/v2/po", ["/wp/v2/posts", "/wp/v2/pages"]) == ["wp/v2/posts"]
    assert parse_params("a=1\nb = two") == {"a": "1", "b": "two"}
    assert parse_params('{"x": 2}') == {"x": 2}
    with pytest.raises(ValueError):
        parse_params("nonsense")
    assert needed_capability("POST", "wp/v2/posts") == "edit_posts"
    assert needed_capability("GET", "wp/v2/posts") == ""
    tree = answer_tree({"id": 3, "tags": [1, 2]})
    assert tree.label == "Answer (2 fields)" and tree.children[0].label == "id: 3"
    assert tree.children[1].label == "tags (2 items)"


def test_watches_learn_first_then_say_only_what_is_new() -> None:
    site = Site("a")
    site.comments = [1]
    state = WatchState()
    assert check([("A", site, [])], state, ["comment"], now=lambda: 1000.0) == []
    site.comments = [1, 2, 3]
    assert check([("A", site, [])], state, ["comment"], now=lambda: 2000.0) == [
        "2 new comments waiting on A."
    ]
    assert not due(state, 15, now=lambda: 2000.0 + 60)
    assert due(state, 15, now=lambda: 2000.0 + 15 * 60)


def test_the_practice_site_says_what_is_missing_and_builds_its_command(tmp_path) -> None:
    assert "Playground" in missing_words(PracticeTools(None, None))
    tools = PracticeTools(tmp_path / "node.exe", tmp_path / "cli.js")
    argv = start_command(tools, tmp_path / "site")
    assert argv[2] == "server" and "--port=9400" in argv and "--login" in argv
    plan = json.loads((tmp_path / "site" / "blueprint.json").read_text(encoding="utf-8"))
    assert plan["steps"][0]["step"] == "login"
    assert "runPHP" == blueprint()["steps"][1]["step"]  # type: ignore[index]
    assert read_password(tmp_path / "site") is None
    (tmp_path / "site" / "quill-practice-password.json").write_text(
        '{"username": "admin", "password": "abcd"}', encoding="utf-8"
    )
    assert read_password(tmp_path / "site") == ("admin", "abcd")
