"""Pulling the links out of show notes and transcripts.

The problem these answer: an address in a read-only text box is a string of
characters to read out and retype, which is the least accessible possible way
to follow a link (reported 2026-08-18). Everything here feeds one list with an
Open and a Copy on it.
"""

from __future__ import annotations

from quill.core.text_links import Link, describe, find_links, links_in_html, links_in_text


def test_a_linked_address_keeps_the_words_that_explained_it() -> None:
    html = '<p>Read <a href="https://arxiv.org/abs/2408.01234">the paper we discussed</a>.</p>'

    links = links_in_html(html)

    assert [link.url for link in links] == ["https://arxiv.org/abs/2408.01234"]
    assert links[0].label == "the paper we discussed -- https://arxiv.org/abs/2408.01234"


def test_a_row_says_the_name_and_the_address_not_one_or_the_other() -> None:
    # The name alone hides where a link goes; the address alone is unskimmable.
    named = Link(url="https://example.com/a", text="Sponsor")
    bare = Link(url="https://example.com/b")

    assert named.label == "Sponsor -- https://example.com/a"
    assert bare.label == "https://example.com/b"


def test_a_hand_typed_address_in_show_notes_is_found_too() -> None:
    # Most show notes are half real anchors and half addresses somebody typed.
    html = "<p>Everything is at https://example.com/links</p>"

    assert [link.url for link in links_in_html(html)] == ["https://example.com/links"]


def test_the_same_place_linked_twice_is_one_row() -> None:
    html = (
        '<p><a href="https://sponsor.example">Acme</a> sponsors us.</p>'
        '<p>Again: <a href="https://sponsor.example/">Acme</a></p>'
    )

    links = links_in_html(html)

    assert len(links) == 1
    # ...and the first mention's words win, because that is where it was explained.
    assert links[0].text == "Acme"


def test_a_sentence_full_stop_is_not_part_of_the_address() -> None:
    assert links_in_text("See https://example.com/thing.")[0].url == "https://example.com/thing"
    assert links_in_text("(https://example.com/x)")[0].url == "https://example.com/x"


def test_balanced_brackets_inside_an_address_survive() -> None:
    # Excluding brackets outright truncated every Wikipedia link.
    text = "https://en.wikipedia.org/wiki/Turing_(disambiguation) is the one"

    assert links_in_text(text)[0].url == "https://en.wikipedia.org/wiki/Turing_(disambiguation)"


def test_only_addresses_a_browser_can_open_are_offered() -> None:
    html = (
        '<a href="javascript:void(0)">no</a>'
        '<a href="file:///C:/secret.txt">no</a>'
        '<a href="mailto:someone@example.com">no</a>'
        '<a href="https://yes.example">yes</a>'
    )

    assert [link.url for link in links_in_html(html)] == ["https://yes.example"]


def test_malformed_html_answers_rather_than_raising() -> None:
    # Somebody else's show notes must never crash a menu.
    assert links_in_html("<p><a href=https://x.example>unquoted<p></a></div>")
    assert links_in_html("") == []
    assert links_in_text("") == []


def test_find_links_reads_plain_text_as_plain_text() -> None:
    # A transcript is prose, not markup: an angle bracket in speech is not a tag.
    spoken = "she said go to https://example.com/one and then https://example.com/two"

    assert len(find_links(spoken)) == 2
    assert len(find_links(spoken, is_html=True)) == 2


def test_the_count_is_said_in_words_including_when_there_is_nothing() -> None:
    assert describe([]) == "No links here."
    assert describe([Link(url="https://a.example")]) == "1 link."
    assert describe([Link(url="https://a.example"), Link(url="https://b.example")]) == "2 links."
