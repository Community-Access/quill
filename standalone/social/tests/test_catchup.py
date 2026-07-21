"""Tests for catch-up grouping and collapsing (PRD 12.6)."""

from quill_social.model import SocialItem
from quill_social.services import catchup


def _it(remote_id, author="Ada", text="hello", network="mock", **kw):
    return SocialItem(network=network, remote_id=remote_id, author_display=author,
                      author_id=author, author_handle=f"@{author.lower()}",
                      text=text, **kw)


def test_unread_total():
    items = [_it("1"), _it("2", read=True), _it("3")]
    assert catchup.unread_total(items) == 2


def test_collapse_reposts_when_original_present():
    original = _it("100", text="original")
    boost = _it("200", text="boost", reblog_of="100")
    out = catchup.collapse_reposts([original, boost])
    assert len(out) == 1
    assert out[0].remote_id == "100"


def test_collapse_duplicate_boosts():
    boost1 = _it("201", reblog_of="999")
    boost2 = _it("202", reblog_of="999")
    out = catchup.collapse_reposts([boost1, boost2])
    assert len(out) == 1


def test_collapse_cross_network_keeps_earliest():
    a = _it("m1", network="mastodon", text="same words", created_at=100)
    b = _it("b1", network="bluesky", text="same words", created_at=200)
    out = catchup.collapse_cross_network([a, b])
    assert len(out) == 1
    assert out[0].network == "mastodon"


def test_cross_network_keeps_distinct_text():
    a = _it("m1", network="mastodon", text="one")
    b = _it("b1", network="bluesky", text="two")
    assert len(catchup.collapse_cross_network([a, b])) == 2


def test_group_by_person_sorts_unread_first():
    items = [
        _it("1", author="Ada", read=True),
        _it("2", author="Grace"),
        _it("3", author="Grace"),
    ]
    cu = catchup.group_by_person(items)
    assert cu.groups[0].label == "Grace"
    assert cu.groups[0].unread == 2


def test_group_by_conversation():
    root = _it("r", text="1/", created_at=100)
    root.thread_root = "r"
    reply = _it("c", text="2/", created_at=200)
    reply.thread_root = "r"
    reply.in_reply_to = "r"
    cu = catchup.group_by_conversation([reply, root])
    assert len(cu.groups) == 1
    assert [i.remote_id for i in cu.groups[0].items] == ["r", "c"]


def test_media_only():
    from quill_social.model import Media
    a = _it("1")
    b = _it("2", media=[Media(kind="image")])
    assert catchup.media_only([a, b]) == [b]
