"""Tests for offline resilience: outbox, revalidation, and breakers (PRD 32)."""

from quill_social.capabilities import Capabilities
from quill_social.services.outbox import (
    CircuitBreaker,
    Outbox,
    OutboxItem,
    backoff,
    on_reconnect,
)


def test_enqueue_list_remove(store):
    ob = Outbox(store)
    item = OutboxItem(account_id="a1", network="mock", text="hi", created=100)
    ob.enqueue(item)
    listed = ob.list()
    assert len(listed) == 1
    assert listed[0].outbox_id == item.outbox_id
    assert listed[0].text == "hi"
    ob.remove(item.outbox_id)
    assert ob.list() == []


def test_outbox_roundtrip():
    item = OutboxItem(account_id="a1", network="mastodon", text="body",
                      privacy="followers", send_mode="scheduled", expiration=500)
    assert OutboxItem.from_dict(item.to_dict()) == item


def test_list_preserves_order(store):
    ob = Outbox(store)
    for i in range(3):
        ob.enqueue(OutboxItem(account_id="a1", text=f"m{i}", created=100 + i))
    assert [it.text for it in ob.list()] == ["m0", "m1", "m2"]


def test_expired_timing_is_held_not_published():
    item = OutboxItem(account_id="a1", text="late", expiration=500)
    caps = Capabilities(char_limit=500)
    [res] = on_reconnect([item], lambda _it: caps, now=1000)
    assert res.expired
    assert res.needs_review
    assert res.item.validation_status == "expired"
    assert any("intended time" in w for w in res.warnings)


def test_capability_change_warns():
    item = OutboxItem(account_id="a1", text="x" * 40)
    tight = Capabilities(char_limit=10)
    [res] = on_reconnect([item], lambda _it: tight, now=1000)
    assert res.needs_review
    assert any("character limit changed" in w for w in res.warnings)
    assert res.item.validation_status == "warn"


def test_reply_reference_refresh_warning():
    item = OutboxItem(account_id="a1", text="reply", thread_dependency="plan_1")
    caps = Capabilities(char_limit=500)
    [res] = on_reconnect([item], lambda _it: caps, now=1000)
    assert any("reply reference" in w for w in res.warnings)


def test_valid_item_marked_valid():
    item = OutboxItem(account_id="a1", text="fine", privacy="public")
    caps = Capabilities(char_limit=500)
    [res] = on_reconnect([item], lambda _it: caps, now=1000)
    assert not res.needs_review
    assert res.item.validation_status == "valid"


def test_on_reconnect_preserves_order():
    items = [OutboxItem(account_id="a1", text=f"m{i}", created=i) for i in range(4)]
    caps = Capabilities(char_limit=500)
    results = on_reconnect(items, lambda _it: caps, now=10)
    assert [r.item.text for r in results] == ["m0", "m1", "m2", "m3"]


def test_backoff_grows_and_caps():
    assert backoff(0) == 30_000
    assert backoff(1) == 60_000
    assert backoff(2) == 120_000
    assert backoff(99) == 3_600_000


def test_circuit_breaker_opens_after_threshold_and_half_opens():
    cb = CircuitBreaker(service="mastodon", failure_threshold=3, cooldown_ms=100)
    assert cb.allow(now=0)
    for _ in range(3):
        cb.record_failure(now=0)
    assert cb.state == "open"
    assert not cb.allow(now=50)  # still cooling down
    assert cb.allow(now=100)  # cooldown elapsed -> trial allowed
    assert cb.state == "half_open"
    cb.record_success(now=110)
    assert cb.state == "closed"
    assert cb.failures == 0


def test_circuit_breaker_reopens_on_half_open_failure():
    cb = CircuitBreaker(service="bluesky", failure_threshold=1, cooldown_ms=100)
    cb.record_failure(now=0)
    assert cb.state == "open"
    assert cb.allow(now=100)
    assert cb.state == "half_open"
    cb.record_failure(now=105)
    assert cb.state == "open"
    assert not cb.allow(now=150)
