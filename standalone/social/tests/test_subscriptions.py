"""RSS subscriptions, folder placement, and bulk mark-all-read."""

from __future__ import annotations

from quill_social.adapters.registry import adapter_for
from quill_social.adapters.rss import RssAdapter
from quill_social.db import SocialStore
from quill_social.model import Folder, SocialItem
from quill_social.services import subscriptions as subs


def _store(tmp_path) -> SocialStore:
    return SocialStore(tmp_path / "social.db")


def test_subscribe_creates_account_and_is_idempotent(tmp_path):
    store = _store(tmp_path)
    sub = subs.subscribe(store, "https://example.com/feed", title="Example")
    assert sub.feed_url == "https://example.com/feed"
    assert sub.title == "Example"
    # The account exists and the adapter factory builds a read-only RSS adapter.
    account = store.get_account(sub.account_id)
    assert account is not None and account.network == "rss"
    adapter = adapter_for(account)
    assert isinstance(adapter, RssAdapter)
    assert adapter.feed_url == "https://example.com/feed"
    # Subscribing again to the same URL returns the same subscription.
    again = subs.subscribe(store, "https://example.com/feed", title="Dupe")
    assert again.account_id == sub.account_id
    assert len(subs.list_subscriptions(store)) == 1
    store.close()


def test_folder_placement(tmp_path):
    store = _store(tmp_path)
    folder = store.put_folder(Folder(name="Tech"))
    sub = subs.subscribe(store, "https://a.example/feed")
    subs.set_folder(store, sub.account_id, folder.folder_id)
    in_folder = subs.subscriptions_in_folder(store, folder.folder_id)
    assert [s.account_id for s in in_folder] == [sub.account_id]
    store.close()


def test_unsubscribe_removes_account_items_and_doc(tmp_path):
    store = _store(tmp_path)
    sub = subs.subscribe(store, "https://a.example/feed")
    store.upsert_item(
        SocialItem(network="rss", account_id=sub.account_id, remote_id="e1", text="x")
    )
    assert store.count_unread(sub.account_id) == 1
    subs.unsubscribe(store, sub.account_id)
    assert store.get_account(sub.account_id) is None
    assert subs.get_subscription(store, sub.account_id) is None
    assert store.list_items(account_id=sub.account_id) == []
    store.close()


def test_mark_all_read_scoped_and_undo(tmp_path):
    store = _store(tmp_path)
    a = subs.subscribe(store, "https://a.example/feed")
    b = subs.subscribe(store, "https://b.example/feed")
    for acct in (a.account_id, b.account_id):
        for n in range(3):
            store.upsert_item(
                SocialItem(network="rss", account_id=acct, remote_id=f"{acct}-{n}")
            )
    # Scope to feed A only.
    changed = store.mark_all_read(account_ids=[a.account_id])
    assert len(changed) == 3
    assert store.count_unread(a.account_id) == 0
    assert store.count_unread(b.account_id) == 3
    # Marking again is a no-op (nothing changes).
    assert store.mark_all_read(account_ids=[a.account_id]) == []
    # Undo restores exactly the rows that changed.
    store.set_read_bulk(changed, read=False)
    assert store.count_unread(a.account_id) == 3
    store.close()


def test_mark_all_read_global(tmp_path):
    store = _store(tmp_path)
    a = subs.subscribe(store, "https://a.example/feed")
    b = subs.subscribe(store, "https://b.example/feed")
    for acct in (a.account_id, b.account_id):
        store.upsert_item(SocialItem(network="rss", account_id=acct, remote_id=f"{acct}-x"))
    changed = store.mark_all_read()
    assert len(changed) == 2
    assert store.count_unread() == 0
    store.close()
