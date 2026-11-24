"""The timeline refreshes without moving the reader (FUX-06).

Every refresh used to reload the whole scope: the list was cleared and filled,
"Feed. 3 items, 3 unread." was said again, the saved row was selected again
(and so marked read again), and new posts jumped in at the top. Now posts
change row by row around the reader's, new ones wait behind a count until F5,
and a post that has gone is said once.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.model import SocialItem  # noqa: E402
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


def _frame(monkeypatch):
    from quill_social.ui.app import SocialFrame

    frame = SocialFrame()
    frame._refresh_from_network = lambda **_k: None  # never the network
    said: list[str] = []
    monkeypatch.setattr(frame.announcer, "say", lambda text, *_a, **_k: said.append(text))
    # The "gone" sentence waits for the screen reader and the window in front.
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    monkeypatch.setattr(wx.TopLevelWindow, "IsActive", lambda _self: True)
    return frame, said


def _post(sub, n: int) -> SocialItem:
    return SocialItem(
        network="rss",
        account_id=sub.account_id,
        remote_id=f"post-{n}",
        text=f"Post {n}",
        author_display=f"Author {n}",
        created_at=1_000_000 + n,
    )


def _feed(frame, count: int):
    sub = subs_svc.subscribe(frame.store, "https://f.example/feed", title="F")
    posts = [_post(sub, n) for n in range(count)]
    for post in posts:
        frame.store.upsert_item(post)
    frame._load_scope(f"feed:{sub.account_id}", "F")
    return sub, posts


def _reader(frame) -> str:
    return frame._items[frame.list.GetFirstSelected()].text


def test_new_posts_wait_behind_a_count_and_join_on_f5(app, monkeypatch) -> None:
    frame, said = _frame(monkeypatch)
    try:
        sub, _posts = _feed(frame, 3)
        frame.list.Select(1)
        frame.list.Focus(1)
        reader = _reader(frame)
        said.clear()
        frame.store.upsert_item(_post(sub, 9))
        frame._timeline_changed()
        assert len(frame._items) == 3, "an arrival does not enter the list by itself"
        assert _reader(frame) == reader
        assert said == ["1 new post. Press F5 to show them."]
        frame._timeline_changed()
        assert said == ["1 new post. Press F5 to show them."], "said once, not every tick"
        frame.cmd_refresh()
        assert len(frame._items) == 4
        assert _reader(frame) == reader
        assert said[-1] == "Refreshed. 1 new post."
    finally:
        frame._on_close(None)


def test_a_post_gone_from_the_store_is_said_once_and_its_neighbour_chosen(app, monkeypatch) -> None:
    frame, said = _frame(monkeypatch)
    try:
        _sub, _posts = _feed(frame, 3)
        frame.list.Select(1)
        frame.list.Focus(1)
        gone = frame._items[1]
        below = frame._items[2].text
        below_id = frame._items[2].item_id
        said.clear()
        with frame.store.conn:
            frame.store.conn.execute("DELETE FROM items WHERE item_id=?", (gone.item_id,))
        frame._timeline_changed()
        assert _reader(frame) == below
        assert said == [f"The post by {gone.author_display} is no longer in the list."]
        # Landing on the neighbour is not opening it: it stays unread.
        assert frame.store.get_item(below_id).read is False
    finally:
        frame._on_close(None)


def test_a_refresh_does_not_throw_the_reader_out_of_a_conversation(app, monkeypatch) -> None:
    frame, _said = _frame(monkeypatch)
    try:
        sub, _posts = _feed(frame, 2)
        frame.list.Select(0)
        frame.cmd_open_conversation()
        thread = list(frame._items)
        frame.store.upsert_item(_post(sub, 7))
        frame._timeline_changed()
        assert [it.item_id for it in frame._items] == [it.item_id for it in thread]
        frame.cmd_refresh()  # F5 in a conversation refreshes the conversation
        assert [it.item_id for it in frame._items] == [it.item_id for it in thread]
    finally:
        frame._on_close(None)
