"""Numbered messages, the recent ten, and reply headings that nest under the
speaker (todo item 44). Shared by Ask Quill and the AI Conversation window."""

from __future__ import annotations

import pytest

from quill.core.ai.chat_navigation import (
    RECENT_COUNT,
    message_view_html,
    nest_reply_headings,
    number_messages,
    recent_key_label,
    recent_message,
    recent_message_sentence,
    row_label,
)

TWELVE = [("You" if i % 2 == 0 else "AI", f"Message text {i + 1}") for i in range(12)]


def test_messages_are_numbered_from_the_first_with_their_speaker() -> None:
    messages = number_messages([("You", "Hi"), ("AI", "Hello.")])
    assert [m.position for m in messages] == ["Message 1 of 2, You", "Message 2 of 2, AI"]


def test_a_blank_speaker_is_never_silent() -> None:
    assert number_messages([("", "x")])[0].speaker == "Unknown"


def test_alt_1_is_the_newest_and_alt_0_the_tenth_newest() -> None:
    messages = number_messages(TWELVE)
    assert recent_message(messages, 1).number == 12
    assert recent_message(messages, 10).number == 3
    assert [recent_key_label(n) for n in (1, 9, 10)] == ["Alt+1", "Alt+9", "Alt+0"]
    assert RECENT_COUNT == 10


def test_the_sentence_names_speaker_and_place() -> None:
    messages = number_messages(TWELVE)
    assert recent_message_sentence(messages, 1) == "Newest, Message 12 of 12, AI: Message text 12"
    assert recent_message_sentence(messages, 2) == "Message 11 of 12, You: Message text 11"


def test_the_sentence_is_words_not_markdown() -> None:
    messages = number_messages([("AI", "## Plan\n\n**Bold** idea")])
    said = recent_message_sentence(messages, 1)
    assert "#" not in said and "*" not in said
    assert "Plan" in said and "Bold idea" in said


@pytest.mark.parametrize(
    ("pairs", "n", "expected"),
    [
        ([], 1, "No messages yet."),
        ([("You", "Hi")], 2, "There is only 1 message so far. Alt+1 reads the oldest."),
        (
            [("You", "a"), ("AI", "b"), ("You", "c")],
            7,
            "There are only 3 messages so far. Alt+3 reads the oldest.",
        ),
    ],
)
def test_fewer_messages_than_the_key_asks_for_says_how_many(pairs, n, expected) -> None:
    assert recent_message_sentence(number_messages(pairs), n) == expected


def test_no_key_past_the_tenth() -> None:
    with pytest.raises(ValueError):
        recent_key_label(11)


def test_a_row_is_one_line_with_the_position_first() -> None:
    message = number_messages([("AI", "Line one\nline two " + "word " * 40)])[0]
    label = row_label(message)
    assert label.startswith("Message 1 of 1, AI: Line one line two")
    assert "\n" not in label and label.endswith("...")


def test_reply_headings_nest_below_the_speaker_heading() -> None:
    nested = nest_reply_headings("# Title\n\ntext\n\n## Part\n\n### Detail")
    assert nested.splitlines()[0] == "### Title"
    assert "#### Part" in nested and "##### Detail" in nested


def test_nesting_never_goes_past_level_six() -> None:
    assert nest_reply_headings("# A\n\n###### Deep") == "### A\n\n###### Deep"


def test_fenced_code_is_never_a_heading() -> None:
    reply = "## Steps\n\n```python\n# a comment\n```"
    nested = nest_reply_headings(reply)
    assert "### Steps" in nested
    assert "# a comment" in nested and "### a comment" not in nested


def test_text_without_headings_is_unchanged() -> None:
    assert nest_reply_headings("plain\ntext") == "plain\ntext"
    assert nest_reply_headings("### already deep") == "### already deep"


def test_the_viewer_has_a_heading_and_a_real_table() -> None:
    reply = "# Pets\n\n| Pet | Sound |\n| --- | --- |\n| Cat | Meow |"
    html = message_view_html(number_messages([("You", "q"), ("AI", reply)])[1])
    assert html.startswith("<h2>Message 2 of 2, AI</h2>")
    assert "<h3" in html and "<h1" not in html
    assert "<th>Pet</th>" in html and "<td>Meow</td>" in html
