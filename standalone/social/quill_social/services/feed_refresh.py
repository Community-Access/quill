"""Scheduled feed auto-refresh (plan xxx.md 1.5, 3.9).

Pure scheduling logic the shell drives from its timer: pick the subscriptions
whose per-feed interval has elapsed, re-fetch each, upsert new entries (the store
preserves read/flagged state on re-fetch), and stamp ``last_fetched``. A feed
with ``refresh_interval_s <= 0`` is manual-only and never auto-refreshes. The
runner returns the count of genuinely *new* entries so the shell can announce it
politely -- without stealing focus (plan xxx.md 3.10.7).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from quill_social.db import SocialStore
from quill_social.model import SocialItem
from quill_social.services import feed_filters
from quill_social.services.subscriptions import Subscription, save_subscription

# The most articles a single full-text-enabled refresh will fetch, so a large
# backlog of new entries can never turn one tick into an unbounded crawl.
_MAX_FULLTEXT_PER_REFRESH = 20

# A full-text fetch takes an article URL and returns its readable plain text.
FullTextFetch = Callable[[str], str]


class _Adapter(Protocol):
    def home_timeline(self, *, limit: int = 40, since_id: str = "") -> list[SocialItem]: ...


@runtime_checkable
class _Poller(Protocol):
    """An adapter that supports conditional polling (RSS conditional GET)."""

    def poll(self, *, etag: str = "", last_modified: str = "", limit: int = 60) -> object: ...


def due_subscriptions(subs: list[Subscription], *, now: int) -> list[Subscription]:
    """Subscriptions whose refresh interval has elapsed (never-fetched = due).

    A ``refresh_interval_s`` of 0 (or less) means manual-only and never auto-refreshes.
    """
    out: list[Subscription] = []
    for sub in subs:
        interval = sub.refresh_interval_s
        if interval <= 0:
            continue  # manual-only
        if sub.last_fetched <= 0 or now - sub.last_fetched >= interval * 1000:
            out.append(sub)
    return out


def refresh_feed(
    store: SocialStore,
    sub: Subscription,
    adapter: _Adapter,
    *,
    now: int,
    full_text_fetch: FullTextFetch | None = None,
) -> int:
    """Re-fetch one feed, upsert entries, stamp ``last_fetched``; return new count.

    When the adapter supports conditional polling it sends the subscription's
    stored ETag / Last-Modified: a ``304 Not Modified`` skips parsing entirely
    (no new entries) and only the validators + timestamp are refreshed. The new
    validators are persisted so the next poll stays conditional.

    When ``sub.full_text`` is set, each new entry's truncated body is replaced
    with the full article (fetched via ``full_text_fetch``, defaulting to the
    real network fetch). Full-text fetches are per-entry best-effort -- a failure
    keeps the summary -- and capped per refresh so a big backlog can't hang the
    tick.
    """
    fetch_full = full_text_fetch
    if sub.full_text and fetch_full is None:
        from quill_social.services.full_text import fetch_full_text

        fetch_full = fetch_full_text
    fulltext_budget = _MAX_FULLTEXT_PER_REFRESH
    if isinstance(adapter, _Poller):
        poll = adapter.poll(etag=sub.etag, last_modified=sub.last_modified, limit=60)
        if getattr(poll, "not_modified", False):
            sub.etag = getattr(poll, "etag", "") or sub.etag
            sub.last_modified = getattr(poll, "last_modified", "") or sub.last_modified
            sub.last_fetched = now
            save_subscription(store, sub)
            return 0
        items = list(getattr(poll, "items", []))
        sub.etag = getattr(poll, "etag", "") or sub.etag
        sub.last_modified = getattr(poll, "last_modified", "") or sub.last_modified
        sub.hub_url = getattr(poll, "hub_url", "") or sub.hub_url
    else:
        items = adapter.home_timeline(limit=60)

    before = {
        it.remote_id
        for it in store.list_items(account_id=sub.account_id, limit=500)
        if it.remote_id
    }
    new_count = 0
    for item in items:
        item.account_id = sub.account_id
        is_new = bool(item.remote_id) and item.remote_id not in before
        # Per-feed keyword rules run before the entry lands (first-match-wins):
        # hide drops it, mark_read pre-reads it, star flags it for follow-up.
        action = feed_filters.decide(item, sub.filters) if sub.filters else ""
        if action == "hide":
            continue
        if action == "mark_read":
            item.read = True
            is_new = False  # a pre-read entry is not "new" to announce
        elif action == "star":
            item.flagged = True
        # Full-text: enrich only genuinely new entries, bounded per refresh, and
        # never let a fetch failure drop the entry -- keep the summary.
        if is_new and sub.full_text and fetch_full is not None and fulltext_budget > 0 and item.uri:
            fulltext_budget -= 1
            try:
                from quill_social.services.full_text import enrich_item_text

                item.text = enrich_item_text(item.text, fetch_full(item.uri))
            except Exception:  # noqa: BLE001 - article fetch is best-effort
                pass
        if is_new:
            new_count += 1
        store.upsert_item(item)
    # Per-feed retention: drop this feed's stale, read/unkept entries (starred and
    # bookmarked rows are always protected). 0 keeps everything.
    if sub.retention_days > 0:
        store.prune_items(keep_days=sub.retention_days, account_id=sub.account_id)
    sub.last_fetched = now
    save_subscription(store, sub)
    return new_count


def refresh_due(
    store: SocialStore,
    subs: list[Subscription],
    resolve_adapter: Callable[[str], _Adapter],
    *,
    now: int,
    full_text_fetch: FullTextFetch | None = None,
) -> int:
    """Refresh every due subscription; return the new count from notify-on feeds.

    A pure, wx-free driver the shell can run on a background thread (with its own
    store connection). Each feed is isolated: a fetch/adapter failure backs that
    one feed off (stamps ``last_fetched``) and never aborts the batch. Feeds with
    notifications disabled still refresh -- they just don't add to the returned
    total the shell announces.
    """
    total = 0
    for sub in due_subscriptions(subs, now=now):
        if store.get_account(sub.account_id) is None:
            continue
        try:
            adapter = resolve_adapter(sub.account_id)
            new = refresh_feed(store, sub, adapter, now=now, full_text_fetch=full_text_fetch)
            if sub.notify:
                total += new
        except Exception:  # noqa: BLE001 - back off this feed, never crash the batch
            sub.last_fetched = now
            save_subscription(store, sub)
    return total
