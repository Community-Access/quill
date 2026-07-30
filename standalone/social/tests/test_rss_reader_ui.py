"""Feed reader UI wiring: nav tree, nested folders, scopes, mark-all-read/undo.

Builds the real frame against a temp store but never hits the network: feeds are
subscribed and their items inserted directly, then the nav is rebuilt.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.model import Folder, SocialItem  # noqa: E402
from quill_social.services import subscriptions as subs_svc  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILLSOCIAL_DATA", str(tmp_path))
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def _quiet_frame():
    """A frame with auto-mark-on-select disabled, so unread counts are stable.

    Selecting a row normally marks that item read (correct product behaviour);
    these tests exercise the feed nav / mark-all-read logic, so we unbind the
    selection handler to keep counts deterministic.
    """
    from quill_social.ui.app import SocialFrame

    frame = SocialFrame()
    frame.list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
    frame.list.Unbind(wx.EVT_LIST_ITEM_FOCUSED)
    return frame


def _seed_feed(frame, feed_url, folder_id, n_items):
    sub = subs_svc.subscribe(frame.store, feed_url, title=feed_url, folder_id=folder_id)
    for i in range(n_items):
        frame.store.upsert_item(
            SocialItem(network="rss", account_id=sub.account_id, remote_id=f"{feed_url}-{i}")
        )
    return sub


def test_feed_nav_nested_folders_and_scopes(app):
    frame = _quiet_frame()
    try:
        # Deeply nested folders: News > Tech > AI.
        news = frame.store.put_folder(Folder(name="News", kind="manual"))
        tech = frame.store.put_folder(Folder(name="Tech", parent_id=news.folder_id, kind="manual"))
        ai = frame.store.put_folder(Folder(name="AI", parent_id=tech.folder_id, kind="manual"))
        sub = _seed_feed(frame, "https://ai.example/feed", ai.folder_id, 3)

        frame._populate_nav()

        # Feed + all ancestor folders have nav nodes.
        assert f"feed:{sub.account_id}" in frame._nav_nodes
        for folder in (news, tech, ai):
            assert f"folder:{folder.folder_id}" in frame._nav_nodes

        # Unread rolls up through every level of nesting.
        assert frame._folder_unread(news.folder_id) == 3
        assert frame._folder_unread(ai.folder_id) == 3

        # feed: scope shows exactly that feed's items.
        frame._load_scope(f"feed:{sub.account_id}", "AI feed")
        assert len(frame._items) == 3

        # folder: scope at the top rolls up the nested feed.
        frame._load_scope(f"folder:{news.folder_id}", "News")
        assert len(frame._items) == 3
    finally:
        frame._on_close(None)


def test_mark_all_read_and_undo(app):
    frame = _quiet_frame()
    try:
        sub = _seed_feed(frame, "https://a.example/feed", "", 4)
        frame._populate_nav()
        frame._load_scope(f"feed:{sub.account_id}", "A")
        assert frame.store.count_unread(sub.account_id) == 4

        frame.cmd_mark_all_read()
        assert frame.store.count_unread(sub.account_id) == 0
        assert len(frame._undo_mark) == 4
        # Tree label reflects zero unread (no "(N unread)" suffix).
        node = frame._nav_nodes[f"feed:{sub.account_id}"]
        assert "unread" not in frame.nav.GetItemText(node)

        frame.cmd_undo_mark()
        assert frame.store.count_unread(sub.account_id) == 4
    finally:
        frame._on_close(None)


def test_mark_all_read_scoped_to_folder(app):
    frame = _quiet_frame()
    try:
        folder = frame.store.put_folder(Folder(name="Keep", kind="manual"))
        inside = _seed_feed(frame, "https://in.example/feed", folder.folder_id, 2)
        outside = _seed_feed(frame, "https://out.example/feed", "", 2)
        frame._populate_nav()
        frame._load_scope(f"folder:{folder.folder_id}", "Keep")

        frame.cmd_mark_all_read()
        assert frame.store.count_unread(inside.account_id) == 0
        assert frame.store.count_unread(outside.account_id) == 2  # untouched
    finally:
        frame._on_close(None)


def test_smart_folder_nav_and_scope(app):
    frame = _quiet_frame()
    try:
        sub = _seed_feed(frame, "https://a.example/feed", "", 0)
        for rid, text in [("p1", "python news"), ("p2", "python tips"), ("x1", "other")]:
            frame.store.upsert_item(
                SocialItem(network="rss", account_id=sub.account_id, remote_id=rid, text=text)
            )
        folder = frame.store.put_folder(
            Folder(name="Python", kind="smart", rule={"keyword": "python"})
        )
        frame._populate_nav()

        assert "smart_group" in frame._nav_nodes
        scope = f"smart:{folder.folder_id}"
        assert scope in frame._nav_nodes

        frame._load_scope(scope, "Python")
        assert {it.remote_id for it in frame._items} == {"p1", "p2"}  # only keyword hits
    finally:
        frame._on_close(None)


def test_manual_refresh_routes_rss_through_feed_path(app, monkeypatch):
    """F5 sends RSS accounts through refresh_feed so full-text/filters/retention run."""
    from quill_social.services import feed_refresh

    frame = _quiet_frame()
    try:
        sub = _seed_feed(frame, "https://a.example/feed", "", 0)
        seen = {"accounts": []}

        def spy(store, s, adapter, *, now, full_text_fetch=None):
            seen["accounts"].append(s.account_id)  # no network: just record the routing
            return 0

        monkeypatch.setattr(feed_refresh, "refresh_feed", spy)
        frame._refresh_from_network(announce=False)
        assert sub.account_id in seen["accounts"]  # the rss feed went through the feed path
    finally:
        frame._on_close(None)


def test_reading_position_restored_per_feed(app):
    frame = _quiet_frame()
    try:
        sub = _seed_feed(frame, "https://a.example/feed", "", 5)
        other = _seed_feed(frame, "https://b.example/feed", "", 3)
        frame._populate_nav()

        feed_a = f"feed:{sub.account_id}"
        frame._load_scope(feed_a, "A")
        # Land on the 3rd article and remember it by switching away.
        frame.list.Select(2)
        frame.list.Focus(2)
        third_id = frame._items[2].item_id
        frame._load_scope(f"feed:{other.account_id}", "B")

        # Coming back restores focus to that same article.
        frame._load_scope(feed_a, "A")
        assert frame._items[frame.list.GetFirstSelected()].item_id == third_id
    finally:
        frame._on_close(None)


def test_reading_position_defaults_to_first_unread(app):
    frame = _quiet_frame()
    try:
        sub = _seed_feed(frame, "https://a.example/feed", "", 4)
        # Mark the first two read; no saved position yet.
        items = frame.store.list_items(account_id=sub.account_id, limit=10)
        newest_first = sorted(items, key=lambda it: it.created_at, reverse=True)
        frame.store.set_read(newest_first[0].item_id, True)
        frame.store.set_read(newest_first[1].item_id, True)

        frame._populate_nav()
        frame._load_scope(f"feed:{sub.account_id}", "A")
        focused = frame._items[frame.list.GetFirstSelected()]
        assert focused.read is False  # jumped to the first unread article
        assert focused.item_id == newest_first[2].item_id
    finally:
        frame._on_close(None)


def test_find_text_works_across_any_view(app):
    from quill_social.ui.app import SocialFrame

    frame = SocialFrame()
    try:
        # The seeded mock timeline is loaded; find a phrase in it.
        frame._load_scope("home:all", "Home")
        frame.list.Select(0)
        frame.list.Focus(0)
        frame._find_query = "orbital"
        frame._find_direction = "forward"
        frame._do_find()
        idx = frame.list.GetFirstSelected()
        assert idx >= 0
        assert "orbital" in frame.list.GetItemText(idx).lower()

        # A miss leaves things stable and does not raise.
        frame._find_query = "zzz-not-present-phrase"
        frame._do_find()

        # F3 / Shift+F3 repeat the current query without reopening the dialog.
        frame._find_query = "accessibility"
        frame.cmd_find_next()
        assert frame._find_direction == "forward"
        frame.cmd_find_prev()
        assert frame._find_direction == "backward"
    finally:
        frame._on_close(None)


def test_listen_commands_drive_the_queue(app, monkeypatch):
    """Listen menu builds a queue from the view and drives transport (no audio)."""
    from quill_social.services.listen import QueueReader
    from quill_social.ui.app import SocialFrame

    class _FakePlayer:
        def __init__(self):
            self.spoken = []
            self.stopped = 0

        def speak(self, text, on_finished):
            self.spoken.append(text)

        def pause(self):
            pass

        def resume(self):
            pass

        def stop(self):
            self.stopped += 1

    frame = SocialFrame()
    try:
        # Inject a fake reader so no real speech engine is needed.
        player = _FakePlayer()
        frame._queue_reader = QueueReader(player=player, announce=lambda t: None)
        frame._load_scope("home:all", "Home")
        frame.cmd_listen_start()
        assert frame._queue_reader.state == QueueReader.PLAYING
        assert player.spoken  # first article started narrating
        frame.cmd_listen_next()
        frame.cmd_listen_toggle()  # pause
        assert frame._queue_reader.state == QueueReader.PAUSED
        frame.cmd_listen_stop()
        assert frame._queue_reader.state == QueueReader.STOPPED

        # With no reader and the engine forced unavailable, degrade gracefully
        # (announce "not available", never raise, never speak).
        monkeypatch.setattr(
            "quill_social.services.tts_player.Sapi5Player.available",
            staticmethod(lambda: False),
        )
        frame._queue_reader = None
        frame.cmd_listen_start()
        assert frame._queue_reader is None
    finally:
        frame._on_close(None)
