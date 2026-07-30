"""Per-feed keyword filters: matcher, decision order, and refresh wiring."""

from __future__ import annotations

from quill_social.db import SocialStore
from quill_social.model import SocialItem
from quill_social.services import feed_filters, feed_refresh
from quill_social.services import subscriptions as subs_svc


def _item(remote_id, text):
    return SocialItem(network="rss", remote_id=remote_id, text=text)


def test_keyword_matches_is_case_insensitive():
    it = _item("1", "Big SALE on widgets today")
    assert feed_filters.keyword_matches(it, "sale")
    assert feed_filters.keyword_matches(it, "WIDGETS")
    assert not feed_filters.keyword_matches(it, "clearance")
    assert not feed_filters.keyword_matches(it, "")


def test_decide_first_match_wins():
    it = _item("1", "spoilers ahead about the finale")
    rules = [
        {"keyword": "finale", "action": "star"},
        {"keyword": "spoilers", "action": "hide"},
    ]
    assert feed_filters.decide(it, rules) == "star"  # first rule wins


def test_decide_skips_malformed_rules():
    it = _item("1", "sponsored content here")
    rules = [
        {"keyword": "sponsored", "action": "bogus"},  # unknown action -> skip
        {"keyword": "", "action": "hide"},  # empty keyword -> skip
        "not a dict",
        {"keyword": "sponsored", "action": "mark_read"},
    ]
    assert feed_filters.decide(it, rules) == "mark_read"


def test_decide_no_match_returns_empty():
    assert feed_filters.decide(_item("1", "hello"), [{"keyword": "x", "action": "hide"}]) == ""
    assert feed_filters.decide(_item("1", "hello"), []) == ""


class _FakeAdapter:
    def __init__(self, entries):
        self._entries = entries  # list of (remote_id, text)

    def home_timeline(self, *, limit=40, since_id=""):
        return [SocialItem(network="rss", remote_id=r, text=t) for r, t in self._entries]


def _store(tmp_path):
    return SocialStore(tmp_path / "s.db")


def test_refresh_hide_action_drops_entry(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.filters = [{"keyword": "sponsored", "action": "hide"}]
    subs_svc.save_subscription(store, sub)
    adapter = _FakeAdapter([("e1", "real news"), ("e2", "sponsored post")])
    new = feed_refresh.refresh_feed(store, sub, adapter, now=100)
    remaining = {i.remote_id for i in store.list_items(account_id=sub.account_id)}
    assert remaining == {"e1"}  # sponsored entry never stored
    assert new == 1  # only the kept entry counts as new
    store.close()


def test_refresh_mark_read_action_presets_read(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.filters = [{"keyword": "digest", "action": "mark_read"}]
    subs_svc.save_subscription(store, sub)
    adapter = _FakeAdapter([("e1", "weekly digest"), ("e2", "breaking")])
    new = feed_refresh.refresh_feed(store, sub, adapter, now=100)
    assert new == 1  # the digest is pre-read, not announced
    assert store.count_unread(sub.account_id) == 1  # only e2 unread
    store.close()


def test_refresh_star_action_flags_entry(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.filters = [{"keyword": "urgent", "action": "star"}]
    subs_svc.save_subscription(store, sub)
    adapter = _FakeAdapter([("e1", "urgent recall notice")])
    feed_refresh.refresh_feed(store, sub, adapter, now=100)
    items = store.list_items(account_id=sub.account_id)
    assert len(items) == 1
    assert items[0].flagged is True
    store.close()


def test_filters_survive_subscription_roundtrip(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.filters = [{"keyword": "x", "action": "hide"}]
    sub.notify = False
    sub.full_text = True
    subs_svc.save_subscription(store, sub)
    reloaded = subs_svc.get_subscription(store, sub.account_id)
    assert reloaded.filters == [{"keyword": "x", "action": "hide"}]
    assert reloaded.notify is False
    assert reloaded.full_text is True
    store.close()
