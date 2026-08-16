"""Importing the channels you already follow, from your own Takeout export.

The listener's question was "can I sign in with my YouTube account, and will it
sync my history?" -- both no, by Google's own documentation. What was actually
wanted is here instead, and with no account involved at all: a CSV the listener
exports themselves, read into the channel branch they already have.

Pinned here is the tolerance, because a real export passes through spreadsheets
and email on its way to us: a missing header, reordered or extra columns, a
BOM, quoted commas, a bare channel id where the URL was lost, and rows that are
not channels at all. Losing ninety-nine good rows to one odd one would make the
feature worse than pasting the addresses by hand.
"""

from __future__ import annotations

from quill.core.radio.youtube_takeout import parse_subscriptions

TAKEOUT = (
    "Channel ID,Channel URL,Channel title\n"
    "UCg6gPGh8HU2U01vaFCAsvmQ,http://www.youtube.com/channel/UCg6gPGh8HU2U01vaFCAsvmQ,"
    "Chris Titus Tech\n"
    "UC4a-Gbdw7vOaccHmFo40b9g,http://www.youtube.com/channel/UC4a-Gbdw7vOaccHmFo40b9g,"
    "Khan Academy\n"
)


def test_a_real_takeout_export_imports() -> None:
    channels = parse_subscriptions(TAKEOUT)
    assert [c.name for c in channels] == ["Chris Titus Tech", "Khan Academy"]
    assert channels[0].url == "https://www.youtube.com/channel/UCg6gPGh8HU2U01vaFCAsvmQ"
    # http:// in the export, https:// in the store: normalized on the way in.
    assert all(c.url.startswith("https://") for c in channels)


def test_a_byte_order_mark_does_not_hide_the_header() -> None:
    """Excel writes one; without handling it the first column stops matching."""
    channels = parse_subscriptions("﻿" + TAKEOUT)
    assert len(channels) == 2
    assert channels[0].name == "Chris Titus Tech"


def test_columns_may_arrive_in_any_order() -> None:
    text = (
        "Channel title,Channel ID,Channel URL\n"
        "Khan Academy,UC4a-Gbdw7vOaccHmFo40b9g,"
        "https://www.youtube.com/channel/UC4a-Gbdw7vOaccHmFo40b9g\n"
    )
    channels = parse_subscriptions(text)
    assert len(channels) == 1
    assert channels[0].name == "Khan Academy"
    assert channels[0].url.endswith("UC4a-Gbdw7vOaccHmFo40b9g")


def test_a_lost_url_column_falls_back_to_the_channel_id() -> None:
    """A spreadsheet round trip loses columns; the id still names the channel."""
    text = "Channel ID,Channel title\nUC4a-Gbdw7vOaccHmFo40b9g,Khan Academy\n"
    channels = parse_subscriptions(text)
    assert len(channels) == 1
    assert channels[0].url == "https://www.youtube.com/channel/UC4a-Gbdw7vOaccHmFo40b9g"
    assert channels[0].name == "Khan Academy"


def test_a_file_with_no_header_still_imports() -> None:
    text = (
        "UCg6gPGh8HU2U01vaFCAsvmQ,https://www.youtube.com/channel/UCg6gPGh8HU2U01vaFCAsvmQ,"
        "Chris Titus Tech\n"
    )
    channels = parse_subscriptions(text)
    assert len(channels) == 1
    assert channels[0].url.endswith("UCg6gPGh8HU2U01vaFCAsvmQ")
    assert channels[0].name == "Chris Titus Tech"


def test_a_comma_in_a_channel_name_survives() -> None:
    text = (
        "Channel ID,Channel URL,Channel title\n"
        'UCabcdefghij,https://www.youtube.com/channel/UCabcdefghij,"Lewis, Clark and Co"\n'
    )
    channels = parse_subscriptions(text)
    assert channels[0].name == "Lewis, Clark and Co"


def test_one_bad_row_never_costs_the_good_ones() -> None:
    text = (
        "Channel ID,Channel URL,Channel title\n"
        "UCg6gPGh8HU2U01vaFCAsvmQ,https://www.youtube.com/channel/UCg6gPGh8HU2U01vaFCAsvmQ,Good\n"
        ",,\n"
        "not-an-id,not a url at all,Nonsense\n"
        "UC4a-Gbdw7vOaccHmFo40b9g,https://www.youtube.com/channel/UC4a-Gbdw7vOaccHmFo40b9g,Also\n"
    )
    assert [c.name for c in parse_subscriptions(text)] == ["Good", "Also"]


def test_the_same_channel_twice_is_imported_once() -> None:
    text = TAKEOUT + (
        "UCg6gPGh8HU2U01vaFCAsvmQ,http://www.youtube.com/channel/UCg6gPGh8HU2U01vaFCAsvmQ,"
        "Chris Titus Tech\n"
    )
    assert len(parse_subscriptions(text)) == 2


def test_a_video_link_is_not_a_channel() -> None:
    """normalize_channel_url refuses these deliberately: following a channel
    the listener never chose would be worse than importing nothing."""
    text = "Channel URL,Channel title\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ,Not a channel\n"
    assert parse_subscriptions(text) == []


def test_junk_and_empty_input_answer_empty_rather_than_raising() -> None:
    for text in ("", "   \n\n", "\x00\x01\x02", "not,a,subscriptions,file\n"):
        assert isinstance(parse_subscriptions(text), list)


def test_a_handle_export_is_accepted() -> None:
    """Some exporters write the @handle rather than the /channel/ URL."""
    text = "Channel URL,Channel title\nhttps://www.youtube.com/@TED,TED\n"
    channels = parse_subscriptions(text)
    assert len(channels) == 1 and channels[0].url == "https://www.youtube.com/@TED"
