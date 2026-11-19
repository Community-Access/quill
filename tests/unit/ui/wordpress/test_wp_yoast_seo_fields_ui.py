"""Yoast SEO's canonical address, primary category and schema type on a post's Properties.

The real provider on a fake site with ``yoast/v1``: where the site registers
Yoast's meta for REST, the SEO page edits it and a save sends only that meta;
where it does not, the page shows what ``yoast_head_json`` says, read only,
with the sentence that sends the person to the post's Yoast panel, and Open
in wp-admin on the SEO row opens the post's editor. Recorded-shape answers
only; no live site.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_edit import body_for  # noqa: E402
from quill.core.wordpress.workbench_rows import item_row  # noqa: E402
from quill.core.wordpress.workbench_seo import seo_row  # noqa: E402
from quill.core.workbench.properties import FieldChange  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)

_HEAD = {
    "title": "Hello - Radio",
    "canonical": "https://radio.example/hello/",
    "schema": {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "@id": "https://radio.example/hello/#article"},
            {"@type": ["WebPage", "FAQPage"], "@id": "https://radio.example/hello/"},
            {"@type": "BreadcrumbList", "@id": "https://radio.example/hello/#breadcrumb"},
        ],
    },
}

_REGISTERED = {
    "_yoast_wpseo_canonical": {"type": "string"},
    "_yoast_wpseo_primary_category": {"type": "string"},
    "_yoast_wpseo_schema_page_type": {"type": "string"},
    "_yoast_wpseo_schema_article_type": {"type": "string"},
    "_yoast_wpseo_title": {"type": "string"},
}


class _Options:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.total = 0


class YoastApi(FakeApi):
    """A site with Yoast SEO; *registered* says whether its four meta fields are in REST."""

    def __init__(self, *, registered: bool) -> None:
        super().__init__()
        self.registered = registered
        self.posts[0]["yoast_head_json"] = dict(_HEAD)
        if registered:
            self.posts[0]["meta"] = {
                "_yoast_wpseo_canonical": "",
                "_yoast_wpseo_primary_category": "",
                "_yoast_wpseo_schema_page_type": "",
                "_yoast_wpseo_schema_article_type": "",
                "_yoast_wpseo_title": "",
            }

    def get(self, route: str, **params: Any) -> Any:
        if route == "":
            answer = dict(super().get(route, **params))
            answer["namespaces"] = ["wp/v2", "yoast/v1"]
            return answer
        return super().get(route, **params)

    def request(self, method: str, route: str, **kw: Any) -> Any:
        if method == "OPTIONS" and route == "wp/v2/posts":
            meta = dict(_REGISTERED) if self.registered else {}
            return _Options({"schema": {"properties": {"meta": {"properties": meta}}}})
        return super().request(method, route, **kw)


def _bench(api: YoastApi, tmp_path: Any) -> WorkbenchFrame:
    said: list[str] = []
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    return frame


@pytest.fixture
def make(wx_session_app, tmp_path):
    frames: list[WorkbenchFrame] = []

    def build(*, registered: bool) -> WorkbenchFrame:
        tx.clear_cache()
        frame = _bench(YoastApi(registered=registered), tmp_path)
        frames.append(frame)
        return frame

    yield build
    for frame in frames:
        frame.frame.Destroy()
    tx.clear_cache()


def test_unregistered_fields_are_read_only_from_what_yoast_tells_search_engines(make) -> None:
    bench = make(registered=False)
    row = item_row(bench.api.posts[0], "post", SITE)
    sheet, values, *_rest = bench.provider._load_sheet(row)
    page = next(p for p in sheet.pages if p.key == "seo")
    assert [f.label for f in page.fields] == [
        "Canonical address",
        "Primary category",
        "Schema page type",
        "Schema article type",
        "Where these change",
    ]
    assert all(f.readonly for f in page.fields)
    assert values["yoast._yoast_wpseo_canonical"] == "https://radio.example/hello/"
    assert values["yoast._yoast_wpseo_schema_page_type"] == "FAQ page"
    assert values["yoast._yoast_wpseo_schema_article_type"] == "Article"
    assert "its categories: Shows" in str(values["yoast._yoast_wpseo_primary_category"])
    where = str(values["yoast.where"])
    assert "changed in this post's Yoast panel in wp-admin" in where
    assert "Open in wp-admin" in where
    assert where.count(".") == 1  # one plain sentence


def test_registered_fields_are_edited_and_saved_as_meta(make) -> None:
    bench = make(registered=True)
    row = item_row(bench.api.posts[0], "post", SITE)
    sheet, values, _fresh, _names, meta = bench.provider._load_sheet(row)
    page = next(p for p in sheet.pages if p.key == "seo")
    assert not any(f.readonly for f in page.fields)
    assert "yoast.where" not in values
    meta_page = next((p for p in sheet.pages if p.key == "meta"), None)
    moved = {f.key for f in meta_page.fields} if meta_page else set()
    assert "meta._yoast_wpseo_canonical" not in moved  # moved, not shown twice
    primary = sheet.field("meta._yoast_wpseo_primary_category")
    assert primary.choices == ("", "5")
    assert primary.choice_words[1] == "Shows (5)"
    page_type = sheet.field("meta._yoast_wpseo_schema_page_type")
    assert page_type.word_for("FAQPage") == "FAQ page"
    body = body_for(
        sheet,
        row,
        [
            FieldChange("meta._yoast_wpseo_primary_category", "Primary category", "", "5"),
            FieldChange(
                "meta._yoast_wpseo_canonical",
                "Canonical address",
                "",
                "https://radio.example/main/",
            ),
        ],
        meta_schema=meta,
    )
    assert body == {
        "meta": {
            "_yoast_wpseo_primary_category": "5",
            "_yoast_wpseo_canonical": "https://radio.example/main/",
        }
    }


def test_properties_on_an_seo_row_opens_the_post_sheet(make, monkeypatch) -> None:
    bench = make(registered=False)
    seo = seo_row(bench.api.posts[0], SITE)
    loaded: list[Any] = []

    def background(_name: str, work: Any, _done: Any, *_a: Any, **_k: Any) -> None:
        loaded.append(work)

    monkeypatch.setattr(bench.provider, "background", background)
    monkeypatch.setattr(bench.provider, "_load_sheet", lambda r: r)
    bench.provider._one_sheet(seo)
    row = loaded[0]()
    assert row.kind == "item" and row.route == "wp/v2/posts/1" and row.subkind == "post"


def test_open_in_wp_admin_on_an_seo_row_opens_the_post_editor(make) -> None:
    bench = make(registered=False)
    seo = seo_row(bench.api.posts[0], SITE)
    bench.provider.do_dashboard_screen(None, seo)
    assert bench.commands.host.opened == [
        "https://radio.example/wp-admin/post.php?post=1&action=edit"
    ]
    assert "Yoast panel" in bench.said[-1]
