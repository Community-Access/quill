"""Feed refresh scheduling: due selection and re-fetch with new-count."""

from __future__ import annotations

from quill_social.db import SocialStore
from quill_social.model import SocialItem
from quill_social.services import feed_refresh
from quill_social.services import subscriptions as subs_svc
from quill_social.services.subscriptions import Subscription


def _store(tmp_path):
    return SocialStore(tmp_path / "s.db")


def test_due_subscriptions_selects_by_interval():
    now = 10_000_000
    never = Subscription(account_id="a", feed_url="u1", last_fetched=0, refresh_interval_s=900)
    fresh = Subscription(
        account_id="b", feed_url="u2", last_fetched=now - 60_000, refresh_interval_s=900
    )
    stale = Subscription(
        account_id="c", feed_url="u3", last_fetched=now - 2_000_000, refresh_interval_s=900
    )
    manual = Subscription(account_id="d", feed_url="u4", last_fetched=0, refresh_interval_s=0)
    due = feed_refresh.due_subscriptions([never, fresh, stale, manual], now=now)
    ids = {s.account_id for s in due}
    assert ids == {"a", "c"}  # never-fetched + stale; fresh + manual excluded


class _FakeAdapter:
    def __init__(self, remote_ids):
        self._remote_ids = remote_ids

    def home_timeline(self, *, limit=40, since_id=""):
        return [SocialItem(network="rss", remote_id=r, text=f"item {r}") for r in self._remote_ids]


def test_refresh_due_drives_all_due_feeds(tmp_path):
    store = _store(tmp_path)
    a = subs_svc.subscribe(store, "https://a.example/feed")
    b = subs_svc.subscribe(store, "https://b.example/feed")
    b.notify = False  # b refreshes but is not counted in the announced total
    subs_svc.save_subscription(store, b)
    adapters = {
        a.account_id: _FakeAdapter(["a1", "a2"]),
        b.account_id: _FakeAdapter(["b1"]),
    }
    subs = subs_svc.list_subscriptions(store)
    total = feed_refresh.refresh_due(store, subs, lambda aid: adapters[aid], now=1000)
    assert total == 2  # only a's new items counted (b has notify off)
    assert store.count_unread(a.account_id) == 2
    assert store.count_unread(b.account_id) == 1  # still refreshed
    store.close()


def test_refresh_due_isolates_a_failing_feed(tmp_path):
    store = _store(tmp_path)
    good = subs_svc.subscribe(store, "https://good.example/feed")
    bad = subs_svc.subscribe(store, "https://bad.example/feed")

    class _Boom:
        def home_timeline(self, *, limit=40, since_id=""):
            raise RuntimeError("feed down")

    adapters = {good.account_id: _FakeAdapter(["g1"]), bad.account_id: _Boom()}
    subs = subs_svc.list_subscriptions(store)
    total = feed_refresh.refresh_due(store, subs, lambda aid: adapters[aid], now=1000)
    assert total == 1  # good feed still delivered
    # The failing feed was backed off (last_fetched stamped) so it isn't retried instantly.
    assert subs_svc.get_subscription(store, bad.account_id).last_fetched == 1000
    store.close()


def test_refresh_feed_counts_new_and_stamps(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    adapter = _FakeAdapter(["e1", "e2"])
    now = 5_000_000
    new = feed_refresh.refresh_feed(store, sub, adapter, now=now)
    assert new == 2
    assert store.count_unread(sub.account_id) == 2
    reloaded = subs_svc.get_subscription(store, sub.account_id)
    assert reloaded.last_fetched == now

    # Second refresh with one overlapping + one new -> only the new one counts.
    adapter2 = _FakeAdapter(["e2", "e3"])
    assert feed_refresh.refresh_feed(store, reloaded, adapter2, now=now + 1) == 1
    store.close()


class _FakePoller:
    """A conditional-GET adapter: returns 304 or fresh items, tracking validators."""

    def __init__(self, poll_result):
        self._poll_result = poll_result
        self.seen = {}

    def poll(self, *, etag="", last_modified="", limit=60):
        self.seen = {"etag": etag, "last_modified": last_modified}
        return self._poll_result


class _Poll:
    def __init__(self, *, items=None, etag="", last_modified="", not_modified=False):
        self.items = items or []
        self.etag = etag
        self.last_modified = last_modified
        self.not_modified = not_modified


def test_refresh_feed_uses_conditional_poll_and_persists_validators(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    items = [SocialItem(network="rss", remote_id="e1", text="one")]
    poller = _FakePoller(
        _Poll(items=items, etag='"v1"', last_modified="Mon, 01 Jan 2026 00:00:00 GMT")
    )
    assert feed_refresh.refresh_feed(store, sub, poller, now=100) == 1
    reloaded = subs_svc.get_subscription(store, sub.account_id)
    assert reloaded.etag == '"v1"'
    assert reloaded.last_modified == "Mon, 01 Jan 2026 00:00:00 GMT"
    assert reloaded.last_fetched == 100
    store.close()


def test_refresh_feed_applies_per_feed_retention(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.retention_days = 1
    subs_svc.save_subscription(store, sub)
    feed_refresh.refresh_feed(store, sub, _FakeAdapter(["e1", "e2"]), now=100)
    # Age the just-upserted rows so retention can consider them.
    store.conn.execute("UPDATE items SET fetched_at=0")
    store.conn.commit()
    # A subsequent refresh brings one new entry and prunes the two stale ones.
    feed_refresh.refresh_feed(store, sub, _FakeAdapter(["e3"]), now=200)
    remaining = {i.remote_id for i in store.list_items(account_id=sub.account_id)}
    assert remaining == {"e3"}  # e1/e2 pruned by retention, e3 fresh
    store.close()


def test_retention_days_survives_subscription_roundtrip(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.retention_days = 14
    subs_svc.save_subscription(store, sub)
    assert subs_svc.get_subscription(store, sub.account_id).retention_days == 14
    store.close()


def test_refresh_feed_304_skips_parsing_and_counts_zero(tmp_path):
    store = _store(tmp_path)
    sub = subs_svc.subscribe(store, "https://a.example/feed")
    sub.etag = '"cached"'
    subs_svc.save_subscription(store, sub)
    # A 304 poll: no items, validators echoed back.
    poller = _FakePoller(_Poll(etag='"cached"', not_modified=True))
    new = feed_refresh.refresh_feed(store, sub, poller, now=200)
    assert new == 0
    assert poller.seen["etag"] == '"cached"'  # sent the stored validator
    reloaded = subs_svc.get_subscription(store, sub.account_id)
    assert reloaded.last_fetched == 200
    assert reloaded.etag == '"cached"'
    assert store.count_unread(sub.account_id) == 0
    store.close()
