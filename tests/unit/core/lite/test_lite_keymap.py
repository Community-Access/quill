"""QUILL Lite's keymap layer: defaults from the table, overrides in a file.

The three properties this file exists to hold, because each has a cheap wrong
version that would pass a casual reading:

* **The table is still the defaults.** Nothing was copied into a second list
  that could fall out of step with the menu bar.
* **The stored file is a delta, never a snapshot.** A snapshot would freeze
  today's keys into a profile forever, so a key improved in a later version
  would never reach anybody who had launched the app once.
* **A chord's identity ignores modifier spelling.** ``Ctrl+Alt+Shift+H`` and
  ``Ctrl+Shift+Alt+H`` are one key to wx and to the keyboard; comparing the raw
  strings let a collision through review once.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.lite.commands import COMMANDS
from quill.core.lite.keymap import (
    KEYMAP_FILE,
    RESERVED_KEYS,
    audit_keymap,
    binding_for,
    chord_identity,
    command_titles,
    conflicting_handlers,
    default_keymap,
    describe_binding_problem,
    load_keymap,
    normalise_chord,
    resolved_commands,
    save_keymap,
)

ALL_ON = lambda _area: True  # noqa: E731 - a fixture value, not a function


# ---------------------------------------------------------------------------
# chords


@pytest.mark.parametrize(
    ("typed", "canonical"),
    [
        ("Ctrl+S", "Ctrl+S"),
        ("ctrl+s", "Ctrl+S"),
        ("shift+ctrl+s", "Ctrl+Shift+S"),
        ("Control+Alt+Shift+E", "Ctrl+Shift+Alt+E"),
        ("f7", "F7"),
        ("ctrl+f7", "Ctrl+F7"),
        ("alt+left", "Alt+Left"),
        ("ctrl+pgdn", "Ctrl+PageDown"),
        ("ctrl+enter", "Ctrl+Return"),
        ("Ctrl+,", "Ctrl+,"),
    ],
)
def test_a_chord_normalises_to_what_wx_renders(typed: str, canonical: str) -> None:
    assert normalise_chord(typed) == canonical


@pytest.mark.parametrize("junk", ["", "   ", "Ctrl", "Ctrl+A+B", "Ctrl+Nonsense", "+"])
def test_nonsense_is_not_a_chord(junk: str) -> None:
    assert normalise_chord(junk) == ""


def test_modifier_order_does_not_make_two_keys() -> None:
    assert chord_identity("Ctrl+Alt+Shift+H") == chord_identity("Ctrl+Shift+Alt+H")
    assert chord_identity("Ctrl+Alt+Shift+H") == chord_identity("shift+alt+control+h")


def test_two_unreadable_strings_still_compare_equal() -> None:
    """Otherwise two identical broken bindings look like two free keys."""
    assert chord_identity("Ctrl+Nonsense") == chord_identity(" ctrl+nonsense ")


# ---------------------------------------------------------------------------
# refusals


def test_insert_can_never_be_bound() -> None:
    """It is NVDA's and JAWS's own modifier."""
    problem = describe_binding_problem("Insert")
    assert problem == RESERVED_KEYS["Insert"]
    assert "NVDA" in problem


def test_a_modified_insert_is_refused_too() -> None:
    assert describe_binding_problem("Ctrl+Insert") == RESERVED_KEYS["Insert"]


def test_a_bare_letter_is_refused_with_the_reason() -> None:
    assert "would type the character" in describe_binding_problem("K")


def test_shift_alone_is_not_enough_to_make_a_letter_safe() -> None:
    """Shift+A fires when the capital is typed, for the same reason K does.

    The advice used to read "Add Ctrl, Alt or Shift", which was wrong about the
    third one (bad.md H1).
    """
    assert "would type the character" in describe_binding_problem("Shift+A")


def test_the_windows_key_is_refused_and_says_why() -> None:
    """wx accepts Win+A, returns True, and hands back a BARE A.

    So a hand-edited keymap saying {"cmd_delete_line": "Win+A"} ran Delete Line
    every time the user typed the letter A -- no failure, no warning.
    """
    for chord in ("Win+A", "Cmd+A", "Windows+Z", "Command+7"):
        assert "Windows key" in describe_binding_problem(chord), chord


def test_a_real_chord_is_not_refused() -> None:
    assert describe_binding_problem("Ctrl+Alt+Shift+R") == ""


def test_an_unreadable_chord_says_so() -> None:
    assert "not a key combination" in describe_binding_problem("Ctrl+Nonsense")


def test_an_empty_box_asks_rather_than_complains() -> None:
    assert describe_binding_problem("") == "Press the key combination you want to use."


# ---------------------------------------------------------------------------
# the defaults are the table


def test_the_defaults_come_from_the_command_table() -> None:
    from_table = {
        handler: key
        for _menu, _label, key, handler, kind in COMMANDS
        if kind not in {"sep", "sub"} and handler and key
    }
    assert default_keymap() == from_table


def test_every_command_has_a_title_with_its_menu_path() -> None:
    titles = command_titles()
    assert titles["cmd_sort_lines"] == "Edit > Lines > Sort Lines A to Z"
    assert titles["cmd_save"] == "File > Save"


def test_a_title_has_no_ampersands_in_it() -> None:
    assert not any("&" in title for title in command_titles().values())


def test_every_bound_handler_has_a_title() -> None:
    assert set(default_keymap()) <= set(command_titles())


# ---------------------------------------------------------------------------
# resolution


def test_with_no_overrides_the_rows_are_the_table() -> None:
    from quill.core.lite.command_areas import visible_commands

    assert resolved_commands(ALL_ON) == visible_commands(ALL_ON)


def test_an_override_reaches_the_menu_rows() -> None:
    keymap = default_keymap()
    keymap["cmd_save"] = "Ctrl+Alt+Shift+W"
    row = next(r for r in resolved_commands(ALL_ON, keymap) if r[3] == "cmd_save")
    assert row[2] == "Ctrl+Alt+Shift+W"


def test_an_override_for_a_switched_off_area_changes_nothing_visible() -> None:
    """A key that still fires for a feature somebody turned off is the feature on."""
    keymap = default_keymap()
    keymap["cmd_sort_lines"] = "Ctrl+Alt+Shift+W"
    rows = resolved_commands(lambda area: area != "tools", keymap)
    assert not any(row[3] == "cmd_sort_lines" for row in rows)


def test_binding_for_answers_the_resolved_key() -> None:
    keymap = default_keymap()
    assert binding_for(keymap, "cmd_save") == "Ctrl+S"
    assert binding_for(keymap, "cmd_nothing_at_all") == ""


# ---------------------------------------------------------------------------
# conflicts


def test_a_taken_key_names_who_has_it() -> None:
    assert conflicting_handlers(default_keymap(), "cmd_new", "Ctrl+S") == ["cmd_save"]


def test_a_conflict_is_found_however_the_key_was_spelled() -> None:
    assert conflicting_handlers(default_keymap(), "cmd_new", "shift+ctrl+s") == ["cmd_save_as"]


def test_a_command_never_conflicts_with_itself() -> None:
    assert conflicting_handlers(default_keymap(), "cmd_save", "Ctrl+S") == []


def _a_genuinely_free_chord() -> str:
    """A chord nothing is bound to, worked out rather than assumed.

    This used to name ``Ctrl+Alt+Shift+Q`` outright, and the day a real command
    claimed it (Back Up Settings, #1501) two tests failed for a reason that had
    nothing to do with what they were testing. The property under test is "a key
    nobody owns has no owner"; which key that is, is the keymap's business.

    Asked of ``conflicting_handlers`` rather than of the values, because *that*
    is what "free" means here: chords are compared with their modifiers
    normalised, so a raw string that is absent from the table can still collide
    with a binding spelled a different way round.
    """
    import string

    keymap = default_keymap()
    candidates = [f"Ctrl+Alt+Shift+{letter}" for letter in string.ascii_uppercase]
    candidates += [f"Ctrl+Shift+F{number}" for number in range(1, 13)]
    for chord in candidates:
        if not conflicting_handlers(keymap, "cmd_new", chord):
            return chord
    raise AssertionError("the keymap has no free chord left to test with")


def test_a_free_key_has_no_owner() -> None:
    assert conflicting_handlers(default_keymap(), "cmd_new", _a_genuinely_free_chord()) == []


# ---------------------------------------------------------------------------
# the audit


def test_the_shipped_keymap_is_clean() -> None:
    audit = audit_keymap(default_keymap())
    assert audit.is_clean, audit.summary()


def test_a_duplicate_is_reported_with_both_owners() -> None:
    keymap = default_keymap()
    keymap["cmd_new"] = "Ctrl+S"
    audit = audit_keymap(keymap)
    assert audit.duplicates == {"Ctrl+S": ["cmd_new", "cmd_save"]}
    assert "claimed more than once" in audit.summary()


def test_a_binding_for_a_command_that_is_gone_is_reported() -> None:
    keymap = default_keymap()
    keymap["cmd_that_left"] = _a_genuinely_free_chord()
    assert audit_keymap(keymap).unknown == ["cmd_that_left"]


def test_an_unreadable_binding_is_reported() -> None:
    keymap = default_keymap()
    keymap["cmd_save"] = "Ctrl+Nonsense"
    assert audit_keymap(keymap).unparseable == ["cmd_save"]


def test_a_reserved_binding_is_reported() -> None:
    keymap = default_keymap()
    keymap["cmd_save"] = "Ctrl+Insert"
    assert audit_keymap(keymap).reserved == ["cmd_save"]


# ---------------------------------------------------------------------------
# storage


def test_a_missing_file_reads_as_the_shipped_keys(tmp_path: Path) -> None:
    assert load_keymap(tmp_path) == default_keymap()


def test_a_corrupt_file_reads_as_the_shipped_keys(tmp_path: Path) -> None:
    """A broken keymap file must leave the editor usable, not keyless."""
    (tmp_path / KEYMAP_FILE).write_text("{not json", encoding="utf-8")
    assert load_keymap(tmp_path) == default_keymap()


def test_a_foreign_file_reads_as_the_shipped_keys(tmp_path: Path) -> None:
    (tmp_path / KEYMAP_FILE).write_text('["a list"]', encoding="utf-8")
    assert load_keymap(tmp_path) == default_keymap()


def test_only_the_changes_are_written(tmp_path: Path) -> None:
    keymap = default_keymap()
    keymap["cmd_save"] = "Ctrl+Alt+Shift+W"
    save_keymap(tmp_path, keymap)
    stored = json.loads((tmp_path / KEYMAP_FILE).read_text(encoding="utf-8"))
    assert stored["bindings"] == {"cmd_save": "Ctrl+Alt+Shift+W"}


def test_an_unchanged_keymap_writes_nothing_at_all(tmp_path: Path) -> None:
    """The whole reason deltas exist: a later build's better key still arrives."""
    save_keymap(tmp_path, default_keymap())
    stored = json.loads((tmp_path / KEYMAP_FILE).read_text(encoding="utf-8"))
    assert stored["bindings"] == {}


def test_a_respelled_key_is_not_a_change(tmp_path: Path) -> None:
    keymap = default_keymap()
    keymap["cmd_save_as"] = "shift+ctrl+s"  # the same key, typed differently
    save_keymap(tmp_path, keymap)
    stored = json.loads((tmp_path / KEYMAP_FILE).read_text(encoding="utf-8"))
    assert stored["bindings"] == {}


def test_an_override_round_trips(tmp_path: Path) -> None:
    keymap = default_keymap()
    keymap["cmd_save"] = "ctrl+alt+shift+w"
    save_keymap(tmp_path, keymap)
    # Ctrl, Shift, Alt is the order wx itself renders, so a stored key and what
    # the menu shows are the same string.
    assert load_keymap(tmp_path)["cmd_save"] == "Ctrl+Shift+Alt+W"


def test_the_rest_of_the_keys_survive_a_round_trip(tmp_path: Path) -> None:
    keymap = default_keymap()
    keymap["cmd_save"] = "Ctrl+Alt+Shift+W"
    save_keymap(tmp_path, keymap)
    loaded = load_keymap(tmp_path)
    assert loaded["cmd_new"] == default_keymap()["cmd_new"]
    assert set(loaded) == set(default_keymap())


def test_an_override_for_a_command_that_is_gone_is_dropped_on_read(tmp_path: Path) -> None:
    """It can never fire, and keeping it only lets it collide with a real key."""
    (tmp_path / KEYMAP_FILE).write_text(
        json.dumps({"schema": 1, "bindings": {"cmd_that_left": "Ctrl+Alt+Shift+Q"}}),
        encoding="utf-8",
    )
    assert "cmd_that_left" not in load_keymap(tmp_path)


def test_an_unreadable_override_is_dropped_on_read(tmp_path: Path) -> None:
    (tmp_path / KEYMAP_FILE).write_text(
        json.dumps({"schema": 1, "bindings": {"cmd_save": "Ctrl+Nonsense"}}), encoding="utf-8"
    )
    assert load_keymap(tmp_path)["cmd_save"] == default_keymap()["cmd_save"]


def test_every_alias_is_free_parseable_and_unique() -> None:
    """An alias must not shadow a key something else already answers to.

    Three ways a second chord goes wrong, and all three are silent: it repeats a
    key the defaults already use (one of the pair stops firing), two aliases
    claim the same chord (same thing), or wx cannot parse it at all (the key is
    advertised in the docs and does nothing -- the failure the menu-accelerator
    gate exists to stop, arriving through a table that gate does not read).
    """
    import wx

    from quill.core.lite.keymap import DEFAULT_ALIASES, default_keymap

    defaults = default_keymap()
    taken = {chord: handler for handler, chord in defaults.items() if chord}

    seen: dict[str, str] = {}
    for handler, chord in DEFAULT_ALIASES.items():
        assert handler in defaults, (
            f"{handler} has an alias but no primary key; an alias is a SECOND route"
        )
        assert chord not in taken, f"alias {chord} for {handler} is already {taken[chord]}'s key"
        assert chord not in seen, f"alias {chord} claimed by both {seen[chord]} and {handler}"
        seen[chord] = handler

        entry = wx.AcceleratorEntry()
        assert entry.FromString(chord), f"wx cannot parse the alias {chord}"
        assert entry.ToString() == chord, (
            f"wx round-trips {chord} as {entry.ToString()}; the two spellings must agree "
            "or the docs and the accelerator disagree"
        )


def test_the_mark_and_select_pair_keeps_its_function_keys() -> None:
    """The alias is a second route, never a replacement.

    F8 is Microsoft Word's own Extend Selection key, so it is muscle memory for
    most of the people this editor is written for. The home-row pair was added
    beside it (2026-09-15) because a function key means taking your hands off
    the home row; taking F8 away would have traded one group's habit for
    another's.
    """
    from quill.core.lite.keymap import DEFAULT_ALIASES, default_keymap

    defaults = default_keymap()
    assert defaults["cmd_start_selection"] == "F8"
    assert defaults["cmd_complete_selection"] == "Shift+F8"
    assert DEFAULT_ALIASES["cmd_start_selection"] == "Ctrl+;"
    assert DEFAULT_ALIASES["cmd_complete_selection"] == "Ctrl+'"
