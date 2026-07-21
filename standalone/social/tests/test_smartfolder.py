"""Tests for smart-folder rule evaluation (PRD 13.2)."""

from quill_social.model import Media, SocialItem
from quill_social.services import smartfolder


def _it(**kw):
    kw.setdefault("text", "hello")
    kw.setdefault("network", "mock")
    return SocialItem(author_display="Ada", author_handle="@ada", **kw)


def test_empty_rule_matches_all():
    items = [_it(), _it(network="bluesky")]
    assert len(smartfolder.evaluate(items, {})) == 2


def test_network_filter():
    items = [_it(network="mastodon"), _it(network="bluesky")]
    hits = smartfolder.evaluate(items, {"network": "bluesky"})
    assert len(hits) == 1
    assert hits[0].network == "bluesky"


def test_missing_alt_rule():
    good = _it(remote_id="g", media=[Media(alt_text="ok")])
    bad = _it(remote_id="b", media=[Media(alt_text="")])
    hits = smartfolder.evaluate([good, bad], {"missing_alt": True})
    assert [h.remote_id for h in hits] == ["b"]


def test_keyword_and_language_and_engagement():
    a = _it(text="accessibility matters", lang="en", reply_count=5, reblog_count=5,
            favourite_count=5)
    b = _it(text="something else", lang="fr")
    hits = smartfolder.evaluate([a, b],
                                {"keyword": "accessibility", "language": "en",
                                 "min_engagement": 10})
    assert len(hits) == 1


def test_unreplied_rule():
    a = _it(reply_count=0)
    b = _it(reply_count=3)
    hits = smartfolder.evaluate([a, b], {"unreplied": True})
    assert len(hits) == 1


def test_date_range():
    a = _it(created_at=100)
    b = _it(created_at=5000)
    hits = smartfolder.evaluate([a, b], {"since_ms": 1000})
    assert len(hits) == 1
    assert hits[0].created_at == 5000


def test_results_newest_first():
    a = _it(remote_id="old", created_at=100)
    b = _it(remote_id="new", created_at=9000)
    hits = smartfolder.evaluate([a, b], {})
    assert [h.remote_id for h in hits] == ["new", "old"]
