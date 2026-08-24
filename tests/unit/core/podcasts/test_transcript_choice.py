"""Which transcript a feed's several get read (list.md 2.6).

QUILL took the first ``<podcast:transcript>`` tag it matched, whatever its
type -- so the choice belonged to whoever wrote the feed's element order. A
publisher who listed HTML first silently cost their listeners the timed
transcript reader, the chapter cascade's transcript tier and Markdown
timestamps, on every episode, with no error anywhere.

The order is by what a format *can do*, not by taste: JSON and WebVTT carry cue
times, SRT carries times, HTML carries only the words. And an unrecognised
format still gets used, because refusing it would lose the words to protect the
timings.
"""

from __future__ import annotations

from quill.core.podcasts import transcript_choice as tc
from quill.core.podcasts.feed_reader import _episode_extra_tags


def _tag(url: str, kind: str = "") -> str:
    type_attr = f' type="{kind}"' if kind else ""
    return f'<podcast:transcript url="{url}"{type_attr} />'


# -- the ranking ------------------------------------------------------------------


def test_structured_formats_outrank_html() -> None:
    assert tc.rank("application/json") < tc.rank("text/html")
    assert tc.rank("text/vtt") < tc.rank("text/html")
    assert tc.rank("application/x-subrip") < tc.rank("text/html")


def test_json_outranks_vtt_and_vtt_outranks_srt() -> None:
    assert tc.rank("application/json") < tc.rank("text/vtt") < tc.rank("application/x-subrip")


def test_an_unrecognised_type_sorts_last_but_is_still_usable() -> None:
    """Refusing it would lose the words to protect the timings."""
    assert tc.rank("application/x-martian") > tc.rank("text/html")
    assert tc.best([("https://e/t.mars", "application/x-martian")])[0] == "https://e/t.mars"


def test_a_missing_type_falls_back_to_the_file_extension() -> None:
    """Omitting the attribute is legal and common; the publisher still named
    the file."""
    assert tc.rank("", "https://e/show.vtt") == tc.rank("text/vtt")
    assert tc.rank("", "https://e/show.json") == tc.rank("application/json")
    assert tc.rank("", "https://e/show.html") == tc.rank("text/html")


def test_a_query_string_does_not_hide_the_extension() -> None:
    assert tc.rank("", "https://e/show.vtt?token=abc") == tc.rank("text/vtt")


def test_a_declared_type_beats_the_extension() -> None:
    """A publisher who said what it is has said what it is."""
    assert tc.rank("application/json", "https://e/show.html") == tc.rank("application/json")


def test_an_address_with_no_extension_at_all_is_not_a_crash() -> None:
    assert tc.rank("", "https://example.com/transcripts/412") > tc.rank("text/html")


# -- choosing ---------------------------------------------------------------------


def test_the_structured_one_wins_however_the_feed_ordered_them() -> None:
    """The bug, in one line: HTML first must not mean HTML chosen."""
    url, kind = tc.best([
        ("https://e/t.html", "text/html"),
        ("https://e/t.vtt", "text/vtt"),
    ])

    assert url == "https://e/t.vtt"
    assert kind == "text/vtt"


def test_html_is_taken_when_it_is_genuinely_all_there_is() -> None:
    assert tc.best([("https://e/t.html", "text/html")])[0] == "https://e/t.html"


def test_nothing_offered_is_two_empty_strings() -> None:
    assert tc.best([]) == ("", "")


def test_a_tag_with_no_address_is_not_a_representation() -> None:
    assert tc.best([("", "application/json"), ("https://e/t.html", "text/html")])[0] == (
        "https://e/t.html"
    )


def test_a_tie_keeps_the_publishers_own_order() -> None:
    """Among equals, the feed's order is the publisher's preference."""
    url, _kind = tc.best([
        ("https://e/first.vtt", "text/vtt"),
        ("https://e/second.vtt", "text/vtt"),
    ])
    assert url == "https://e/first.vtt"


# -- what a caller really wants to know -------------------------------------------


def test_the_structured_formats_are_the_ones_with_timings() -> None:
    assert tc.carries_timings("application/json") is True
    assert tc.carries_timings("text/vtt") is True
    assert tc.carries_timings("application/x-subrip") is True


def test_html_is_not_dependably_timed_and_says_so() -> None:
    """HTML sometimes carries cue times. "Sometimes" is not something a
    follow-along reader can be built on."""
    assert tc.carries_timings("text/html") is False
    assert tc.carries_timings("application/x-martian") is False


# -- the feed reader uses it ------------------------------------------------------


def test_the_feed_reader_now_looks_at_every_tag() -> None:
    entry = (
        f"<item>{_tag('https://e/t.html', 'text/html')}{_tag('https://e/t.vtt', 'text/vtt')}</item>"
    )

    _chapters, url, kind = _episode_extra_tags(entry)

    assert url == "https://e/t.vtt"
    assert kind == "text/vtt"


def test_a_single_transcript_still_reads_exactly_as_before() -> None:
    entry = f"<item>{_tag('https://e/t.srt', 'application/x-subrip')}</item>"

    _chapters, url, kind = _episode_extra_tags(entry)

    assert url == "https://e/t.srt"
    assert kind == "application/x-subrip"


def test_an_episode_with_no_transcript_is_unchanged() -> None:
    _chapters, url, kind = _episode_extra_tags("<item><title>X</title></item>")
    assert (url, kind) == ("", "")


def test_choosing_a_transcript_never_disturbs_the_chapters_tag() -> None:
    html = _tag("https://e/t.html", "text/html")
    json_tag = _tag("https://e/t.json", "application/json")
    entry = (
        '<item><podcast:chapters url="https://e/c.json" type="application/json" />'
        f"{html}{json_tag}</item>"
    )

    chapters, url, _kind = _episode_extra_tags(entry)

    assert chapters == "https://e/c.json"
    assert url == "https://e/t.json"
