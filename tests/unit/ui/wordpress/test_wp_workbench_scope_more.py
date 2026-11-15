"""Convert to Block, synced patterns, a plugin's blocks, Merge and Remove Everywhere (15.12).

WP-R-043 and WP-R-044 in the real frame, on the fake site of the Workbench
window tests: every change previewed, sent, said, and undone where it can be.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.workbench_across import SiteScan  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE  # noqa: E402

bench = _bench


def _scan(bench, first: str, second: str = "") -> SiteScan:
    scan = SiteScan(SITE)
    scan.items = [dict(p) for p in bench.api.posts]
    scan.items[0]["content"] = {"raw": first}
    scan.items[1]["content"] = {"raw": second}
    scan.patterns = {7: "Footer"}
    bench.provider.__dict__.setdefault("_scans", {})[SITE] = (time.time(), scan)
    return scan


def _previews(monkeypatch, answer: bool = True) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **k: (seen.append(k), answer)[1])
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: seen.append(k))
    return seen


def _value(kind: str, value: str, count: int = 0) -> WbRow:
    return WbRow("value", SITE, value, {"value": value, "count": str(count)}, "", subkind=kind)


def test_convert_a_shortcode_to_its_block_on_the_checked_items_and_undo(bench, monkeypatch) -> None:
    _scan(bench, '[audio mp3="https://radio.example/a.mp3"]', '[audio src="x.mp3"]')
    seen = _previews(monkeypatch)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [0])
    bench.provider.do_convert_shortcode(None, _value("blocks", "[audio] shortcode"))
    assert seen[0]["lines"] == [f"{SITE}: Hello: 1 [audio] use becomes the audio block"]
    method, route, body = bench.api.writes[-1]
    assert (method, route) == ("POST", "wp/v2/posts/1")
    assert '<audio controls src="https://radio.example/a.mp3"></audio>' in body["content"]
    assert len(bench.api.writes) == 1  # the unchecked item is left alone
    assert bench.provider.history.undo() == "Put 1 back as they were."
    assert bench.api.writes[-1][2] == {"content": '[audio mp3="https://radio.example/a.mp3"]'}


def test_a_shortcode_with_no_block_says_so_and_a_cancelled_preview_sends_nothing(
    bench, monkeypatch
) -> None:
    _scan(bench, '[playlist ids="1"] [gallery ids="1"]')
    _previews(monkeypatch, answer=False)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [0])
    bench.provider.do_convert_shortcode(None, _value("blocks", "[playlist] shortcode"))
    assert "no core playlist block" in bench.said[-1]
    bench.provider.do_convert_shortcode(None, _value("links", "https://x.example"))
    assert bench.said[-1] == "Only a shortcode has a block to become."
    bench.provider.__dict__["_scans"][SITE][1].media = [
        {"id": 1, "source_url": "https://radio.example/1.jpg"}
    ]
    bench.provider.do_convert_shortcode(None, _value("blocks", "[gallery] shortcode"))
    assert bench.api.writes == []


def test_update_a_synced_pattern_once_and_undo(bench, monkeypatch) -> None:
    _scan(bench, '<!-- wp:block {"ref":7} /-->')
    seen = _previews(monkeypatch)
    pattern = {
        "id": 7,
        "title": {"raw": "Footer"},
        "content": {"raw": "<p>old</p>"},
        "modified_gmt": "2026-10-01T00:00:00",
    }
    get = bench.api.get
    monkeypatch.setattr(
        bench.api,
        "get",
        lambda route, **kw: dict(pattern) if route == "wp/v2/blocks/7" else get(route, **kw),
    )
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "<p>new</p>")
    bench.provider.do_update_pattern(None, _value("patterns", "Footer", 1))
    assert "the page placing it show" in seen[0]["lines"][0]
    assert bench.api.writes[-1] == ("POST", "wp/v2/blocks/7", {"content": "<p>new</p>"})
    bench.provider.history.undo()
    assert bench.api.writes[-1] == ("POST", "wp/v2/blocks/7", {"content": "<p>old</p>"})


def test_detach_a_pattern_on_the_checked_pages(bench, monkeypatch) -> None:
    _scan(bench, '<!-- wp:block {"ref":7} /-->', '<p>a</p><!-- wp:block {"ref":7} /-->')
    seen = _previews(monkeypatch)
    get = bench.api.get
    blocks = {"id": 7, "content": {"raw": "<!-- wp:paragraph --><p>Footer</p>"}}
    monkeypatch.setattr(
        bench.api,
        "get",
        lambda route, **kw: dict(blocks) if route == "wp/v2/blocks/7" else get(route, **kw),
    )
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [1])
    bench.provider.do_detach_pattern(None, _value("patterns", "Footer", 2))
    assert seen[0]["lines"] == [
        f"{SITE}: News: Footer becomes its own blocks here, no longer synced"
    ]
    assert bench.api.writes == [
        ("POST", "wp/v2/posts/2", {"content": "<p>a</p><!-- wp:paragraph --><p>Footer</p>"})
    ]
    assert bench.provider.history.can_undo()


def test_pages_using_a_plugins_blocks_are_listed_from_its_row(bench, monkeypatch) -> None:
    _scan(bench, '<!-- wp:jetpack/slideshow {"ids":[1]} /-->', "<!-- wp:paragraph -->")
    seen = _previews(monkeypatch)
    row = WbRow(
        "plugin",
        SITE,
        "jetpack/jetpack",
        {"plugin": "Jetpack"},
        "",
        raw={"plugin": "jetpack/jetpack", "textdomain": "jetpack"},
    )
    bench.provider.do_plugin_block_uses(None, row)
    assert bench.said[-1] == f"1 pages on {SITE} use blocks from jetpack."
    assert "Hello: jetpack/slideshow" in seen[0]["text"]
    bench.provider.do_plugin_block_uses(None, _value("blocks", "paragraph block"))
    assert "core block" in bench.said[-1]
    assert bench.api.writes == []


def _across(kind: str, key: str, objects: dict[str, Any]) -> WbRow:
    variants = {"slug news": list(objects)}
    raw = {"variants": variants, "missing": [], "objects": objects}
    return WbRow("across", "", key, {}, "", subkind=kind, raw=raw)


def test_merge_a_term_everywhere_moves_posts_then_deletes_it(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    monkeypatch.setattr(dlg, "ask_text", lambda *a, **k: "Shows")
    walk = bench.api.iter_collection

    def iter_collection(route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/categories":
            yield {"id": 6, "name": "Shows"}
        else:
            yield from walk(route, params, **kw)

    monkeypatch.setattr(bench.api, "iter_collection", iter_collection)
    bench.api.posts[0]["categories"] = [5]
    bench.api.posts[1]["categories"] = [5, 9]
    row = _across("terms", "News (category)", {SITE: {"id": 5, "slug": "news", "count": 2}})
    bench.provider.do_merge_everywhere(None, row)
    assert "cannot be undone" in seen[0]["summary"]
    assert [w[:2] for w in bench.api.writes] == [
        ("POST", "wp/v2/posts/1"),
        ("POST", "wp/v2/posts/2"),
        ("DELETE", "wp/v2/categories/5"),
    ]
    assert bench.api.writes[1][2] == {"categories": [9, 6]}
    assert "merged into Shows on 1 of 1 sites" in bench.said[-1]
    assert not bench.provider.history.can_undo()


def test_remove_a_redirect_everywhere_after_a_destructive_preview(bench, monkeypatch) -> None:
    seen = _previews(monkeypatch)
    row = _across("redirects", "/old", {SITE: {"id": 5, "url": "/old"}})
    bench.provider.do_remove_everywhere(None, row)
    assert seen[0]["destructive"] is True and "cannot be undone" in seen[0]["summary"]
    assert bench.api.writes == [("POST", "redirection/v1/bulk/redirect/delete", {"items": [5]})]
    bench.provider.do_remove_everywhere(None, _across("forms", "Contact", {SITE: {"id": 1}}))
    assert "delete it in Forms on each site" in bench.said[-1]
    assert len(bench.api.writes) == 1
