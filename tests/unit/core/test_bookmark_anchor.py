"""Edit-surviving bookmark anchors: a bookmark must relocate to where its text
actually lives after edits, not drift with a bare offset."""

from __future__ import annotations

from quill.core.bookmark_anchor import BookmarkAnchor, capture_anchor, resolve_anchor

_BASE = "Chapter One\nThe quick brown fox jumps.\nChapter Two\nAnother line here."


def test_no_edit_resolves_to_the_same_offset() -> None:
    off = _BASE.index("brown")
    anchor = capture_anchor(_BASE, off)
    assert resolve_anchor(_BASE, anchor) == off


def test_insertion_above_shifts_the_anchor_to_follow_its_text() -> None:
    off = _BASE.index("brown")
    anchor = capture_anchor(_BASE, off)
    edited = "A whole new preface paragraph.\n\n" + _BASE
    assert resolve_anchor(edited, anchor) == edited.index("brown")


def test_deletion_above_shifts_the_anchor_to_follow_its_text() -> None:
    off = _BASE.index("brown")
    anchor = capture_anchor(_BASE, off)
    edited = _BASE.replace("Chapter One\n", "")
    assert resolve_anchor(edited, anchor) == edited.index("brown")


def test_deleted_bookmarked_text_clamps_without_crashing() -> None:
    off = _BASE.index("brown")
    anchor = capture_anchor(_BASE, off)
    edited = "totally different and much shorter"
    result = resolve_anchor(edited, anchor)
    assert 0 <= result <= len(edited)


def test_repeated_snippet_reanchors_to_the_nearest_occurrence() -> None:
    text = "alpha marker beta\ngamma marker delta"
    # Bookmark the SECOND "marker".
    off = text.index("marker", text.index("marker") + 1)
    anchor = capture_anchor(text, off)
    # Insert above; the second occurrence is still the nearest to the old offset.
    edited = "xx\n" + text
    assert resolve_anchor(edited, anchor) == edited.index("marker", edited.index("marker") + 1)


def test_caret_at_end_of_document_anchors_to_end_of_before() -> None:
    text = "some content ending here"
    anchor = capture_anchor(text, len(text))
    edited = "PREFIX " + text
    assert resolve_anchor(edited, anchor) == len(edited)


def test_offset_is_clamped_on_capture() -> None:
    anchor = capture_anchor("short", 999)
    assert anchor.offset == len("short")


def test_round_trip_through_dict() -> None:
    anchor = capture_anchor(_BASE, _BASE.index("fox"))
    assert BookmarkAnchor.from_dict(anchor.to_dict()) == anchor


def test_from_dict_rejects_non_anchor_values() -> None:
    assert BookmarkAnchor.from_dict(5) is None
    assert BookmarkAnchor.from_dict({"before": "x"}) is None  # no offset
    assert BookmarkAnchor.from_dict({"offset": "nope"}) is None


def test_legacy_anchor_without_context_clamps() -> None:
    # An anchor with empty before/after (e.g. migrated from a bare int) simply
    # clamps to its offset -- never worse than the old behavior.
    anchor = BookmarkAnchor(offset=3, before="", after="", line=0)
    assert resolve_anchor("hello world", anchor) == 3
    assert resolve_anchor("hi", anchor) == 2  # clamped to len
