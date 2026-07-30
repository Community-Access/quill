"""Tests for the SQLite + FTS5 store (PRD 30)."""

from quill_social.model import (
    Account,
    Draft,
    Folder,
    Note,
    PublicationPlan,
    SocialItem,
    Workspace,
)


def _item(remote_id="rem1", account_id="a1", text="hello orbital math", **kw):
    return SocialItem(
        network="mock",
        account_id=account_id,
        remote_id=remote_id,
        author_display="Ada",
        author_handle="@ada",
        text=text,
        **kw,
    )


def test_account_roundtrip(store):
    ws = store.put_workspace(Workspace(name="Personal"))
    a = Account(
        network="mastodon",
        handle="jeff",
        instance="mastodon.example",
        workspace_id=ws.workspace_id,
        is_default=True,
    )
    store.put_account(a)
    got = store.get_account(a.account_id)
    assert got.handle == "jeff"
    assert got.instance == "mastodon.example"
    assert got.is_default
    assert got.full_handle == "@jeff@mastodon.example"


def test_upsert_dedupes_by_remote_id(store):
    store.upsert_item(_item(text="v1"))
    store.upsert_item(_item(text="v2"))  # same network+account+remote
    items = store.list_items()
    assert len(items) == 1
    assert items[0].text == "v2"


def test_upsert_preserves_local_state_on_refetch(store):
    it = store.upsert_item(_item())
    store.set_read(it.item_id, True)
    store.set_flag(it.item_id, "flagged", True)
    # Simulate a network refetch that does not know local state.
    refetched = _item(text="edited text")
    refetched.read = False
    refetched.flagged = False
    store.upsert_item(refetched)
    back = store.get_item(it.item_id)
    assert back.read is True
    assert back.flagged is True
    assert back.text == "edited text"


def test_full_text_search(store):
    store.upsert_item(_item(remote_id="r1", text="calculating orbital trajectories"))
    store.upsert_item(_item(remote_id="r2", text="a post about accessibility"))
    assert len(store.search_items("orbital")) == 1
    assert len(store.search_items("accessibility")) == 1
    assert store.search_items("nonexistentword") == []


def test_search_query_with_punctuation_is_safe(store):
    store.upsert_item(_item(text="hello world"))
    # Must not raise an FTS syntax error; result may be empty.
    assert isinstance(store.search_items('"broken (query'), list)


def test_unread_count_and_mark(store):
    store.upsert_item(_item(remote_id="r1"))
    store.upsert_item(_item(remote_id="r2"))
    assert store.count_unread() == 2
    first = store.list_items()[0]
    store.set_read(first.item_id, True)
    assert store.count_unread() == 1


def test_folders_and_members(store):
    it = store.upsert_item(_item())
    f = store.put_folder(Folder(name="Research", kind="manual"))
    store.add_to_folder(f.folder_id, it.item_id)
    members = store.list_folder_items(f.folder_id)
    assert len(members) == 1
    store.remove_from_folder(f.folder_id, it.item_id)
    assert store.list_folder_items(f.folder_id) == []


def test_draft_roundtrip(store):
    d = Draft(text="draft body", targets=["a1", "a2"], thread_mode=True)
    store.put_draft(d)
    got = store.get_draft(d.draft_id)
    assert got.text == "draft body"
    assert got.targets == ["a1", "a2"]
    assert got.thread_mode is True


def test_notes_confidential_flag_roundtrip(store):
    n = Note(target_type="profile", target_id="@ada", text="met at conference", confidential=True)
    store.put_note(n)
    got = store.notes_for("profile", "@ada")
    assert len(got) == 1
    assert got[0].confidential is True


def test_plans_due_and_state(store):
    d = Draft(text="x", targets=["a1"])
    store.put_draft(d)
    p = PublicationPlan(draft_id=d.draft_id, account_id="a1", state="queued", scheduled_for=500)
    store.put_plan(p)
    assert len(store.due_plans(now=1000)) == 1
    assert store.due_plans(now=100) == []


def test_prune_keeps_bookmarked_and_drafts(store):
    store.upsert_item(_item(remote_id="old"))
    fav = _item(remote_id="fav", text="keep me")
    fav.bookmarked = True
    store.upsert_item(fav)
    d = Draft(text="safe draft", targets=["a1"])
    store.put_draft(d)
    # upsert stamps fetched_at=now; age the cached rows so prune can consider
    # them (a bookmarked row must still survive).
    store.conn.execute("UPDATE items SET fetched_at=0")
    store.conn.commit()
    removed = store.prune_items(keep_days=1)
    assert removed == 1
    remaining = {i.remote_id for i in store.list_items()}
    assert "fav" in remaining and "old" not in remaining
    assert store.get_draft(d.draft_id) is not None  # drafts never pruned


def test_prune_scoped_to_account(store):
    # Two feeds; only the targeted account's stale rows are pruned.
    store.upsert_item(_item(remote_id="a-old", account_id="feedA"))
    store.upsert_item(_item(remote_id="b-old", account_id="feedB"))
    star = _item(remote_id="a-star", account_id="feedA")
    star.flagged = True  # starred/kept: always protected
    store.upsert_item(star)
    store.conn.execute("UPDATE items SET fetched_at=0")
    store.conn.commit()
    removed = store.prune_items(keep_days=1, account_id="feedA")
    assert removed == 1  # only a-old
    remaining = {i.remote_id for i in store.list_items()}
    assert remaining == {"b-old", "a-star"}  # other feed + starred survive


def test_reading_position_roundtrip(store):
    from quill_social.model import ReadingPosition

    store.set_position(ReadingPosition(account_id="a1", feed="home", item_id="i5"))
    pos = store.get_position("a1", "home")
    assert pos.item_id == "i5"
