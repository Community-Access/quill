"""YouTube comments: parsing, threading, the row wording, filtering, sort, paging."""

from __future__ import annotations

from quill.core.radio import youtube_comments as yc

INFO = {
    "comments": [
        {
            "id": "c1",
            "parent": "root",
            "text": "The bridge at sunset is the best bit.\nWent last spring.",
            "author": "@Alice",
            "like_count": 1203,
            "_time_text": "2 years ago",
            "is_pinned": True,
        },
        {
            "id": "c1.r1",
            "parent": "c1",
            "text": "Agreed, the suspension bridge!",
            "author": "@Rick Steves",
            "like_count": 1,
            "_time_text": "2 years ago",
            "author_is_uploader": True,
        },
        {"id": "c2", "parent": "root", "text": "Great narration", "author": "@Bob"},
        {"id": "", "parent": "root", "text": "no id is dropped"},
        {"id": "x9.r", "parent": "x9", "text": "Orphaned reply", "author": "@Carol"},
    ]
}


def test_threads_put_replies_after_their_comment_and_name_the_parent() -> None:
    comments = yc.parse_comments(INFO)
    assert [c.comment_id for c in comments] == ["c1", "c1.r1", "c2", "x9.r"]
    assert comments[1].reply_to == "Alice"
    assert comments[3].is_reply and comments[3].reply_to == ""


def test_row_label_is_author_first_line_then_likes_and_when() -> None:
    first, reply, plain, orphan = yc.parse_comments(INFO)
    assert yc.row_label(first) == (
        "Alice, pinned: The bridge at sunset is the best bit. ... (1,203 likes, 2 years ago)"
    )
    assert yc.row_label(reply) == (
        "Rick Steves (channel owner), reply to Alice: Agreed, the suspension bridge! "
        "(1 like, 2 years ago)"
    )
    assert yc.row_label(plain) == "Bob: Great narration"
    assert yc.row_label(orphan).startswith("Carol, reply:")


def test_a_long_first_line_is_cut_for_the_row_but_kept_in_full_text() -> None:
    long = yc.Comment("z", "Dee", "word " * 60)
    assert yc.row_label(long).endswith(" ...")
    assert ("word " * 60).strip() in yc.full_text(long)


def test_full_text_names_who_was_answered() -> None:
    reply = yc.parse_comments(INFO)[1]
    assert yc.full_text(reply).startswith("Rick Steves, replying to Alice (1 like, 2 years ago)")


def test_filter_needs_every_word_in_any_order_ignoring_case() -> None:
    comments = yc.parse_comments(INFO)
    assert [c.comment_id for c in yc.filter_comments(comments, "BRIDGE sunset")] == ["c1"]
    assert [c.comment_id for c in yc.filter_comments(comments, "bob")] == ["c2"]
    assert yc.filter_comments(comments, "  ") == comments
    assert yc.filter_comments(comments, "zebra") == []


def test_fetch_asks_for_comments_in_the_chosen_order_and_cap() -> None:
    asked: list[dict] = []

    def fetch(target, options):
        asked.append(dict(options))
        return INFO

    yc.fetch_comments("https://www.youtube.com/watch?v=abcdefghijk", sort=yc.NEWEST, fetch=fetch)
    args = asked[0]["extractor_args"]["youtube"]
    assert asked[0]["getcomments"] is True
    assert args == {"max_comments": ["100"], "comment_sort": ["new"]}
    yc.fetch_comments("u", sort="anything else", limit=5000, fetch=fetch)
    assert asked[1]["extractor_args"]["youtube"] == {
        "max_comments": [str(yc.MAX_COMMENTS)],
        "comment_sort": ["top"],
    }


def test_paging_grows_by_a_page_and_stops_at_the_cap() -> None:
    assert yc.next_limit(100) == 200
    assert yc.next_limit(950) == 1000
    assert yc.next_limit(1000) == 0


def test_merge_keeps_what_was_there_and_never_duplicates() -> None:
    old = yc.parse_comments(INFO)[:2]
    new = yc.parse_comments(INFO)[1:]
    merged = yc.merge(old, new)
    assert [c.comment_id for c in merged] == ["c1.r1", "c2", "x9.r", "c1"]


def test_a_video_with_no_comments_is_an_empty_list() -> None:
    assert yc.parse_comments({}) == []
    assert yc.parse_comments({"comments": None}) == []


def test_emoji_are_read_as_their_names_and_joiners_say_nothing() -> None:
    said = yc.speakable("So good \U0001f602\U0001f602 and \u2764\ufe0f :yt-heart:")
    assert (
        said == "So good (face with tears of joy) (face with tears of joy) and "
        "(heavy black heart) :yt-heart:"
    )


def test_links_are_named_as_links() -> None:
    comment = yc.Comment("l", "Ann", "Map here: https://www.example.com/bristol/map. Enjoy")
    assert "link to example.com." in yc.row_label(comment)
    assert "link: https://www.example.com/bristol/map." in yc.full_text(comment)


def test_a_search_finds_an_emoji_by_its_name() -> None:
    comment = yc.Comment("e", "Ann", "\U0001f602")
    assert yc.filter_comments([comment], "tears of joy") == [comment]
