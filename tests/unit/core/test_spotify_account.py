"""Tests for telling a free Spotify account what it can and cannot do.

The split is Spotify's: the Web API (search, library, playlists) is open to any
account, while the Web Playback SDK is Premium-only. A free user should learn
that from a plain sentence at sign-in, not from an opaque SDK error the first
time they press play.
"""

from quill.core.spotify.models import (
    FREE_ACCOUNT_NOTICE,
    PREMIUM_ACCOUNT_NOTICE,
    account_can_play,
    account_product,
    describe_account,
)


def test_a_premium_profile_may_play() -> None:
    assert account_product({"product": "premium"}) == "premium"
    assert account_can_play({"product": "premium"}) is True


def test_a_free_profile_may_not_play() -> None:
    assert account_product({"product": "free"}) == "free"
    assert account_can_play({"product": "free"}) is False


def test_the_open_tier_is_treated_as_free() -> None:
    """Spotify reports some unpaid accounts as "open"."""
    assert account_can_play({"product": "open"}) is False


def test_product_is_matched_case_and_space_insensitively() -> None:
    assert account_product({"product": "  Premium  "}) == "premium"
    assert account_can_play({"product": "FREE"}) is False


def test_an_unknown_tier_is_allowed_to_try() -> None:
    """Locking out a paying subscriber over a missing field is the worse error."""
    assert account_can_play({}) is True
    assert account_can_play({"product": "something-new"}) is True
    assert account_product({}) == ""


def test_the_free_notice_says_what_still_works() -> None:
    """A refusal that lists only what is lost reads as "this is useless to you"."""
    notice = FREE_ACCOUNT_NOTICE.lower()
    assert "search" in notice
    assert "brows" in notice  # "browsing" / "browse"
    assert "premium" in notice


def test_the_free_notice_points_at_where_playing_does_work() -> None:
    """Free users play Spotify every day -- in Spotify's app. Say so.

    "Free accounts cannot play Spotify" is both false and discouraging; the
    restriction is on *where* the audio plays, not on whether you may listen.
    """
    assert "spotify app" in FREE_ACCOUNT_NOTICE.lower()


def test_describe_account_picks_the_right_sentence() -> None:
    assert describe_account({"product": "free"}) == FREE_ACCOUNT_NOTICE
    assert describe_account({"product": "premium"}) == PREMIUM_ACCOUNT_NOTICE
