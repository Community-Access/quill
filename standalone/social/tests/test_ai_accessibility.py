"""Tests for the Accessibility Assistant heuristics (PRD 21.5)."""

from quill_social.model import Draft, Media, Poll, PollOption, SocialItem
from quill_social.services.ai import accessibility as a11y


def _kinds(issues):
    return {i.kind for i in issues}


def test_missing_alt_text_fires_and_stays_quiet_when_present():
    assert "missing_alt_text" in _kinds(a11y.check_media([Media(kind="image")]))
    described = a11y.check_media([Media(kind="image", alt_text="A red bicycle")])
    assert "missing_alt_text" not in _kinds(described)


def test_filename_like_description_detected():
    issues = a11y.check_media([Media(kind="image", alt_text="IMG_1234.jpg")])
    assert "filename_like_description" in _kinds(issues)
    clean = a11y.check_media([Media(kind="image", alt_text="Sunset over the bay")])
    assert "filename_like_description" not in _kinds(clean)


def test_media_without_transcript_detected():
    assert "media_without_transcript" in _kinds(a11y.check_media([Media(kind="audio")]))
    with_tx = a11y.check_media([Media(kind="video", transcript="full transcript")])
    assert "media_without_transcript" not in _kinds(with_tx)


def test_image_with_substantial_text_flagged():
    issues = a11y.check_media(
        [Media(kind="image", alt_text="screenshot of the settings screen")]
    )
    assert "image_with_text" in _kinds(issues)
    clean = a11y.check_media([Media(kind="image", alt_text="a dog on a beach")])
    assert "image_with_text" not in _kinds(clean)


def test_ambiguous_link_text_detected():
    assert "ambiguous_link_text" in _kinds(
        a11y.check_text("Click here https://example.com for the guide")
    )
    clean = a11y.check_text("Read the accessibility guide at https://example.com/a11y")
    assert "ambiguous_link_text" not in _kinds(clean)


def test_emoji_only_meaning_detected():
    assert "emoji_only_meaning" in _kinds(a11y.check_text("🎉🎉🎉"))
    assert "emoji_only_meaning" not in _kinds(a11y.check_text("Party time 🎉"))


def test_unexplained_acronym_detected():
    assert "unexplained_acronym" in _kinds(a11y.check_text("The FOOBAR release is out"))
    # Well-known acronyms in the allowlist stay quiet.
    assert "unexplained_acronym" not in _kinds(a11y.check_text("Read the API docs"))


def test_all_caps_passage_detected():
    assert "all_caps_passage" in _kinds(
        a11y.check_text("THIS IS ENTIRELY SHOUTING RIGHT NOW")
    )
    assert "all_caps_passage" not in _kinds(a11y.check_text("This is a calm sentence."))


def test_unclear_poll_detected():
    unclear = a11y.check_poll(Poll(options=[PollOption("a"), PollOption("b")]))
    assert "unclear_poll" in _kinds(unclear)
    clear = a11y.check_poll(
        Poll(options=[PollOption("Yes, ship it"), PollOption("No, hold off")])
    )
    assert "unclear_poll" not in _kinds(clear)
    assert a11y.check_poll(None) == []


def test_thread_loses_context_detected():
    text = (
        "We shipped the brand new build today after weeks of careful testing. "
        "It fixes the annoying crash."
    )
    issues = a11y.check_thread(text, limit=40)
    assert "thread_loses_context" in _kinds(issues)
    # Short text that does not split stays quiet.
    assert a11y.check_thread("One short post.", limit=500) == []


def test_check_draft_entry_point_aggregates():
    draft = Draft(
        text="Click here https://example.com",
        media=[Media(kind="image")],
        poll=Poll(options=[PollOption("a"), PollOption("b")]),
    )
    kinds = _kinds(a11y.check_draft(draft))
    assert "ambiguous_link_text" in kinds
    assert "missing_alt_text" in kinds
    assert "unclear_poll" in kinds


def test_check_item_entry_point():
    item = SocialItem(text="THIS IS ALL CAPS SHOUTING", media=[Media(kind="image")])
    kinds = _kinds(a11y.check_item(item))
    assert "all_caps_passage" in kinds
    assert "missing_alt_text" in kinds
