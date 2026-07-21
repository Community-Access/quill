"""Tests for the Where Am I context builder (PRD 10.3)."""

from quill_social.whereami import WhereAmI


def test_full_announcement_includes_key_parts():
    w = WhereAmI(
        workspace="Personal", account="Demo", network="mastodon",
        feed="Unified Home", position=3, total=15, unread=4,
        sort_state="newest first", post_type="reply", visibility="public",
        current_field="Author", field_value="Ada",
    )
    text = w.announce()
    assert "Workspace Personal" in text
    assert "Account Demo on Mastodon" in text
    assert "Unified Home" in text
    assert "item 3 of 15" in text
    assert "4 unread" in text
    assert "reply" in text
    assert "field Author: Ada" in text
    assert text.endswith(".")


def test_empty_context():
    assert WhereAmI().announce() == "No context available"


def test_error_and_pending_surface():
    w = WhereAmI(feed="Queue", pending="publishing", error="rate limited")
    text = w.announce()
    assert "pending publishing" in text
    assert "error: rate limited" in text


def test_omits_empty_fields():
    w = WhereAmI(feed="Bookmarks", position=1, total=2)
    text = w.announce()
    assert "Workspace" not in text
    assert "Bookmarks" in text
    assert "item 1 of 2" in text
