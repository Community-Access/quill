"""RSS feed subscriptions on top of the existing store (plan xxx.md 3.3).

A subscription reuses what product B already has instead of adding a bespoke
table:

- an ``Account`` row (``network="rss"``, ``instance`` = feed URL) -- which the
  adapter factory already turns into a read-only :class:`RssAdapter`, and which
  gives every feed entry an ``account_id`` for dedupe and per-feed unread counts;
- a ``feed_subscription`` document (the generic JSON store) holding the folder
  placement, tags, refresh cadence, and conditional-GET validators.

Folders reuse the nestable ``folders`` table (``Folder.parent_id``), so
folders-of-folders come for free. This module is wx-free and I/O-free beyond the
store; fetching/parsing lives in the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill_social.db import SocialStore
from quill_social.model import Account, now_ms

DOC_KIND = "feed_subscription"
DEFAULT_REFRESH_S = 900


@dataclass
class Subscription:
    """A subscribed feed: its account id plus local placement and fetch state."""

    account_id: str
    feed_url: str
    title: str = ""
    site_url: str = ""
    folder_id: str = ""
    tags: list[str] = field(default_factory=list)
    refresh_interval_s: int = DEFAULT_REFRESH_S
    retention_days: int = 0  # 0 = keep forever; N = prune read/unkept older than N
    notify: bool = True  # include this feed's new items in the polite announcement
    full_text: bool = False  # fetch the full article for truncated feeds
    # Per-feed keyword rules: each is {"keyword": str, "action": hide|mark_read|star}.
    filters: list[dict] = field(default_factory=list)
    etag: str = ""
    last_modified: str = ""
    hub_url: str = ""  # WebSub hub advertised by the feed (detection only; polls still)
    last_fetched: int = 0  # epoch ms of the last successful/attempted refresh
    added: int = field(default_factory=now_ms)

    def to_doc(self) -> dict:
        return {
            "account_id": self.account_id,
            "feed_url": self.feed_url,
            "title": self.title,
            "site_url": self.site_url,
            "folder_id": self.folder_id,
            "tags": list(self.tags),
            "refresh_interval_s": self.refresh_interval_s,
            "retention_days": self.retention_days,
            "notify": self.notify,
            "full_text": self.full_text,
            "filters": [dict(f) for f in self.filters],
            "etag": self.etag,
            "last_modified": self.last_modified,
            "hub_url": self.hub_url,
            "last_fetched": self.last_fetched,
            "added": self.added,
        }

    @classmethod
    def from_doc(cls, d: dict) -> Subscription:
        return cls(
            account_id=d.get("account_id", ""),
            feed_url=d.get("feed_url", ""),
            title=d.get("title", ""),
            site_url=d.get("site_url", ""),
            folder_id=d.get("folder_id", ""),
            tags=list(d.get("tags", [])),
            refresh_interval_s=int(d.get("refresh_interval_s", DEFAULT_REFRESH_S) or 0),
            retention_days=int(d.get("retention_days", 0) or 0),
            notify=bool(d.get("notify", True)),
            full_text=bool(d.get("full_text", False)),
            filters=[dict(f) for f in d.get("filters", []) if isinstance(f, dict)],
            etag=d.get("etag", ""),
            last_modified=d.get("last_modified", ""),
            hub_url=d.get("hub_url", ""),
            last_fetched=int(d.get("last_fetched", 0) or 0),
            added=int(d.get("added", 0) or 0),
        )


def _normalize_url(url: str) -> str:
    return url.strip()


def find_by_url(store: SocialStore, feed_url: str) -> Subscription | None:
    """Return an existing subscription for ``feed_url`` (dedupe key), or None."""
    target = _normalize_url(feed_url)
    for doc in store.list_documents(DOC_KIND):
        if _normalize_url(doc.get("feed_url", "")) == target:
            return Subscription.from_doc(doc)
    return None


def subscribe(
    store: SocialStore,
    feed_url: str,
    *,
    title: str = "",
    site_url: str = "",
    folder_id: str = "",
    tags: list[str] | None = None,
) -> Subscription:
    """Subscribe to ``feed_url`` (idempotent by URL). Returns the subscription."""
    feed_url = _normalize_url(feed_url)
    if not feed_url:
        raise ValueError("feed_url is required")
    existing = find_by_url(store, feed_url)
    if existing is not None:
        return existing
    display = title or feed_url
    account = Account(
        network="rss",
        handle=display,
        display_name=display,
        instance=feed_url,
    )
    store.put_account(account)
    sub = Subscription(
        account_id=account.account_id,
        feed_url=feed_url,
        title=display,
        site_url=site_url,
        folder_id=folder_id,
        tags=list(tags or []),
    )
    store.put_document(DOC_KIND, account.account_id, sub.to_doc())
    return sub


def get_subscription(store: SocialStore, account_id: str) -> Subscription | None:
    doc = store.get_document(DOC_KIND, account_id)
    return Subscription.from_doc(doc) if doc else None


def list_subscriptions(store: SocialStore) -> list[Subscription]:
    return [Subscription.from_doc(d) for d in store.list_documents(DOC_KIND)]


def subscriptions_in_folder(store: SocialStore, folder_id: str) -> list[Subscription]:
    """Direct feed subscriptions filed in ``folder_id`` (not recursive)."""
    return [s for s in list_subscriptions(store) if s.folder_id == folder_id]


def save_subscription(store: SocialStore, sub: Subscription) -> Subscription:
    """Persist edits to a subscription (folder move, rename, fetch validators)."""
    store.put_document(DOC_KIND, sub.account_id, sub.to_doc())
    return sub


def set_folder(store: SocialStore, account_id: str, folder_id: str) -> None:
    sub = get_subscription(store, account_id)
    if sub is None:
        return
    sub.folder_id = folder_id
    save_subscription(store, sub)


def unsubscribe(store: SocialStore, account_id: str) -> None:
    """Remove a subscription: its account, cached items, and its config doc."""
    store.delete_account(account_id)  # also clears the feed's items + FTS rows
    store.delete_document(DOC_KIND, account_id)
