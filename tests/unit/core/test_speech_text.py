"""Speech-shaped text for the announcement path (assessment item 9)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quill.core.speech_text import (
    clock_duration,
    condense_leading_mentions,
    first_sentence,
    format_relative_time,
    html_to_speech_text,
    prepare_for_speech,
    scrub_tts_hazards,
    speak_duration,
    strip_decorative_unicode,
    strip_markdown_for_speech,
)

# -- strip_markdown_for_speech -----------------------------------------------


def test_emphasis_markers_do_not_reach_the_listener() -> None:
    assert strip_markdown_for_speech("This is **very** important") == "This is very important"
    assert strip_markdown_for_speech("This is __very__ important") == "This is very important"
    assert strip_markdown_for_speech("A *stressed* word") == "A stressed word"
    assert strip_markdown_for_speech("A _stressed_ word") == "A stressed word"
    assert strip_markdown_for_speech("~~gone~~ now") == "gone now"


def test_snake_case_identifiers_survive_emphasis_stripping() -> None:
    # An underscore inside a word is not emphasis; speaking "sortlinesbydate"
    # would be a different identifier than the one the AI actually named.
    assert strip_markdown_for_speech("call sort_lines_by_date now") == "call sort_lines_by_date now"


def test_headings_keep_their_words_and_lose_their_hashes() -> None:
    assert strip_markdown_for_speech("## Results") == "Results"
    assert strip_markdown_for_speech("###### Deep") == "Deep"
    assert strip_markdown_for_speech("## Closed ##") == "Closed"


def test_setext_underline_and_thematic_breaks_are_dropped() -> None:
    assert strip_markdown_for_speech("Title\n=====\nBody") == "Title\nBody"
    assert strip_markdown_for_speech("one\n\n---\n\ntwo") == "one\n\ntwo"
    assert strip_markdown_for_speech("one\n***\ntwo") == "one\ntwo"


def test_link_keeps_its_label_and_drops_its_url() -> None:
    assert strip_markdown_for_speech("See [the guide](https://x.test/a/b)") == "See the guide"


def test_autolink_is_spoken_without_its_angle_brackets() -> None:
    assert strip_markdown_for_speech("Visit <https://x.test>") == "Visit https://x.test"


def test_image_is_announced_with_its_alt_text() -> None:
    assert strip_markdown_for_speech("![a red door](d.png)") == "image, a red door"
    assert strip_markdown_for_speech("![](d.png)") == "image"


def test_inline_code_loses_its_backticks() -> None:
    assert strip_markdown_for_speech("run `pytest -q` first") == "run pytest -q first"


def test_fenced_code_block_collapses_to_two_words() -> None:
    text = "Here:\n```python\nprint(1)\nprint(2)\n```\nDone"
    assert strip_markdown_for_speech(text) == "Here:\ncode block\nDone"


def test_unterminated_fence_still_collapses() -> None:
    assert strip_markdown_for_speech("Here:\n```\nprint(1)") == "Here:\ncode block"


def test_list_markers_are_removed_and_items_survive() -> None:
    assert strip_markdown_for_speech("- one\n- two") == "one\ntwo"
    assert strip_markdown_for_speech("1. first\n2. second") == "first\nsecond"


def test_blockquote_markers_are_removed() -> None:
    assert strip_markdown_for_speech("> quoted\n>> deeper") == "quoted\ndeeper"


def test_table_row_reads_as_a_sentence() -> None:
    table = "| Name | Size |\n| --- | --- |\n| a.txt | 4 KB |"
    assert strip_markdown_for_speech(table) == "Name, Size\na.txt, 4 KB"


def test_plain_prose_is_returned_unchanged() -> None:
    assert strip_markdown_for_speech("Nothing to do here.") == "Nothing to do here."


# -- scrub_tts_hazards -------------------------------------------------------


@pytest.mark.parametrize(
    "invisible",
    ["​", "‎", "‮", "⁦", "﻿", "⁠"],
)
def test_invisible_and_bidi_controls_are_removed(invisible: str) -> None:
    assert scrub_tts_hazards(f"a{invisible}b") == "ab"


def test_a_normal_accent_survives_but_a_combining_stack_does_not() -> None:
    assert scrub_tts_hazards("é") == "é"
    zalgo = "e" + "́" * 30
    scrubbed = scrub_tts_hazards(zalgo)
    assert scrubbed == "e" + "́́"


def test_decorative_box_drawing_becomes_a_space() -> None:
    assert scrub_tts_hazards("Total ──────── 5") == "Total 5"
    assert scrub_tts_hazards("███ done") == "done"


def test_repeated_punctuation_collapses_to_three() -> None:
    assert scrub_tts_hazards("Wait!!!!!!!!!!") == "Wait!!!"
    assert scrub_tts_hazards("really????") == "really???"


def test_a_very_long_unbroken_token_is_truncated() -> None:
    blob = "a" * 200
    scrubbed = scrub_tts_hazards(blob)
    assert scrubbed.endswith("…")
    assert len(scrubbed) == 61


def test_a_normal_url_is_left_intact() -> None:
    url = "https://example.test/guide"
    assert scrub_tts_hazards(url) == url


def test_runs_of_spaces_collapse_but_newlines_survive() -> None:
    assert scrub_tts_hazards("a     b") == "a b"
    assert scrub_tts_hazards("a\n\n\n\n\nb") == "a\n\nb"


# -- html_to_speech_text -----------------------------------------------------


def test_paragraphs_and_breaks_become_line_breaks() -> None:
    assert html_to_speech_text("<p>one</p><p>two</p>") == "one\ntwo"
    assert html_to_speech_text("one<br>two") == "one\ntwo"


def test_entities_are_decoded() -> None:
    assert html_to_speech_text("<p>Tom &amp; Jerry &#8212; friends</p>") == "Tom & Jerry — friends"


def test_mastodon_invisible_spans_are_not_spoken() -> None:
    # Mastodon hides the scheme and the tail of a link; a naive tag strip reads
    # the whole raw URL, which is exactly what the sender's client hid.
    markup = (
        '<p>Read <a href="https://example.test/a/very/long/path">'
        '<span class="invisible">https://</span>'
        '<span class="ellipsis">example.test/a</span>'
        '<span class="invisible">/very/long/path</span></a></p>'
    )
    assert html_to_speech_text(markup) == "Read example.test/a"


def test_custom_emoji_contributes_its_shortcode() -> None:
    markup = '<p>hello <img class="custom-emoji" alt=":wave:" src="w.png"></p>'
    assert html_to_speech_text(markup) == "hello :wave:"


def test_script_and_style_bodies_are_dropped() -> None:
    markup = "<p>keep</p><script>alert(1)</script><style>p{color:red}</style>"
    assert html_to_speech_text(markup) == "keep"


def test_malformed_markup_degrades_to_a_tag_strip() -> None:
    assert "bio" in html_to_speech_text("<p>bio<<<</p")


def test_plain_text_passes_through_unchanged() -> None:
    assert html_to_speech_text("no markup here") == "no markup here"


# -- condense_leading_mentions -----------------------------------------------


def test_a_pile_of_leading_mentions_becomes_a_count() -> None:
    # Three handles read aloud before the first word of the actual reply.
    assert (
        condense_leading_mentions("@alice @bob @carol Actually, no.")
        == "@alice and 2 more Actually, no."
    )


def test_two_leading_mentions_use_the_singular() -> None:
    assert condense_leading_mentions("@alice @bob Hi") == "@alice and one more Hi"


def test_a_single_leading_mention_is_left_alone() -> None:
    # One handle is address information, and in a reply it is the point.
    assert condense_leading_mentions("@alice Actually, no.") == "@alice Actually, no."


def test_text_with_no_leading_mention_is_unchanged() -> None:
    assert condense_leading_mentions("Just a post.") == "Just a post."
    assert condense_leading_mentions("Ask @alice about it") == "Ask @alice about it"


def test_a_post_that_is_only_mentions_still_counts_the_last_one() -> None:
    assert condense_leading_mentions("@alice @bob @carol") == "@alice and 2 more"


def test_full_handles_and_a_multiline_body_survive() -> None:
    assert (
        condense_leading_mentions("@a@x.test @b@y.test line one\nline two")
        == "@a@x.test and one more line one\nline two"
    )


# -- strip_decorative_unicode ------------------------------------------------


def test_emoji_are_removed_from_a_display_name() -> None:
    # Names are where decorated text collects, and a name is announced
    # constantly -- in every list row and every notification.
    assert strip_decorative_unicode("😄 Alice 🎉") == "Alice"
    assert strip_decorative_unicode("Bob 👍🏽") == "Bob"


def test_a_zero_width_joiner_sequence_leaves_nothing_behind() -> None:
    assert strip_decorative_unicode("Team 👨‍👩‍👧 here") == "Team here"


def test_a_variation_selector_does_not_survive_its_emoji() -> None:
    assert strip_decorative_unicode("love ❤️ it") == "love it"


def test_accented_latin_and_other_scripts_are_kept() -> None:
    assert strip_decorative_unicode("Zoë Müller") == "Zoë Müller"
    assert strip_decorative_unicode("Ольга") == "Ольга"
    assert strip_decorative_unicode("日本語") == "日本語"


def test_ordinary_punctuation_and_currency_are_kept() -> None:
    assert strip_decorative_unicode("“Yes” — really… €5") == "“Yes” — really… €5"


def test_a_name_of_pure_emoji_becomes_empty_so_callers_can_fall_back() -> None:
    assert strip_decorative_unicode("🌻🌻🌻") == ""


# -- first_sentence ----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("One thing. Then another.", "One thing."),
        ("Really? Yes.", "Really?"),
        ("Stop! Now go.", "Stop!"),
        ('He said "no." Then left.', 'He said "no."'),
        ("(A note.) More.", "(A note.)"),
        ("Wait... then go.", "Wait..."),
    ],
)
def test_the_first_sentence_ends_at_its_own_terminator(text: str, expected: str) -> None:
    assert first_sentence(text) == expected


def test_a_decimal_or_a_url_is_not_a_sentence_end() -> None:
    assert first_sentence("It costs 3.50 today. Tomorrow more.") == "It costs 3.50 today."
    assert first_sentence("See example.test/a for it. Later.") == "See example.test/a for it."


def test_a_common_abbreviation_does_not_end_the_sentence() -> None:
    assert first_sentence("Dr. Smith arrived. Then left.") == "Dr. Smith arrived."
    assert first_sentence("Bring a coat, e.g. a parka. Then go.") == "Bring a coat, e.g. a parka."


def test_a_line_break_ends_a_sentence_that_has_no_full_stop() -> None:
    assert first_sentence("A headline\nthe body follows") == "A headline"


def test_text_with_no_terminator_is_returned_whole() -> None:
    assert first_sentence("no terminator here") == "no terminator here"
    assert first_sentence("   ") == ""


# -- format_relative_time ----------------------------------------------------

_NOW = datetime(2026, 8, 2, 12, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (timedelta(seconds=0), "just now"),
        (timedelta(seconds=-10), "just now"),
        (timedelta(seconds=30), "just now"),
        (timedelta(seconds=-50), "50 seconds ago"),
        (timedelta(minutes=-1), "1 minute ago"),
        (timedelta(minutes=-3), "3 minutes ago"),
        (timedelta(hours=-1), "1 hour ago"),
        (timedelta(hours=-5), "5 hours ago"),
        (timedelta(days=-1), "1 day ago"),
        (timedelta(days=-3), "3 days ago"),
        (timedelta(days=-14), "2 weeks ago"),
        (timedelta(days=-60), "1 month ago"),
        (timedelta(days=-800), "2 years ago"),
        (timedelta(minutes=90), "in 1 hour"),
        (timedelta(hours=2), "in 2 hours"),
        (timedelta(minutes=1), "in 1 minute"),
    ],
)
def test_relative_time_reads_naturally_in_both_directions(delta: timedelta, expected: str) -> None:
    assert format_relative_time(_NOW + delta, _NOW) == expected


def test_a_naive_timestamp_is_read_as_utc_instead_of_raising() -> None:
    naive = datetime(2026, 8, 2, 11, 55, 0)
    assert format_relative_time(naive, _NOW) == "5 minutes ago"
    assert format_relative_time(_NOW, naive) == "in 5 minutes"


# -- prepare_for_speech ------------------------------------------------------


def test_funnel_scrubs_hazards_by_default_without_touching_markdown() -> None:
    assert prepare_for_speech("**bold**​") == "**bold**"


def test_funnel_applies_markdown_when_asked() -> None:
    assert prepare_for_speech("**bold**", markdown=True) == "bold"


def test_funnel_flattens_html_then_scrubs() -> None:
    markup = '<p>hi​<span class="invisible">https://</span>example.test</p>'
    assert prepare_for_speech(markup, html=True) == "hiexample.test"


def test_funnel_handles_markdown_inside_html() -> None:
    # An AI response rendered into HTML can still carry Markdown emphasis.
    assert prepare_for_speech("<p>a **bold** claim</p>", html=True, markdown=True) == "a bold claim"


# -- durations (5a.10) -------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds", "spoken"),
    [
        (0, "0 seconds"),
        (0.4, "0 seconds"),
        (1, "1 second"),
        (59, "59 seconds"),
        (60, "1 minute"),
        (61, "1 minute 1 second"),
        (192, "3 minutes 12 seconds"),
        (3600, "1 hour"),
        (3605, "1 hour 5 seconds"),
        (7325, "2 hours 2 minutes 5 seconds"),
    ],
)
def test_spoken_duration_reads_naturally(seconds: float, spoken: str) -> None:
    assert speak_duration(seconds) == spoken


@pytest.mark.parametrize(
    ("seconds", "clock"),
    [(0, "00:00:00"), (192, "00:03:12"), (3605, "01:00:05"), (360000, "100:00:00")],
)
def test_clock_duration_is_pastable_and_sorts_as_a_string(seconds: float, clock: str) -> None:
    assert clock_duration(seconds) == clock


def test_negative_durations_clamp_to_zero() -> None:
    assert speak_duration(-5) == "0 seconds"
    assert clock_duration(-5) == "00:00:00"
