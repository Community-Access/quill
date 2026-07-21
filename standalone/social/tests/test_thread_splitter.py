"""Tests for the intelligent thread splitter (PRD 16.1)."""

from quill_social.services.thread_splitter import (
    mastodon_counter,
    split_thread,
)


def test_short_text_single_segment():
    r = split_thread("Hello world", 300)
    assert r.count == 1
    assert r.segments[0].text == "Hello world"
    assert not r.any_over_limit


def test_every_segment_within_limit_including_numbering():
    text = " ".join(f"word{i}" for i in range(200))
    r = split_thread(text, 80)
    assert r.count > 1
    for seg in r.segments:
        assert seg.length <= 80, seg.text
    assert not r.any_over_limit


def test_numbering_present_when_multiple():
    text = ". ".join(f"Sentence number {i} here" for i in range(30))
    r = split_thread(text, 90)
    assert r.count > 1
    for seg in r.segments:
        assert seg.text.endswith(f"{seg.index}/{r.count}")


def test_prefers_paragraph_then_sentence_boundaries():
    text = "First para sentence one. First para sentence two.\n\nSecond paragraph body."
    r = split_thread(text, 55, numbering=False)
    # The paragraph boundary should be chosen over a mid-sentence cut.
    assert r.segments[0].text == "First para sentence one. First para sentence two."
    assert r.segments[1].text == "Second paragraph body."


def test_never_breaks_a_url():
    url = "https://example.com/a/very/long/path/that/keeps/going/and/going/more"
    text = f"See this link {url} okay"
    r = split_thread(text, 40, numbering=False)
    # The URL must appear whole in exactly one segment.
    joined = [s for s in r.segments if url in s.text]
    assert len(joined) == 1


def test_oversized_unbreakable_token_flags_over_limit():
    url = "https://example.com/" + "x" * 100
    r = split_thread(f"start {url} end", 40, numbering=False)
    assert r.any_over_limit
    assert any(url in s.text for s in r.segments)
    assert r.warnings


def test_never_breaks_mention_or_hashtag():
    text = "hey " + " ".join(["@friend@server.social"] * 5) + " #accessibility done"
    r = split_thread(text, 30, numbering=False)
    for seg in r.segments:
        # A segment should never start or end mid-token with a dangling '@'.
        assert not seg.text.endswith("@")


def test_mastodon_counter_weights_urls_as_23():
    url = "https://example.com/" + "y" * 100
    assert mastodon_counter(url) == 23
    assert mastodon_counter(f"hi {url}") == 3 + 23


def test_mastodon_counter_drops_mention_domain():
    assert mastodon_counter("@user@instance.social") == len("@user")


def test_split_uses_custom_counter():
    url = "https://example.com/" + "z" * 200
    text = f"lead {url} tail words here"
    # With Mastodon weighting the URL is only 23 chars, so this fits in fewer
    # segments than raw length would suggest.
    r = split_thread(text, 60, numbering=False, counter=mastodon_counter)
    assert not r.any_over_limit


def test_empty_input():
    assert split_thread("", 300).count == 0
    assert split_thread("   \n  ", 300).count == 0


def test_zero_limit_is_safe():
    r = split_thread("hello", 0)
    assert r.count == 0
    assert r.warnings
