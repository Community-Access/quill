"""Taxonomies, statuses and writing types, as the site describes them (WP-R-031, WP-R-032)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress import site_types as stypes
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi, WordPressApiError

FIXTURES = Path(__file__).parent / "fixtures"
RECORDED = json.loads((FIXTURES / "discovery_test_site.json").read_text(encoding="utf-8"))


class _Response:
    def __init__(self, payload, headers=None):
        self._raw = json.dumps(payload).encode()
        self.status = 200
        self.headers = headers or {}

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class FakeSite:
    """Answers by (method, path); records (method, path, query) for every request."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.seen: list[tuple[str, str, dict]] = []
        self.bodies: list[object] = []

    def __call__(self, request, timeout=None, context=None):
        parsed = urlparse(request.full_url)
        path = parsed.path.removeprefix("/wp-json/")
        query = parse_qs(parsed.query)
        self.seen.append((request.get_method(), path, query))
        if request.data:
            self.bodies.append(json.loads(request.data))
        answer = self.routes.get((request.get_method(), path))
        if callable(answer):
            answer = answer(query)
        if isinstance(answer, int):
            raise HTTPError(request.full_url, answer, "no", {}, io.BytesIO(b'{"code":"nope"}'))
        if answer is None:
            raise HTTPError(
                request.full_url, 404, "nf", {}, io.BytesIO(b'{"code":"rest_no_route"}')
            )
        if isinstance(answer, _Response):
            return answer
        return _Response(answer)

    def paths(self) -> list[str]:
        return [p for _m, p, _q in self.seen]


def _api(fake, user="jeff", site="https://radio.example"):
    return WordPressApi(SiteAddress(site), SiteAuth("app_password", user, "abcd efgh"), opener=fake)


@pytest.fixture(autouse=True)
def _fresh_cache():
    tx.clear_cache()
    yield
    tx.clear_cache()


def _recorded_site(more: dict | None = None) -> FakeSite:
    return FakeSite({
        ("GET", "wp/v2/taxonomies"): RECORDED["taxonomies"],
        ("GET", "wp/v2/statuses"): RECORDED["statuses"],
        ("GET", "wp/v2/types"): RECORDED["types"],
        **(more or {}),
    })


# --------------------------------------------------------------------------- #
# taxonomies


def test_every_taxonomy_the_test_site_lists_is_read_with_its_route_and_types() -> None:
    found = tx.discover_taxonomies(_api(_recorded_site()))
    assert set(found) == set(RECORDED["taxonomies"])
    events = found["tribe_events_cat"]
    assert events.route == "wp/v2/tribe_events_cat"
    assert events.hierarchical and events.types == ("tribe_events",)
    assert found["post_tag"].types == ("post", "tribe_events")
    assert not found["product_tag"].hierarchical


def test_the_route_comes_from_rest_base_not_from_the_name() -> None:
    # A taxonomy whose route differs from its slug: guessing would ask wp/v2/genre.
    fake = FakeSite({
        ("GET", "wp/v2/taxonomies"): {
            "genre": {
                "slug": "genre",
                "name": "Genres",
                "rest_base": "genres",
                "rest_namespace": "music/v1",
                "hierarchical": True,
                "types": ["album"],
            },
        },
        ("GET", "music/v1/genres"): [{"id": 4, "name": "Jazz", "slug": "jazz", "count": 2}],
    })
    api = _api(fake)
    assert wp.taxonomy_route("genre", api) == "music/v1/genres"
    assert wp.taxonomy_field("genre", api) == "genres"
    assert [t.name for t in wp.list_terms(api, "genre")] == ["Jazz"]
    # The site was asked once, then the cache answered.
    assert fake.paths().count("wp/v2/taxonomies") == 1


def test_core_taxonomies_never_cost_a_request_of_their_own() -> None:
    fake = FakeSite({("GET", "wp/v2/tags"): [{"id": 1, "name": "JAWS", "slug": "jaws"}]})
    api = _api(fake)
    assert wp.taxonomy_route("category", api) == "wp/v2/categories"
    assert [t.name for t in wp.list_terms(api, "post_tag")] == ["JAWS"]
    assert fake.paths() == ["wp/v2/tags"]


def test_without_a_site_or_when_it_will_not_say_the_old_guess_stands() -> None:
    assert wp.taxonomy_route("category") == "wp/v2/categories"
    assert wp.taxonomy_route("post_tag") == "wp/v2/tags"
    assert wp.taxonomy_route("genre") == "wp/v2/genre"
    fake = FakeSite({("GET", "wp/v2/taxonomies"): 500})
    api = _api(fake)
    assert wp.taxonomy_route("genre", api) == "wp/v2/genre"
    assert wp.taxonomy_route("genre", api) == "wp/v2/genre"
    # A failed answer is remembered too, so a broken site is not asked on every call.
    assert fake.paths().count("wp/v2/taxonomies") == 1


