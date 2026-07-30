"""Full-text article fetch: extraction, sanitizing, enrichment, refresh wiring."""

from __future__ import annotations

from quill_social.db import SocialStore
from quill_social.model import SocialItem
from quill_social.services import feed_refresh, full_text
from quill_social.services import subscriptions as subs_svc

ARTICLE_HTML = b"""<html><head><title>x</title>
<style>.a{color:red}</style></head>
<body>
  <nav>Home About <a href="/login">Log in</a></nav>
  <header>Site banner</header>
  <article>
    <h1>The Real Headline</h1>
    <p>First paragraph of the <b>actual</b> article.</p>
    <p>Second paragraph with a <a href="https://ex.example/more">link</a>.</p>
    <aside>Related junk you should not see</aside>
  </article>
  <footer>Copyright boilerplate</footer>
  <script>tracker()</script>
</body></html>
"""


def test_balanced_region_handles_nesting():
    html = "<article>outer <article>inner</article> tail</article> after"
    start, end = full_text._balanced_region(html, "article")
    assert html[start:end] == "<article>outer <article>inner</article> tail</article>"


def test_extract_main_prefers_article_and_strips_chrome():
    html = ARTICLE_HTML.decode()
    main = full_text.extract_main_html(html)
    assert "actual" in main
    assert "Related junk" not in main  # aside stripped
    assert "About" not in main  # nav was outside <article>


def test_fetch_full_text_returns_sanitized_article():
    text = full_text.fetch_full_text("https://ex.example/post", fetch=lambda url: ARTICLE_HTML)
    assert "First paragraph of the actual article." in text
    assert "tracker()" not in text  # script content dropped by the sanitizer
    assert "Related junk" not in text  # aside stripped by the extractor
    assert "https://ex.example/more" in text  # link url inlined for a11y


def test_fetch_full_text_empty_url_returns_empty():
    assert full_text.fetch_full_text("", fetch=lambda url: ARTICLE_HTML) == ""


def test_enrich_item_text_swaps_body_keeps_title():
    combined = "The Headline\n\nshort summary"
    out = full_text.enrich_item_text(combined, "a much longer full article body here")
    assert out == "The Headline\n\na much longer full article body here"


def test_enrich_item_text_keeps_original_when_no_better():
    combined = "Title\n\nalready the full thing is quite long here"
    assert full_text.enrich_item_text(combined, "") == combined  # nothing fetched
    assert full_text.enrich_item_text(combined, "short") == combined  # shorter -> keep


class _FakeAdapter:
    def __init__(self, entries):
        self._entries = entries  # (remote_id, uri, text)

    def home_timeline(self, *, limit=40, since_id=""):
        return [SocialItem(network="rss", remote_id=r, uri=u, text=t) for r, u, t in self._entries]


def _store(tmp_path):
    return SocialStore(tmp_path / "s.db")


def test_refresh_enriches_new_entries_when_full_text_on(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.full_text = True
    subs_svc.save_subscription(store, sub)
    adapter = _FakeAdapter([("e1", "https://a.example/1", "Headline\n\nteaser")])
    feed_refresh.refresh_feed(
        store,
        sub,
        adapter,
        now=100,
        full_text_fetch=lambda url: "the complete article text, much longer than the teaser",
    )
    item = store.list_items(account_id=sub.account_id)[0]
    assert "complete article text" in item.text
    assert item.text.startswith("Headline")  # title preserved
    store.close()


def test_refresh_full_text_failure_keeps_summary(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.full_text = True
    subs_svc.save_subscription(store, sub)

    def boom(url):
        raise RuntimeError("network down")

    adapter = _FakeAdapter([("e1", "https://a.example/1", "Headline\n\nteaser")])
    new = feed_refresh.refresh_feed(store, sub, adapter, now=100, full_text_fetch=boom)
    assert new == 1  # still stored and counted
    item = store.list_items(account_id=sub.account_id)[0]
    assert item.text == "Headline\n\nteaser"  # summary intact
    store.close()


def test_refresh_no_full_text_never_fetches(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")  # full_text default False

    def boom(url):
        raise AssertionError("must not fetch when full_text is off")

    adapter = _FakeAdapter([("e1", "https://a.example/1", "Headline\n\nteaser")])
    feed_refresh.refresh_feed(store, sub, adapter, now=100, full_text_fetch=boom)
    store.close()
