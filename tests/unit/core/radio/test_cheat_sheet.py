"""The shortcut sheet lists the keys you actually have.

Quill Radio 3.0 made every menu item name its own key, which fixed discovery
inside a menu and left "open six menus and arrow to the end of each" as the only
way to see them together. The documentation route is worse: a listener who
rebound anything is then reading a list of somebody else's keys.

The trap these guard is the second copy. The rows come off the live menu bar
rather than the keymap or a hand-kept table, so the sheet cannot drift from the
menus -- it *is* the menus.
"""

from __future__ import annotations

from quill.core.radio.cheat_sheet import (
    CheatRow,
    build_sheet,
    clean_label,
    filter_rows,
    off_menu_rows,
    rows_from_menu_items,
    summary,
)


def test_a_menu_label_is_cleaned_into_something_speakable() -> None:
    assert clean_label("&Browse Stations...\tCtrl+B") == "Browse Stations"
    assert clean_label("&Play") == "Play"
    assert clean_label("Report a &Bug...") == "Report a Bug"


def test_a_literal_ampersand_survives_the_mnemonic_stripping() -> None:
    # "&&" is how wx spells one ampersand, and losing it would rename the item.
    assert clean_label("Rock && Roll\tCtrl+R") == "Rock & Roll"


def test_rows_carry_the_menu_the_action_and_the_key() -> None:
    rows = rows_from_menu_items([("&Playback", "&Play/Stop\tCtrl+P")])
    assert rows == [CheatRow(group="Playback", action="Play/Stop", key="Ctrl+P")]


def test_an_item_with_no_key_is_dropped_rather_than_listed_blank() -> None:
    # The accelerator gate means an enabled item always has one, so anything
    # without a key is a disabled status readout -- not something to press.
    assert rows_from_menu_items([("&View", "Nothing is playing")]) == []
    assert rows_from_menu_items([("&View", "Something\t  ")]) == []


def test_the_sheet_keeps_menu_order_rather_than_sorting_by_name() -> None:
    # The menus already group by what things are; re-sorting alphabetically
    # would scatter that into an index.
    rows = build_sheet([
        ("&Station", "&Browse...\tCtrl+B"),
        ("&Playback", "&Zoom\tCtrl+Z"),
        ("&Playback", "&Announce\tCtrl+A"),
    ])
    assert [row.action for row in rows[:3]] == ["Browse", "Zoom", "Announce"]


def test_keys_with_no_menu_item_are_included_and_say_where_they_work() -> None:
    rows = off_menu_rows()
    assert any(row.key == "F6" for row in rows)
    winamp = [row for row in rows if row.group == "Recordings"]
    assert {"X", "C", "V", "B", "Z"} <= {row.key for row in winamp}
    # "Where does this key work?" is the first thing to know about a key that
    # only works in one window.
    assert all(row.group for row in rows)


def test_the_sheet_ends_with_the_off_menu_keys() -> None:
    rows = build_sheet([("&Station", "&Browse...\tCtrl+B")])
    assert rows[0].action == "Browse"
    assert rows[-1].group in {row.group for row in off_menu_rows()}


def test_filtering_matches_the_action_the_key_and_the_menu() -> None:
    rows = [
        CheatRow("Playback", "Play/Stop", "Ctrl+P"),
        CheatRow("Station", "Browse Stations", "Ctrl+B"),
        CheatRow("Recordings", "Next recording", "B"),
    ]
    # By what you want to do...
    assert [r.action for r in filter_rows(rows, "browse")] == ["Browse Stations"]
    # ...and by the key, because "what is Ctrl+B?" is as common a question.
    assert [r.action for r in filter_rows(rows, "ctrl+b")] == ["Browse Stations"]
    # ...and by where it lives.
    assert [r.action for r in filter_rows(rows, "recordings")] == ["Next recording"]


def test_filtering_is_case_insensitive_and_an_empty_query_shows_everything() -> None:
    rows = [CheatRow("Playback", "Play/Stop", "Ctrl+P")]
    assert filter_rows(rows, "PLAY") == rows
    assert filter_rows(rows, "   ") == rows


def test_the_summary_says_when_a_filter_is_hiding_rows() -> None:
    # A filtered list that does not say so is how somebody concludes a key does
    # not exist when it is simply not matching what they typed.
    rows = [CheatRow("Playback", "Play/Stop", "Ctrl+P")]
    assert summary(rows, 1) == "1 keys."
    assert summary(rows, 40) == "1 of 40 keys."
    assert "Clear the box" in summary([], 40)


def test_a_row_leads_with_the_action_not_the_key() -> None:
    # Somebody scanning this is looking for a thing they want to do.
    row = CheatRow("Playback", "Play/Stop", "Ctrl+P")
    assert row.spoken() == "Playback: Play/Stop -- Ctrl+P"
