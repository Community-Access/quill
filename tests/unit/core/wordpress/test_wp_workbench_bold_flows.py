"""W7's bold workflows end to end on fake sites: copy, compare, snapshots, reading,
the queue and its clock, Watches, the REST Console's routes, and lists in and out."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.schedule import ScheduleError
from quill.core.wordpress.workbench_editorial import (
    Review,
    assign_reviewer,
    load_reviews,
    moment_words,
    queue_positions,
    site_moment,
)
from quill.core.wordpress.workbench_io import (
    export_rows,
    folder_plan,
    import_mapping,
    import_plan,
    send_import_results,
)
from quill.core.wordpress.workbench_read_site import ReadScope, document_pages, site_document
from quill.core.wordpress.workbench_rest_routes import (
    argument_lines,
    argument_problems,
    arguments,
    fill_route,
    find_entry,
    route_template,
    schema_lines,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_site_copy import plan_copy, rewrite_links, run_copy
from quill.core.wordpress.workbench_snapshot import (
    compare_sites,
    restore_plan,
    run_restore,
    take_snapshot,
)
from quill.core.wordpress.workbench_watches import WatchState, check, status_facts


class _Address:
    wpcom_site = ""

    def __init__(self, url: str) -> None:
        self.site_url = url


class Site:
    """A fake site: collections by route, each item by id, every write recorded."""

    def __init__(self, url: str, **collections: list[dict[str, Any]]) -> None:
        self.address = _Address(url)
        self.site_name = url
        self.data: dict[str, list[dict[str, Any]]] = {
            route.replace("__", "/").replace("_", "-"): rows for route, rows in collections.items()
        }
        self.writes: list[tuple[str, str, Any]] = []
        self.uploads: list[str] = []
        self.broken: set[str] = set()
        self.next_id = 900

    def _rows(self, route: str) -> list[dict[str, Any]]:
        return self.data.setdefault(route, [])

    def get(self, route: str, **params: Any) -> Any:
        if route in self.broken:
            raise WordPressApiError("no", status=500)
        base, _sep, tail = route.rpartition("/")
        if tail.isdigit():
            found = next((r for r in self._rows(base) if r.get("id") == int(tail)), None)
            if found is None:
                raise WordPressApiError("gone", status=404)
            return dict(found)
        rows = self._rows(route)
        if "slug" in params and route != "wp/v2/menus":  # menus ignore it, as some sites do
            rows = [r for r in rows if r.get("slug") == params["slug"]]
        if "search" in params:
            word = str(params["search"]).casefold()
            rows = [
                r
                for r in rows
                if word in str(r.get("name", "")).casefold()
                or word in str(r.get("username", "")).casefold()
            ]
        return [dict(r) for r in rows]

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        if route in self.broken:
            raise WordPressApiError("no", status=500)
        params = dict(params or {})
        for row in self._rows(route):
            if "menus" in params and row.get("menus") != params["menus"]:
                continue
            if "categories" in params and params["categories"] not in row.get("categories", []):
                continue
            if params.get("status") not in (None, "any") and row.get("status") != params["status"]:
                continue
            yield dict(row)

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append(("POST", route, body))
        self.next_id += 1
        return {"id": self.next_id, **(body or {})}

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {}

    def upload(self, route: str, name: str, data: bytes, kind: str, **_kw: Any) -> Any:
        self.uploads.append(name)
        self.next_id += 1
        return {"id": self.next_id, "source_url": f"{self.address.site_url}/up/{name}"}


A, B = "https://a.example", "https://b.example"


def _post(ident: int, slug: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": ident,
        "slug": slug,
        "type": "post",
        "status": "publish",
        "title": {"raw": slug.title()},
        "content": {"raw": f'<a href="{A}/x">x</a> <img src="{A}/p.png"> {slug}'},
        **extra,
    }


# -- copy ---------------------------------------------------------------------


def test_copy_maps_authors_reuses_files_keeps_status_and_rewrites_every_link() -> None:
    source = Site(
        A,
        wp__v2__users=[{"id": 7, "name": "Ann Lee", "username": "ann"}],
        wp__v2__media=[{"id": 30, "source_url": f"{A}/feature.png"}],
    )
    target = Site(
        B,
        wp__v2__posts=[_post(5, "about", status="publish")],
        wp__v2__users=[{"id": 70, "name": "Ann Lee", "username": "ann"}],
        wp__v2__media=[{"id": 31, "slug": "logo", "source_url": f"{B}/logo.png"}],
    )
    rows = [
        ("item", "post", _post(1, "about", status="draft", author=7, featured_media=30)),
        ("item", "post", _post(2, "news", author=8)),
        ("media", "", {"id": 3, "slug": "logo", "source_url": f"{A}/logo.png", "title": "Logo"}),
        ("media", "", {"id": 4, "slug": "pic", "source_url": f"{A}/pic.png", "alt_text": "A cat"}),
    ]
    plan = plan_copy(target, rows, source_site="A", target_site="B", source_url=A, source=source)
    assert [line.action for line in plan.lines] == ["replace", "create", "skip", "create"]
    assert "status is kept" in plan.lines[0].why and "by Ann Lee" in plan.lines[0].why
    assert "author 8 has no account on B" in plan.lines[1].why
    assert plan.reuse == {f"{A}/logo.png": f"{B}/logo.png"}
    failed = run_copy(source, target, plan, source_url=A, target_url=B, fetch=lambda u: b"x")
    assert failed == []
    posts = [w for w in target.writes if w[1].startswith("wp/v2/posts")]
    replaced, made = posts[0][2], posts[1][2]
    assert posts[0][1] == "wp/v2/posts/5" and "status" not in replaced
    assert replaced["author"] == 70 and replaced["featured_media"]
    assert f"{B}/x" in replaced["content"] and f"{B}/up/p.png" in replaced["content"]
    assert made["status"] == "draft" and "author" not in made
    assert any(w[2].get("alt_text") == "A cat" for w in target.writes if "media/" in w[1])
    assert sorted(target.uploads) == ["feature.png", "p.png", "pic.png"]
    assert len(plan.outcomes) == 4


def test_a_site_that_ignores_slug_is_not_mistaken_for_a_match_and_terms_match_by_name() -> None:
    target = Site(
        B,
        wp__v2__menus=[{"id": 4, "name": "Footer", "slug": "footer"}],
        wp__v2__categories=[{"id": 9, "name": "Shows", "slug": "shows-2"}],
    )
    rows = [
        ("menu", "", {"id": 1, "name": "Main", "slug": "main"}),
        ("term", "category", {"id": 2, "name": "Shows", "slug": "shows", "taxonomy": "category"}),
    ]
    plan = plan_copy(target, rows, source_site="A", target_site="B", source_url=A)
    assert [line.action for line in plan.lines] == ["create", "replace"]
    assert plan.lines[1].target_id == 9 and "same name" in plan.lines[1].why


def test_a_menu_travels_with_its_links_in_order_matched_or_made_plain() -> None:
    source = Site(
        A,
        wp__v2__pages=[{"id": 11, "slug": "about"}, {"id": 12, "slug": "gone"}],
        wp__v2__menu_items=[
            {
                "id": 1,
                "menus": 3,
                "title": {"raw": "About"},
                "type": "post_type",
                "object": "page",
                "object_id": 11,
                "menu_order": 1,
                "url": f"{A}/about",
            },
            {
                "id": 2,
                "menus": 3,
                "title": {"raw": "Gone"},
                "type": "post_type",
                "object": "page",
                "object_id": 12,
                "menu_order": 2,
                "parent": 1,
                "url": f"{A}/gone",
            },
        ],
    )
    target = Site(B, wp__v2__pages=[{"id": 50, "slug": "about"}])
    plan = plan_copy(
        target,
        [("menu", "", {"id": 3, "name": "Main", "slug": "main"})],
        source_site="A",
        target_site="B",
        source_url=A,
        source=source,
    )
    assert "with its 2 links" in plan.lines[0].why
    assert run_copy(source, target, plan, source_url=A, target_url=B) == []
    links = [w[2] for w in target.writes if w[1] == "wp/v2/menu-items"]
    assert links[0]["object_id"] == 50 and links[0]["parent"] == 0
    assert links[1]["type"] == "custom" and links[1]["url"] == f"{B}/gone"
    assert links[1]["parent"] == target.next_id - 1


def test_links_are_rewritten_in_both_schemes_and_in_block_attributes() -> None:
    text = 'http://a.example/p {"url":"https:\\/\\/a.example\\/q"}'
    out = rewrite_links(text, A, B)
    assert out == 'https://b.example/p {"url":"https:\\/\\/b.example\\/q"}'


# -- compare and snapshots ------------------------------------------------------


def test_compare_covers_terms_names_unreadable_kinds_and_states_omissions() -> None:
    first = Site(A, wp__v2__categories=[{"id": 1, "slug": "news", "name": "News"}])
    second = Site(B, wp__v2__categories=[{"id": 2, "slug": "news", "name": "Updates"}])
    second.broken.add("wp/v2/menus")
    found = {
        (d.kind, d.slug, d.words)
        for d in compare_sites(first, second, first_name="A", second_name="B")
    }
    assert ("category", "news", "names differ") in found
    assert any(k == "menu" and "not compared: B said" in w for k, _s, w in found)


def test_a_snapshot_says_what_it_could_not_read_and_saves_media_files_when_asked(
    tmp_path: Path,
) -> None:
    site = Site(A, wp__v2__media=[{"id": 4, "source_url": f"{A}/a.png"}])
    site.broken.add("wp/v2/menus")
    where, counts = take_snapshot(
        site, tmp_path, site="A", media=True, fetch=lambda u: b"png", clock=lambda: 0
    )
    told = json.loads((where / "snapshot.json").read_text(encoding="utf-8"))
    assert told["media_files"] is True and told["unread"][0].startswith("menus")
    assert "people" in told["never_taken"] and "Revisions" in told["put_back"]
    assert (where / "media files" / "4-a.png").read_bytes() == b"png"
    assert counts["media"] == 1 and "menus" not in counts


def test_put_back_sets_changed_items_back_and_remakes_deleted_ones(tmp_path: Path) -> None:
    then = [_post(1, "kept"), _post(2, "changed"), _post(3, "deleted")]
    site = Site(A, wp__v2__posts=[dict(p) for p in then])
    where, _counts = take_snapshot(site, tmp_path, site="A", clock=lambda: 0)
    site.data["wp/v2/posts"] = [then[0], {**then[1], "title": {"raw": "Edited"}}]
    lines = restore_plan(site, where)
    assert [(line.action, line.title) for line in lines] == [
        ("put back", "Changed"),
        ("make again", "Deleted"),
    ]
    said = run_restore(site, lines)
    assert said == ["Put back: post Changed.", "Made again: post Deleted."]
    assert site.writes[-1][2]["status"] == "draft" and site.writes[-2][1] == "wp/v2/posts/2"


# -- reading the site -------------------------------------------------------------


def test_reading_a_menu_follows_its_order_and_names_what_it_leaves_out() -> None:
    site = Site(
        A,
        wp__v2__pages=[
            {
                "id": 1,
                "title": {"rendered": "Home"},
                "status": "publish",
                "content": {"rendered": "<h1>Welcome</h1><p>Hi <a href='u'>there</a></p>"},
            },
            {
                "id": 2,
                "title": {"rendered": "Secret"},
                "status": "publish",
                "content": {"rendered": "", "protected": True},
            },
        ],
        wp__v2__menu_items=[
            {
                "id": 8,
                "menus": 5,
                "type": "custom",
                "url": "https://x",
                "title": {"raw": "X"},
                "menu_order": 0,
            },
            {
                "id": 9,
                "menus": 5,
                "type": "post_type",
                "object": "page",
                "object_id": 2,
                "menu_order": 2,
            },
            {
                "id": 10,
                "menus": 5,
                "type": "post_type",
                "object": "page",
                "object_id": 1,
                "menu_order": 1,
            },
        ],
    )
    pages, notes = document_pages(site, ReadScope("menu", 5, "Main"), site="A")
    assert [p["id"] for p in pages] == [1]
    assert any("password-protected" in n for n in notes) and any("X" in n for n in notes)
    text = site_document(
        "A",
        pages,
        address=A,
        scope=ReadScope("menu", 5, "Main").words,
        made="2026-11-13",
        notes=notes,
    )
    assert "- Read from: https://a.example" in text and "### Welcome" in text
    assert "[there](u)" in text and "Only published content" in text


def test_reading_a_category_is_bounded_and_says_so() -> None:
    posts = [_post(i, f"p{i}", categories=[4]) for i in range(1, 6)]
    pages, notes = document_pages(
        Site(A, wp__v2__posts=posts), ReadScope("category", 4, "N"), limit=3
    )
    assert len(pages) == 3 and any("Only the first 3" in n for n in notes)


# -- the clock and the queue --------------------------------------------------------


def test_a_time_the_clocks_skip_or_repeat_is_named_not_guessed() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    zone = "America/New_York"
    with pytest.raises(ScheduleError, match="does not happen"):
        site_moment("2026-03-08", "2:30 AM", zone, now=now)
    with pytest.raises(ScheduleError, match="happens twice"):
        site_moment("2026-11-01", "1:30 AM", zone, now=now)
    first = site_moment("2026-11-01", "1:30 AM first", zone, now=now)
    second = site_moment("2026-11-01", "1:30 AM second", zone, now=now)
    assert second.timestamp() - first.timestamp() == 3600
    with pytest.raises(ScheduleError, match="future"):
        site_moment("2025-01-01", "9:00", zone, now=now)
    assert site_moment("2025-01-01", "9:00", zone, future_only=False, now=now).year == 2025
    words = moment_words(site_moment("2026-11-20", "9:00", "UTC", now=now), "UTC", here=UTC)
    assert (
        words == "Friday 20 November 2026, 9:00 AM at the site (UTC), which is the same time here"
    )


def test_reviews_are_kept_once_per_item_and_the_queue_says_where_each_stands(
    tmp_path: Path,
) -> None:
    assign_reviewer(tmp_path, Review("A", 1, "wp/v2/posts/1", "One", "Ann"), clock=lambda: 1.0)
    assign_reviewer(tmp_path, Review("A", 1, "wp/v2/posts/1", "One", "Bo"), clock=lambda: 2.0)
    assert [r.reviewer for r in load_reviews(tmp_path)] == ["Bo"]
    rows = [
        WbRow("item", "A", "1", {}, "", status="pending", raw={"modified_gmt": "2026-02"}),
        WbRow("item", "A", "2", {}, "", status="pending", raw={"modified_gmt": "2026-01"}),
    ]
    assert queue_positions(rows)[("A", "1")] == "2 of 2 waiting on A"


# -- Watches -------------------------------------------------------------------------


def test_a_watch_turned_on_later_starts_silent_and_a_down_site_is_said_once() -> None:
    site = Site(A, wp__v2__comments=[{"id": 1, "status": "hold"}])
    state = WatchState()
    assert check([("A", site, [])], state, ["published"], now=lambda: 1.0) == []
    # Comments switched on later: their first look is silent too.
    on = ["comment", "site_down"]
    assert check([("A", site, [])], state, ["published", *on], now=lambda: 2.0) == []
    assert check([], state, on, unreachable=["A"], now=lambda: 3.0) == [
        "A is not answering. Watches will try again next round."
    ]
    assert check([], state, on, unreachable=["A"], now=lambda: 4.0) == []
    site.data["wp/v2/comments"].append({"id": 2, "status": "hold"})
    assert check([("A", site, [])], state, on, now=lambda: 5.0) == [
        "A answers again.",
        "1 new comment waiting on A.",
    ]


def test_the_review_watch_says_when_an_item_leaves_the_queue_and_status_goes_stale() -> None:
    site = Site(A, wp__v2__posts=[{"id": 1, "status": "pending"}])
    review = Review("A", 1, "wp/v2/posts/1", "One", "Ann")
    state = WatchState()
    assert check([("A", site, [])], state, ["review"], reviews=[review], now=lambda: 1.0) == []
    site.data["wp/v2/posts"][0]["status"] = "future"
    said = check([("A", site, [])], state, ["review"], reviews=[review], now=lambda: 2.0)
    assert said == ["One on A was approved and scheduled."]
    facts = dict(status_facts(state, ["A", "B"], 15, now=lambda: 2.0 + 3600))
    assert "stale" in facts["Last round"] and facts["B"] == "not checked yet"
    assert facts["A"].startswith("answering")


# -- the REST Console's routes --------------------------------------------------------

_ROUTES = {
    "/wp/v2/posts": {
        "endpoints": [
            {"methods": ["GET"], "args": {"per_page": {"type": "integer"}}},
            {
                "methods": ["POST"],
                "args": {
                    "title": {"type": "string", "required": True, "description": "The title."},
                    "status": {"type": "string", "enum": ["draft", "publish"]},
                },
            },
        ]
    },
    "/wp/v2/posts/(?P<id>[\\d]+)": {"endpoints": [{"methods": ["GET", "DELETE"], "args": {}}]},
}


def test_routes_complete_as_templates_fill_from_parameters_and_check_arguments() -> None:
    assert route_template("/wp/v2/posts/(?P<id>[\\d]+)") == "wp/v2/posts/{id}"
    assert fill_route("wp/v2/posts/{id}", {"id": "12", "force": "1"}) == (
        "wp/v2/posts/12",
        {"force": "1"},
    )
    with pytest.raises(ValueError, match="needs id"):
        fill_route("wp/v2/posts/{id}", {})
    assert find_entry(_ROUTES, "wp/v2/posts/12") is _ROUTES["/wp/v2/posts/(?P<id>[\\d]+)"]
    args = arguments(_ROUTES["/wp/v2/posts"], "POST")
    assert argument_lines(args)[0] == "title (string, required): The title."
    assert argument_problems(args, {"status": "gone", "colour": "red"}) == [
        "title is required.",
        "status must be one of draft, publish.",
        "colour is not something this route takes.",
    ]
    schema = {"title": "post", "properties": {"id": {"type": "integer", "readonly": True}}}
    assert schema_lines(schema) == ["Answers with: post", "id (integer, read only)"]


# -- lists in and out -----------------------------------------------------------------


def test_lists_go_out_as_markdown_and_spreadsheets_come_in_mapped_as_drafts(
    tmp_path: Path,
) -> None:
    out = tmp_path / "list.md"
    assert export_rows(out, ["Title", "Note"], [["A|B", "one\ntwo"]]) == 1
    assert out.read_text(encoding="utf-8").splitlines()[2] == "| A\\|B | one<br>two |"
    assert import_mapping(["Headline", "Body", "Colour", "Publish Date"]) == (
        {"headline": "title", "body": "content", "publish date": "date"},
        ["colour"],
    )
    plan = import_plan([{"headline": "Go", "post status": "publish"}, {"colour": "red"}])
    assert plan[0].fields["status"] == "draft" and "publish it after a look" in plan[0].sentence
    said = send_import_results(Site(A), "post", plan)
    assert said[0].startswith("Made Row 2: Go") and said[1].startswith("Skipped Row 3")


def test_a_folder_of_documents_becomes_drafts_titled_by_their_first_heading(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.md").write_text("# Second\n\nText", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "skip.png").write_bytes(b"x")
    plan = folder_plan(tmp_path, lambda p: p.read_text(encoding="utf-8"))
    assert [(r.name, r.problem) for r in plan] == [("a.txt", "it is empty"), ("b.md", "")]
    assert plan[1].fields["title"] == "Second" and "Text" in plan[1].fields["content"]


# -- the leftovers: plain-language batches, Site Health Watch, saved requests, Gravity Forms


def test_plain_words_become_exact_requests_or_say_what_they_read() -> None:
    from quill.core.wordpress.workbench_plain_batch import PhraseError, parse_request

    sites = ["Radio", "Shop"]
    asked = parse_request("Move all drafts by Sam to pending on radio", sites, "Shop")
    assert (asked.action, asked.value, asked.status, asked.author, asked.sites) == (
        "status",
        "pending",
        "draft",
        "Sam",
        ("Radio",),
    )
    tagged = parse_request("add tag 2026 to posts in category Events on every site", sites)
    assert (tagged.action, tagged.value, tagged.category, tagged.sites) == (
        "add_tag",
        "2026",
        "Events",
        ("Radio", "Shop"),
    )
    assert parse_request("remove tag Old from published posts", sites, "Shop").sites == ("Shop",)
    for words, said in (
        ("delete everything", "It reads phrases like"),
        ("move all drafts to pending on Moon", "No connected site is called Moon"),
        ("add tag X to pages", "Pages have no tags"),
    ):
        with pytest.raises(PhraseError, match=said):
            parse_request(words, sites, "Radio")


def test_a_plain_batch_resolves_exact_items_and_runs_with_a_conflict_check() -> None:
    from quill.core.wordpress.workbench_plain_batch import parse_request, resolve, run_site

    site = Site(
        A,
        wp__v2__users=[{"id": 4, "name": "Sam"}, {"id": 5, "name": "Samuel"}],
        wp__v2__tags=[{"id": 8, "name": "Old"}],
        wp__v2__posts=[
            _post(1, "a", status="draft", author=4, modified_gmt="t1"),
            _post(2, "b", status="pending", author=4, modified_gmt="t1"),
        ],
    )
    site._quill_no_batch = True  # type: ignore[attr-defined]
    request = parse_request("move all drafts by Sam to pending", ["A"], "A")
    plan = resolve(request, "A", site)
    assert [r.key for r in plan.rows] == ["1"] and plan.bodies == [{"status": "pending"}]
    assert run_site(site, plan, [0]) == ["A, A: saved"]
    assert ("POST", "wp/v2/posts/1", {"status": "pending"}) in site.writes
    nobody = resolve(parse_request("move drafts by Zed to pending", ["A"], "A"), "A", site)
    assert nobody.sentence == "A: nothing, because Zed has no account there."
    tag = resolve(parse_request("add tag Fresh to posts", ["A"], "A"), "A", site)
    assert tag.make_tag == "Fresh" and len(tag.rows) == 2
    run_site(site, tag, [0])
    made = next(w for w in site.writes if w[1] == "wp/v2/tags")
    assert made[2] == {"name": "Fresh"}
    assert site.writes[-1][2] == {"tags": [site.next_id - 1]}


def test_the_health_watch_says_only_a_test_whose_status_changed() -> None:
    site = Site(A)
    status = {"t": "good"}
    original = site.get

    def get(route: str, **params: Any) -> Any:
        if route == "":
            return {"namespaces": ["wp-site-health/v1"], "routes": {}}
        if route.startswith("wp-site-health/v1/tests/"):
            return {"status": status["t"] if route.endswith("https-status") else "good"}
        return original(route, **params)

    site.get = get  # type: ignore[method-assign]
    state = WatchState()
    assert check([("A", site, [])], state, ["health"], now=lambda: 1.0) == []
    assert check([("A", site, [])], state, ["health"], now=lambda: 2.0) == []
    status["t"] = "critical"
    said = check([("A", site, [])], state, ["health"], now=lambda: 3.0)
    assert len(said) == 1 and said[0].startswith("Site Health on A:")
    assert said[0].endswith("is now critical.")


def test_saved_requests_are_kept_by_name_newest_first(tmp_path: Path) -> None:
    from quill.core.wordpress.workbench_rest_saved import (
        SavedRequest,
        forget,
        load_saved,
        remember,
    )

    remember(SavedRequest("Drafts", "A", "GET", "wp/v2/posts", "status=draft"), tmp_path)
    remember(SavedRequest("Me", "A", "GET", "wp/v2/users/me"), tmp_path)
    remember(SavedRequest("drafts", "A", "GET", "wp/v2/pages", "status=draft"), tmp_path)
    assert [(r.name, r.route) for r in load_saved(tmp_path)] == [
        ("drafts", "wp/v2/pages"),
        ("Me", "wp/v2/users/me"),
    ]
    assert [r.name for r in forget("ME", tmp_path)] == ["drafts"]


def test_a_gravity_form_copies_whole_without_entries_and_replaces_by_title() -> None:
    class Gravity(Site):
        def request(self, method: str, route: str, **kw: Any) -> Any:
            self.writes.append((method, route, kw.get("json_body")))

            class _R:
                payload: dict[str, Any] = {}

            return _R()

    form = {
        "id": 3,
        "title": "Sign Up",
        "fields": [{"id": 1, "type": "text"}],
        "confirmations": {"c": {"url": f"{A}/thanks"}},
        "entries": 12,
        "date_created": "x",
    }
    source = Site(A, gf__v2__forms=[form])
    target = Gravity(B, gf__v2__forms=[{"id": 9, "title": "sign up"}])
    rows = [("gravity_form", "gravity", {"id": 3, "title": "Sign Up"})]
    plan = plan_copy(target, rows, source_site="A", target_site="B", source_url=A, source=source)
    assert plan.lines[0].action == "replace" and "entries there are kept" in plan.lines[0].why
    assert "never its entries" in plan.lines[0].why
    assert run_copy(source, target, plan, source_url=A, target_url=B) == []
    method, route, body = target.writes[-1]
    assert (method, route) == ("PUT", "gf/v2/forms/9") and "entries" not in body
    assert body["confirmations"]["c"]["url"] == f"{B}/thanks" and body["id"] == 9
    fresh = Gravity(B)
    plan = plan_copy(fresh, rows, source_site="A", target_site="B", source_url=A, source=source)
    run_copy(source, fresh, plan, source_url=A, target_url=B)
    assert fresh.writes[-1][1] == "gf/v2/forms" and "date_created" not in fresh.writes[-1][2]