def test_a_taxonomy_named_by_its_route_is_still_found() -> None:
    api = _api(_recorded_site())
    tx.discover_taxonomies(api)
    assert tx.lookup(api, "categories") is not None
    assert tx.lookup(api, "categories").slug == "category"


def test_the_cache_is_per_connection_and_can_be_forgotten() -> None:
    fake = _recorded_site()
    tx.discover_taxonomies(_api(fake))
    tx.discover_taxonomies(_api(fake))  # a new client for the same connection
    assert fake.paths().count("wp/v2/taxonomies") == 1
    tx.discover_taxonomies(_api(fake, user="someone-else"))
    tx.discover_taxonomies(_api(fake, site="https://other.example"))
    assert fake.paths().count("wp/v2/taxonomies") == 3
    tx.forget(_api(fake))
    tx.discover_taxonomies(_api(fake))
    assert fake.paths().count("wp/v2/taxonomies") == 4
    tx.discover_taxonomies(_api(fake), refresh=True)
    assert fake.paths().count("wp/v2/taxonomies") == 5


def test_edit_context_falls_back_to_the_public_answer() -> None:
    def answer(query):
        return 403 if query.get("context") == ["edit"] else RECORDED["taxonomies"]

    fake = FakeSite({("GET", "wp/v2/taxonomies"): answer})
    assert "product_cat" in tx.discover_taxonomies(_api(fake))
    assert len(fake.seen) == 2


def test_an_unreachable_site_is_a_plain_error_from_discover() -> None:
    with pytest.raises(WordPressApiError):
        tx.discover_taxonomies(_api(FakeSite({("GET", "wp/v2/taxonomies"): 500})))


def test_hierarchical_custom_terms_keep_their_parent_on_update() -> None:
    fake = _recorded_site({
        ("POST", "wp/v2/product_cat/9"): {"id": 9, "name": "Hats", "slug": "hats", "parent": 3},
        ("POST", "wp/v2/product_tag/5"): {"id": 5, "name": "Red", "slug": "red"},
    })
    api = _api(fake)
    wp.update_term(api, wp.Term(9, "product_cat", "Hats", "hats", 0, parent=3))
    wp.update_term(api, wp.Term(5, "product_tag", "Red", "red", 0, parent=3))
    assert fake.bodies[0]["parent"] == 3
    assert "parent" not in fake.bodies[1]


def test_merging_custom_terms_moves_posts_by_the_rest_base_field() -> None:
    fake = FakeSite({
        ("GET", "wp/v2/taxonomies"): {
            "genre": {"slug": "genre", "rest_base": "genres", "types": ["post"]},
        },
        ("GET", "wp/v2/posts"): [{"id": 7, "genres": [1, 2]}],
        ("POST", "batch/v1"): {"responses": [{"status": 200, "body": {}}]},
        ("DELETE", "wp/v2/genres/1"): {"deleted": True},
    })
    assert wp.merge_terms(_api(fake), "genre", 1, 2) == 1
    get_posts = next(q for m, p, q in fake.seen if p == "wp/v2/posts")
    assert get_posts["genres"] == ["1"]
    assert fake.bodies[0]["requests"][0]["body"] == {"genres": [2]}


# --------------------------------------------------------------------------- #
# statuses


def test_statuses_include_the_plugins_own() -> None:
    found = tx.discover_statuses(_api(_recorded_site()))
    assert found["wc-processing"].name == "Processing"
    assert found["tribe-ea-success"].protected
    assert found["private"].private and not found["trash"].show_in_list
    assert found["draft"].date_floating


def test_statuses_are_asked_once_per_connection() -> None:
    fake = _recorded_site()
    tx.discover_statuses(_api(fake))
    tx.discover_statuses(_api(fake))
    assert fake.paths().count("wp/v2/statuses") == 1


def test_parsers_ignore_rows_they_cannot_read() -> None:
    assert tx.parse_taxonomies(["not", "a", "dict"]) == {}
    assert tx.parse_taxonomies({"x": "nope", "y": {"slug": "y"}}) == {}
    assert tx.parse_statuses(None) == {}
    assert list(tx.parse_statuses({"z": {"name": "Zed"}})) == ["z"]


