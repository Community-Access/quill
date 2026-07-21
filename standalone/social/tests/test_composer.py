"""Tests for composer capability + accessibility checks (PRD 15.3, 15.6)."""

from quill_social.capabilities import default_for
from quill_social.model import Account, Draft, Media, Poll, PollOption
from quill_social.services.composer import analyze_draft


def _ctx():
    masto = Account(account_id="m", network="mastodon", handle="a", display_name="Ada")
    bsky = Account(account_id="b", network="bluesky", handle="ada.bsky.social",
                   display_name="Ada")
    accounts = {"m": masto, "b": bsky}
    caps = {"m": default_for("mastodon"), "b": default_for("bluesky")}
    return accounts, caps


def test_over_limit_flagged_without_thread_mode():
    accounts, caps = _ctx()
    d = Draft(text="x" * 400, targets=["b"])  # 400 > bluesky 300
    r = analyze_draft(d, accounts, caps)
    nr = r.per_network[0]
    assert not nr.ok
    assert any("over the" in e for e in nr.errors)


def test_thread_mode_avoids_over_limit_error():
    accounts, caps = _ctx()
    d = Draft(text=("word " * 300).strip(), targets=["b"], thread_mode=True)
    r = analyze_draft(d, accounts, caps)
    nr = r.per_network[0]
    assert nr.segments > 1
    assert nr.ok


def test_visibility_not_supported_on_bluesky():
    accounts, caps = _ctx()
    d = Draft(text="hi", targets=["b"], visibility="followers")
    r = analyze_draft(d, accounts, caps)
    assert any("visibility" in e for e in r.per_network[0].errors)


def test_poll_on_bluesky_is_error():
    accounts, caps = _ctx()
    d = Draft(text="vote", targets=["b"],
              poll=Poll(options=[PollOption("a"), PollOption("b")]))
    r = analyze_draft(d, accounts, caps)
    assert any("poll" in e.lower() for e in r.per_network[0].errors)


def test_missing_alt_is_warning_not_error():
    accounts, caps = _ctx()
    d = Draft(text="pic", targets=["m"], media=[Media(kind="image", alt_text="")])
    r = analyze_draft(d, accounts, caps)
    nr = r.per_network[0]
    assert nr.ok  # missing alt does not block publishing
    assert any("alt text" in w for w in nr.warnings)


def test_too_many_media_is_error():
    accounts, caps = _ctx()
    d = Draft(text="lots", targets=["m"],
              media=[Media(alt_text="x") for _ in range(6)])
    r = analyze_draft(d, accounts, caps)
    assert any("too many media" in e for e in r.per_network[0].errors)


def test_unknown_account_reported():
    accounts, caps = _ctx()
    d = Draft(text="hi", targets=["ghost"])
    r = analyze_draft(d, accounts, caps)
    assert not r.ok
    assert "not connected" in r.per_network[0].errors[0]


def test_per_network_variant_text_used():
    accounts, caps = _ctx()
    d = Draft(text="x" * 400, targets=["b"], variants={"bluesky": "short version"})
    r = analyze_draft(d, accounts, caps)
    assert r.per_network[0].length == len("short version")
    assert r.per_network[0].ok


def test_mastodon_url_weighting_in_length():
    accounts, caps = _ctx()
    url = "https://example.com/" + "x" * 100
    d = Draft(text=f"look {url}", targets=["m"])
    r = analyze_draft(d, accounts, caps)
    # 'look ' (5) + weighted url (23) = 28, well under 500
    assert r.per_network[0].length == 28
