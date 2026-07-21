"""Tests for the configurable field reader (PRD 12.4, 28.5)."""

from quill_social.a11y import A11ySettings
from quill_social.fields import FieldProfile, field_value, read_fields, render_row
from quill_social.model import Account, Media, SocialItem, now_ms


def _item(**kw):
    return SocialItem(network="mock", author_display="Ada", author_handle="@ada",
                      text="hello world", reply_count=2, reblog_count=3,
                      favourite_count=5, **kw)


def test_render_row_default_is_terse():
    it = _item()
    row = render_row(it, FieldProfile(), settings=A11ySettings(), now=now_ms())
    assert "Ada" in row
    assert "hello world" in row
    # engagement off by default
    assert "favourites" not in row


def test_render_row_speaks_engagement_when_enabled():
    it = _item()
    s = A11ySettings(speak_engagement=True)
    row = render_row(it, FieldProfile(), settings=s, now=now_ms())
    assert "favourites" in row


def test_render_row_network_prefix_toggle():
    it = _item()
    on = render_row(it, FieldProfile(), settings=A11ySettings(speak_network_prefix=True))
    off = render_row(it, FieldProfile(),
                     settings=A11ySettings(speak_network_prefix=False))
    assert "Mock" in on
    assert "Mock" not in off


def test_read_fields_drops_empty_values():
    it = _item()  # no media, no CW
    pairs = read_fields(it, FieldProfile(), settings=A11ySettings())
    labels = [label for label, _ in pairs]
    assert "Content warning" not in labels
    assert "Media" not in labels
    assert "Author" in labels


def test_alt_field_reports_missing():
    it = _item(media=[Media(kind="image", alt_text=""), Media(alt_text="ok")])
    val = field_value(it, "alt")
    assert "1 of 2 missing" in val


def test_relation_field_describes_reply_and_boost():
    it = _item(in_reply_to="x", reblog_of="y", reblog_by="@grace")
    val = field_value(it, "relation")
    assert "reply" in val
    assert "boosted by @grace" in val


def test_read_state_respects_setting():
    it = _item(read=False)
    assert field_value(it, "read", settings=A11ySettings(announce_read_state=True)) \
        == "unread"
    assert field_value(it, "read", settings=A11ySettings(announce_read_state=False)) \
        == ""


def test_account_field_uses_account_label():
    it = _item(account_id="a1")
    acct = Account(account_id="a1", network="mock", local_alias="Demo")
    assert field_value(it, "account", account=acct) == "Demo"


def test_relative_time_recent():
    it = _item(created_at=now_ms() - 30_000)
    assert field_value(it, "date", now=now_ms()) == "just now"
