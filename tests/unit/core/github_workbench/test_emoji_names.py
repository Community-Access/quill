"""Emoji shortcodes read by name (GitHub PRD 22.12)."""

from __future__ import annotations

from quill.core.github.emoji_names import name_for, name_shortcodes


def test_github_aliases_and_catalogue_names() -> None:
    assert name_for(":tada:") == "party popper"
    assert name_for("+1") == "thumbs up"
    assert name_for("thumbs_up") == "thumbs up"
    assert name_for("grinning_face") == "grinning face"
    assert name_for("not_an_emoji_at_all") == ""


def test_shortcodes_in_text_are_named_and_code_is_left_alone() -> None:
    text = "Shipped :rocket: :tada:! Use `:rocket:` in code.\n```\n:+1:\n```\nThanks :+1:"
    assert name_shortcodes(text) == (
        "Shipped rocket party popper! Use `:rocket:` in code.\n```\n:+1:\n```\nThanks thumbs up"
    )


def test_unknown_codes_times_and_words_with_colons_stay() -> None:
    assert name_shortcodes("At 10:30:45 see :nonsense_word: and http://x:80/") == (
        "At 10:30:45 see :nonsense_word: and http://x:80/"
    )
