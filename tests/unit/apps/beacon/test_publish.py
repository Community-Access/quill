"""Tests for the read-only web publish surface (PRD 27.1; plan section 12).

Covers rendering, HTML escaping, the no-URI accessible fallback, slug safety,
publish/unpublish lifecycle, token lookup, and structural accessibility
invariants parsed from the rendered HTML.
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import db, publish
from quill.apps.beacon.model import Beacon, Collection, Resource


def _store(tmp):
    return db.BeaconStore(str(tmp / "beacons.db"))


def _seed(store, title="A", uri="https://x/a", collection="Read", note="", tags=None):
    res = Resource(title=title, type="web", primary_uri=uri)
    b = Beacon(resource_id=res.resource_id, title=title, in_inbox=False, note=note, tags=tags or [])
    b.collections = [collection] if collection else []
    store.put_beacon(b, resource=res)
    return b


# -- slugify -----------------------------------------------------------------


def test_slugify_basic():
    assert publish.slugify("Read Later") == "read-later"
    assert publish.slugify("C++ & Stuff!") == "c-stuff"


def test_slugify_rejects_traversal():
    assert publish.slugify("../evil") is None
    assert publish.slugify("a/b") is None
    assert publish.slugify("a\\b") is None
    assert publish.slugify("   ") is None
    assert publish.slugify("") is None


# -- rendering ---------------------------------------------------------------


def test_render_has_accessibility_structure(tmp_path):
    store = _store(tmp_path)
    col = Collection(name="Read", description="Things to read")
    store.put_collection(col)
    _seed(store, "First", collection="Read")
    _seed(store, "Second", collection="Read")
    beacons = store.list_beacons()
    html = publish.render_collection_html(store, col, beacons, published_at=1700000000)
    assert html.count("<!DOCTYPE html>") == 1
    assert 'lang="en"' in html
    assert 'id="main"' in html
    assert 'href="#main"' in html  # skip link target
    assert html.count("<h1") == 1
    assert html.count("<article>") == 2
    assert html.count("<h2>") == 2
    assert "prefers-reduced-motion" in html
    store.close()


def test_render_escapes_html(tmp_path):
    store = _store(tmp_path)
    col = Collection(name="Read")
    store.put_collection(col)
    _seed(store, "<script>x</script>", note="a & b < c", collection="Read")
    b = store.list_beacons()[0]
    res = store.get_resource(b.resource_id)
    res.title = "<img src=x onerror=alert(1)>"  # hostile resource title
    store.put_resource(res)
    html = publish.render_collection_html(store, col, [b])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img" not in html
    assert "a &amp; b &lt; c" in html
    store.close()


def test_render_no_uri_falls_back_to_text(tmp_path):
    store = _store(tmp_path)
    col = Collection(name="Notes")
    store.put_collection(col)
    # A beacon whose resource has no primary_uri.
    res = Resource(title="Local note", type="note", primary_uri="")
    b = Beacon(resource_id=res.resource_id, title="Local note", in_inbox=False)
    b.collections = ["Notes"]
    store.put_beacon(b, resource=res)
    html = publish.render_collection_html(store, col, [b])
    # No empty <a href=""> link; the title appears as plain text instead.
    assert 'href=""' not in html
    assert "Local note" in html
    store.close()


# -- PublishManager lifecycle ------------------------------------------------


def _mgr(tmp_path):
    store = _store(tmp_path)
    return store, publish.PublishManager(store, tmp_path)


def test_publish_unknown_collection(tmp_path):
    store, mgr = _mgr(tmp_path)
    res = mgr.publish("Nope")
    assert "error" in res
    assert not (tmp_path / "published").exists() or not list((tmp_path / "published").iterdir())
    store.close()


def test_publish_writes_files_and_returns_token(tmp_path):
    store, mgr = _mgr(tmp_path)
    _seed(store, "A", collection="Read")
    res = mgr.publish("Read", port=8752)
    assert res["ok"], res
    assert res["count"] == 1
    assert res["token"]
    assert res["slug"] == "read"
    assert res["preview_url"] == "http://127.0.0.1:8752/published/" + res["token"] + "/"
    assert os.path.exists(res["path"])
    assert (tmp_path / "published" / "read" / "manifest.json").exists()
    manifest = json.loads((tmp_path / "published" / "read" / "manifest.json").read_text())
    assert manifest["name"] == "Read"
    assert manifest["count"] == 1
    listed = mgr.list_published()
    assert len(listed) == 1 and listed[0]["name"] == "Read"
    store.close()


def test_publish_rejects_unsafe_name(tmp_path):
    store, mgr = _mgr(tmp_path)
    # A name with a slash can never be a real collection, but slugify must still
    # refuse before any store call so there is no path-traversal write.
    res = mgr.publish("../evil")
    assert "error" in res
    store.close()


def test_unpublish_removes_folder(tmp_path):
    store, mgr = _mgr(tmp_path)
    _seed(store, "A", collection="Read")
    mgr.publish("Read")
    assert mgr.is_published("Read")
    res = mgr.unpublish("Read")
    assert res["ok"]
    assert not mgr.is_published("Read")
    # Second unpublish is "not published", not an error-raising path.
    res2 = mgr.unpublish("Read")
    assert "error" in res2
    store.close()


def test_get_by_token(tmp_path):
    store, mgr = _mgr(tmp_path)
    _seed(store, "A", collection="Read")
    res = mgr.publish("Read")
    found = mgr.get_by_token(res["token"])
    assert found is not None
    assert found["slug"] == "read"
    assert os.path.exists(found["html_path"])
    assert mgr.get_by_token("wrong-token") is None
    assert mgr.get_by_token("") is None
    store.close()


def test_republish_rotates_token(tmp_path):
    store, mgr = _mgr(tmp_path)
    _seed(store, "A", collection="Read")
    t1 = mgr.publish("Read")["token"]
    t2 = mgr.publish("Read")["token"]
    assert t1 != t2
    # Old token no longer valid; new one is.
    assert mgr.get_by_token(t1) is None
    assert mgr.get_by_token(t2) is not None
    store.close()


def test_top_index_lists_collections(tmp_path):
    store, mgr = _mgr(tmp_path)
    _seed(store, "A", collection="Read")
    _seed(store, "B", collection="Watch")
    mgr.publish("Read")
    mgr.publish("Watch")
    idx = (tmp_path / "published" / "index.html").read_text()
    assert "Read" in idx and "Watch" in idx
    assert 'href="read/"' in idx
    store.close()


# -- structural accessibility invariants --------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def _links_with_text(html_str):
    """Return list of (href, text) for every <a> in the page."""
    out = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html_str, re.S):
        attrs = m.group(1)
        text = _TAG_RE.sub("", m.group(2)).strip()
        href = re.search(r'href="([^"]*)"', attrs)
        out.append((href.group(1) if href else "", text))
    return out


def test_a11y_every_link_has_text_and_headings_nested(tmp_path):
    store = _store(tmp_path)
    col = Collection(name="Read", description="d")
    store.put_collection(col)
    _seed(store, "First", collection="Read", note="why", tags=["t1", "t2"])
    _seed(store, "Second", collection="Read")
    html = publish.render_collection_html(store, col, store.list_beacons())
    # Every link has non-empty text (no bare-URL or empty link text).
    for href, text in _links_with_text(html):
        assert text, f"link {href!r} has no accessible text"
    # Heading order: h1 appears before any h2.
    assert html.index("<h1") < html.index("<h2")
    # Exactly one h1.
    assert len(re.findall(r"<h1\b", html)) == 1
    store.close()