# --------------------------------------------------------------------------- #
# writing types (WP-R-032)


def test_writing_types_are_the_sites_own_with_their_taxonomies() -> None:
    found = stypes.discover_writing_types(_api(_recorded_site()))
    assert [t.slug for t in found] == ["product", "tribe_events", "tribe_venue", "tribe_organizer"]
    events = found[1]
    assert events.kind == "tribe_events" and events.singular == "Event"
    assert events.taxonomies == ("post_tag", "tribe_events_cat")
    # The old tuple shape is unchanged for the callers that use it.
    assert stypes.writing_types(_api(_recorded_site()))[0] == ("product", "product", "Products")


def test_a_type_outside_wp_v2_is_reached_at_its_own_route() -> None:
    fake = FakeSite({
        ("GET", "wp/v2/types"): {
            "book": {
                "slug": "book",
                "name": "Books",
                "rest_base": "books",
                "rest_namespace": "library/v1",
            },
        },
        ("GET", "library/v1/books"): [{"id": 3, "title": {"raw": "Dune"}, "status": "draft"}],
    })
    api = _api(fake)
    (book,) = stypes.discover_writing_types(api)
    assert book.kind == "library/v1/books"
    assert wp.kind_route(book.kind) == "library/v1/books"
    assert [i.title for i in stypes.list_by_status(api, book.kind, "draft")] == ["Dune"]


def test_a_type_lists_by_one_status_including_a_plugins_own() -> None:
    fake = _recorded_site({
        ("GET", "wp/v2/product"): [{"id": 1, "title": {"rendered": "Mug"}, "status": "wc-pending"}],
    })
    items = list(stypes.list_by_status(_api(fake), "product", "wc-pending", search=" mug "))
    assert [i.title for i in items] == ["Mug"]
    query = next(q for _m, p, q in fake.seen if p == "wp/v2/product")
    assert query["status"] == ["wc-pending"] and query["search"] == ["mug"]


def test_counts_by_status_read_the_total_header() -> None:
    def answer(query):
        totals = {"publish": "4", "draft": "1"}
        return _Response([], headers={"X-WP-Total": totals.get(query["status"][0], "0")})

    fake = FakeSite({("GET", "wp/v2/tribe_events"): answer})
    counts = stypes.count_by_status(_api(fake), "tribe_events", ["publish", "draft", "trash"])
    assert counts == {"publish": 4, "draft": 1, "trash": 0}
    assert all(q["per_page"] == ["1"] for _m, _p, q in fake.seen)


def test_counts_skip_a_status_the_site_refuses() -> None:
    def answer(query):
        if query["status"][0] == "private":
            return 400
        return _Response([], headers={"X-WP-Total": "2"})

    fake = FakeSite({("GET", "wp/v2/product"): answer})
    assert stypes.count_by_status(_api(fake), "product", ["publish", "private"]) == {"publish": 2}


def test_statuses_for_a_type_are_the_core_ones_then_the_sites() -> None:
    names = [s for s, _label in stypes.statuses_for(_api(_recorded_site()))]
    assert names[:6] == ["publish", "draft", "pending", "future", "private", "trash"]
    assert "wc-processing" in names and "tribe-ea-success" in names
    assert stypes.statuses_for(_api(FakeSite({("GET", "wp/v2/statuses"): 500})))[0] == (
        "publish",
        "Published",
    )


def test_a_new_item_of_a_custom_type_goes_to_its_route_with_its_terms() -> None:
    fake = _recorded_site({
        ("POST", "wp/v2/tribe_events"): {
            "id": 51,
            "type": "tribe_events",
            "title": {"raw": "Open Mic"},
            "status": "draft",
        },
    })
    api = _api(fake)
    events = next(t for t in stypes.discover_writing_types(api) if t.slug == "tribe_events")
    made = stypes.new_item(api, events, "Open Mic", terms={"tribe_events_cat": [8], "post_tag": []})
    assert made.id == 51 and made.kind == "tribe_events"
    body = fake.bodies[-1]
    assert body["title"] == "Open Mic" and body["status"] == "draft"
    # Terms go by each taxonomy's rest_base: tags, not post_tag.
    assert body["tribe_events_cat"] == [8] and body["tags"] == []
    assert "categories" not in body


def test_type_taxonomies_come_from_the_taxonomies_route() -> None:
    api = _api(_recorded_site())
    product = next(t for t in stypes.discover_writing_types(api) if t.slug == "product")
    assert [t.slug for t in stypes.type_taxonomies(api, product)] == [
        "product_brand",
        "product_cat",
        "product_tag",
    ]
