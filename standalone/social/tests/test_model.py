"""Tests for the domain model roundtrips (PRD 30)."""

from quill_social.model import (
    Account,
    Draft,
    Media,
    Poll,
    PollOption,
    PublicationPlan,
    SocialItem,
    now_ms,
)


def test_socialitem_row_roundtrip_with_media_and_poll():
    it = SocialItem(
        network="mastodon", account_id="a1", remote_id="123",
        author_display="Ada", text="hi", visibility="unlisted",
        content_warning="spoiler", moderation_labels=["nsfw"], tags=["accessibility"],
        media=[Media(kind="image", alt_text="a cat")],
        poll=Poll(options=[PollOption("yes", 3), PollOption("no", 1)], total_votes=4),
    )
    back = SocialItem.from_row(it.to_row())
    assert back.author_display == "Ada"
    assert back.content_warning == "spoiler"
    assert back.moderation_labels == ["nsfw"]
    assert back.tags == ["accessibility"]
    assert back.media[0].alt_text == "a cat"
    assert back.poll.total_votes == 4
    assert back.poll.options[0].title == "yes"


def test_media_has_alt():
    assert Media(alt_text="x").has_alt
    assert not Media(alt_text="   ").has_alt


def test_missing_alt_count():
    it = SocialItem(media=[Media(alt_text="ok"), Media(alt_text="")])
    assert it.missing_alt_count == 1


def test_account_label_prefers_alias():
    a = Account(network="bluesky", handle="ada.bsky.social", display_name="Ada",
                local_alias="Work")
    assert a.label == "Work"
    a.local_alias = ""
    assert a.label == "Ada"


def test_bluesky_full_handle():
    a = Account(network="bluesky", handle="ada.bsky.social")
    assert a.full_handle == "@ada.bsky.social"


def test_draft_roundtrip_variants():
    d = Draft(text="base", variants={"bluesky": "short"}, targets=["a1"])
    back = Draft.from_row(d.to_row())
    assert back.variants["bluesky"] == "short"


def test_plan_retry_count():
    from quill_social.model import DeliveryAttempt
    p = PublicationPlan(attempts=[
        DeliveryAttempt(ok=False), DeliveryAttempt(ok=True), DeliveryAttempt(ok=False)])
    assert p.retry_count == 2
    back = PublicationPlan.from_row(p.to_row())
    assert back.retry_count == 2


def test_new_ids_are_unique():
    from quill_social.model import new_id
    assert new_id("x") != new_id("x")


def test_now_ms_is_int():
    assert isinstance(now_ms(), int)
