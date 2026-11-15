"""Copy to Site: a post selected before its own tag, and a term the target already has."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_site_copy import plan_copy, run_copy
from quill.core.wordpress.workbench_site_copy_order import ALREADY_THERE, term_id


class _Address:
    wpcom_site = ""

    def __init__(self, url: str) -> None:
        self.site_url = url


class Site:
    """Tags kept as WordPress keeps them: one per name, ``term_exists`` for a second."""

    def __init__(self, url: str, *, search_finds: bool = True) -> None:
        self.address = _Address(url)
        self.site_name = url
        self.tags: dict[int, dict[str, Any]] = {}
        self.search_finds = search_finds  # False: a search that misses (entities, caching)
        self.writes: list[tuple[str, Any]] = []

    def add_tag(self, name: str, slug: str) -> dict[str, Any]:
        ident = 100 + len(self.tags)
        self.tags[ident] = {"id": ident, "name": name, "slug": slug}
        return self.tags[ident]

    def get(self, route: str, **params: Any) -> Any:
        if route.startswith("wp/v2/tags/"):
            return self.tags[int(route.rsplit("/", 1)[1])]
        if route == "wp/v2/tags":
            rows = list(self.tags.values())
            if "slug" in params:
                return [t for t in rows if t["slug"] == params["slug"]]
            if "search" in params and self.search_finds:
                return [t for t in rows if params["search"].lower() in t["name"].lower()]
            if "search" in params:
                return []
            return rows
        return []

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append((route, body))
        if route == "wp/v2/tags":
            same = [t for t in self.tags.values() if t["name"] == body["name"]]
            if same:
                raise WordPressApiError(
                    "A category or tag with that name already exists.",
                    status=400,
                    wp_code="term_exists",
                    body={"code": "term_exists", "data": {"status": 400, "term_id": same[0]["id"]}},
                )
            return self.add_tag(body["name"], body["slug"])
        return {"id": 900, **(body or {})}

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Any:
        return iter(())


def _post_with(tag: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": 5,
        "slug": "hello",
        "type": "post",
        "title": {"raw": "Hello"},
        "content": {"raw": "<p>Hi</p>"},
        "tags": [tag["id"]],
    }


def test_a_post_selected_before_its_own_tag_is_copied_after_it() -> None:
    source, target = Site("https://a.example"), Site("https://b.example")
    tag = source.add_tag("News", "news")
    rows = [("item", "post", _post_with(tag)), ("term", "post_tag", tag)]
    plan = plan_copy(target, rows, source_site="A", target_site="B", source_url="https://a.example")
    assert [line.kind for line in plan.lines] == ["item", "term"]  # the preview: as chosen
    failed = run_copy(
        source, target, plan, source_url="https://a.example", target_url="https://b.example"
    )
    assert failed == []
    assert plan.outcomes == ["Made term News.", "Made item Hello."]
    [made] = target.tags.values()
    post_body = next(body for route, body in target.writes if route == "wp/v2/posts")
    assert post_body["tags"] == [made["id"]]


def test_a_term_made_meanwhile_is_already_there_not_a_failure() -> None:
    source, target = Site("https://a.example"), Site("https://b.example", search_finds=False)
    tag = source.add_tag("News", "news")
    plan = plan_copy(
        target,
        [("term", "post_tag", tag), ("item", "post", _post_with(tag))],
        source_site="A",
        target_site="B",
        source_url="https://a.example",
    )
    there = target.add_tag("News", "news")  # made after the preview, before the copy
    failed = run_copy(
        source, target, plan, source_url="https://a.example", target_url="https://b.example"
    )
    assert failed == []
    assert plan.outcomes[0] == f"{ALREADY_THERE} term News."
    assert len(target.tags) == 1
    post_body = next(body for route, body in target.writes if route == "wp/v2/posts")
    assert post_body["tags"] == [there["id"]]


def test_term_id_reuses_by_name_and_raises_any_other_refusal() -> None:
    target = Site("https://b.example")
    kept = target.add_tag("News", "news")
    assert term_id(target, "wp/v2/tags", {"name": "news", "slug": "x"}) == (kept["id"], True)
    assert term_id(target, "wp/v2/tags", {"name": "Sport", "slug": "sport"})[1] is False

    class Refusing(Site):
        def post(self, route: str, body: Any = None, **_p: Any) -> Any:
            raise WordPressApiError("No.", status=403, wp_code="rest_cannot_create")

    try:
        term_id(Refusing("https://c.example"), "wp/v2/tags", {"name": "Art"})
    except WordPressApiError as exc:
        assert exc.status == 403
    else:
        raise AssertionError("a refusal was swallowed")
