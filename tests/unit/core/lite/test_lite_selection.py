"""QuillLite's Select menu: the table, the area, and parity with QUILL.

The behaviour of the commands themselves needs a real window and belongs to the
sign-off checklist, which is where a person listens to what they announce. What
is checked here is what a machine can check and a person cannot reliably: that
the menu is complete, that its keys are the ones QUILL uses where that was
possible, that switching the area off does not take Select All with it, and --
the rule that keeps costing work when it is forgotten -- that QuillLite has not
ended up with a selection command QUILL lacks.
"""

from __future__ import annotations

import pytest

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.command_areas import visible_commands
from quill.core.lite.commands import COMMANDS, plain_label
from quill.core.lite.features import AREAS

SELECT_MENU = "&Edit|Selectio&n"


def _rows(menu: str) -> list[tuple[str, str, str, str, str]]:
    return [row for row in COMMANDS if row[0] == menu and row[4] != "sep"]


def test_the_select_menu_exists_and_is_not_thin() -> None:
    rows = _rows(SELECT_MENU)
    assert len(rows) >= 19, [plain_label(r[1]) for r in rows]


def test_selection_is_a_submenu_of_edit_not_a_menu_bar_entry() -> None:
    """Nineteen items belong under Edit, where Word and QUILL both keep them.

    Poured into Edit itself they would swamp it; given a bar entry of their own
    they would push a tenth top-level menu onto a small editor's menu bar. A
    submenu is one Alt+E, N away and carries its own mnemonic namespace.
    """
    from quill.core.lite.commands import menu_titles, split_menu

    parent, child = split_menu(SELECT_MENU)
    assert (parent, child) == ("&Edit", "Selectio&n")
    assert SELECT_MENU not in menu_titles()
    assert parent in menu_titles()


def test_the_submenu_is_named_by_a_row_of_the_edit_menu() -> None:
    """The title is a row, so the menu builder and the access-key check see it.

    A submenu whose title is inferred rather than written down lands wherever
    the builder happens to put it and claims a letter no check compares against
    its neighbours. Written down, it is a row like any other -- which is what
    ``test_no_access_key_is_claimed_twice_within_one_menu`` needs in order to
    catch a title that collides with an item beside it.
    """
    _parent, child = SELECT_MENU.split("|", 1)
    titles = [
        (menu, label) for menu, label, _k, _h, kind in COMMANDS if kind == "sub" and menu == "&Edit"
    ]
    assert ("&Edit", child) in titles, titles


@pytest.mark.parametrize(
    ("handler", "key"),
    [
        ("cmd_start_selection", "F8"),
        ("cmd_complete_selection", "Shift+F8"),
        ("cmd_reselect", "Ctrl+Shift+F8"),
        ("cmd_go_to_selection_start", "Alt+Shift+F8"),
    ],
)
def test_the_f8_family_uses_quills_own_keys(handler: str, key: str) -> None:
    """Muscle memory has to carry between the two products.

    Every one of these was free in QuillLite, so there was no reason to differ
    and every reason not to.
    """
    bound = {h: k for _m, _l, k, h, kind in COMMANDS if kind != "sep"}
    assert bound[handler] == key
    assert key in set(DEFAULT_KEYMAP.values()), f"{key} is not a QUILL key any more"


def test_select_all_survives_the_area_being_switched_off() -> None:
    """The one selection command that predates the menu must never vanish."""
    without = visible_commands(lambda area: area != "selection")
    assert not [r for r in without if r[0] == SELECT_MENU]
    assert any(r[3] == "cmd_select_all" for r in without)
    assert any(r[2] == "Ctrl+A" for r in without)


def test_the_area_exists_and_starts_on() -> None:
    from quill.core.lite.features import DEFAULT_OFF

    labels = {area.id: area.label for area in AREAS}
    assert labels["selection"] == "The Selection submenu"
    assert "selection" not in DEFAULT_OFF


def test_every_select_command_has_a_handler_on_the_window() -> None:
    """A menu row wired to a method that does not exist fails only when pressed."""
    from quill.apps.lite_window import DocumentFrame

    missing = [
        plain_label(label)
        for _menu, label, _key, handler, kind in COMMANDS
        if kind != "sep" and _menu == SELECT_MENU and not hasattr(DocumentFrame, handler)
    ]
    assert missing == [], missing


def test_quill_can_do_everything_the_select_menu_can() -> None:
    """QuillLite is never allowed to be ahead of QUILL.

    Every command in this menu maps to a QUILL command id that is bound. This is
    the test that would have caught Select Word being absent from QUILL, and
    Select Line being registered there with no key at all.
    """
    equivalent = {
        "cmd_start_selection": "edit.start_selection",
        "cmd_complete_selection": "edit.complete_selection",
        "cmd_reselect": "edit.reselect",
        "cmd_go_to_selection_start": "edit.go_to_start_of_selection",
        # Two rows, not one, since 2026-09-17: Ctrl+Alt+F8 is the F8 *marker*
        # toggle and Ctrl+Alt+Shift+F8 is Extend Selection Mode, a sticky
        # Shift. They were sharing a chord across the two products with two
        # different meanings, which is the shape of a key somebody presses
        # expecting one thing and gets the other (bad.md 5.3a, P1.2).
        "cmd_toggle_extend_mode": "edit.toggle_selection_marker",
        "cmd_toggle_extend_selection_mode": "edit.toggle_extend_selection_mode",
        "cmd_select_word": "edit.select_word",
        "cmd_select_line": "edit.select_line",
        "cmd_select_paragraph": "edit.select_paragraph",
        # Ctrl+Space means sentence in both since 2026-09-17. It mapped to
        # edit.select_chunk because QUILL had no Select Sentence at all -- the
        # gate could only say "something here answers that key", not "the same
        # thing does" (bad.md P1.2b, 5.3a).
        "cmd_select_sentence": "edit.select_sentence",
        "cmd_select_block": "edit.select_block",
        "cmd_expand_selection": "edit.expand_selection",
        "cmd_shrink_selection": "edit.shrink_selection",
        "cmd_unselect_all": "edit.unselect_all",
        "cmd_set_mark": "edit.set_mark",
        "cmd_pop_mark": "edit.pop_mark",
        "cmd_list_marks": "edit.list_marks",
        "cmd_exchange_point_mark": "edit.exchange_point_mark",
        "cmd_say_selection": "edit.say_selected",
        "cmd_duplicate_selection": "edit.duplicate_selection",
        # Added 2026-09-16, and it is the reason QUILL's own
        # edit.open_review_buffer finally got a key: the command had been
        # registered there since SEL-4 with nothing bound to it, so the moment
        # QuillLite could reach the feature from the keyboard the small product
        # was ahead (bad.md 4.2, Tier 2). This gate is what said so.
        "cmd_open_review_buffer": "edit.open_review_buffer",
    }
    handlers = {h for _m, _l, _k, h, kind in COMMANDS if kind != "sep" and _m == SELECT_MENU}
    assert handlers <= set(equivalent), sorted(handlers - set(equivalent))

    # say_selected is reachable in QUILL through a conditional Shift+Space
    # intercept rather than the keymap, so it is the one exception to "bound".
    reachable_without_a_keymap_entry = {"edit.say_selected"}
    unreachable = sorted(
        command_id
        for handler, command_id in equivalent.items()
        if handler in handlers
        and command_id not in reachable_without_a_keymap_entry
        and not DEFAULT_KEYMAP.get(command_id)
    )
    assert unreachable == [], (
        "QuillLite offers these and QUILL has no key for them, which is exactly "
        "backwards: " + ", ".join(unreachable)
    )


def test_the_three_clashing_keys_stayed_with_their_resident() -> None:
    """Where a key was already taken here, the newcomer moved -- not the resident.

    An existing binding somebody's fingers already know outranks a new command's
    convention, which is the same call made for Ctrl+J and Ctrl+Shift+V.

    **Except Set Mark**, on 2026-09-16, and the exception has a rule behind it
    rather than a preference: frequency breaks the tie (bad.md rule 3). Set Mark
    is an editing-loop verb and was on a four-key chord, while Switch Document
    Mode -- pressed a handful of times a year -- held the three-key one that is
    Set Mark's in QUILL. The resident moved, to Alt+Shift+F, which is free in
    both editors.
    """
    bound = {h: k for _m, _l, k, h, kind in COMMANDS if kind != "sep"}
    assert bound["cmd_expand_selection"] == "Ctrl+Shift+X"
    assert bound["cmd_set_bookmark"] == "Ctrl+Shift+B"
    assert bound["cmd_switch_document_kind"] == "Alt+Shift+F"
    # ...and the imports took free keys instead of evicting them.
    assert bound["cmd_exchange_point_mark"] == "Ctrl+Alt+X"
    assert bound["cmd_select_block"] == "Ctrl+Alt+Shift+B"
    assert bound["cmd_set_mark"] == "Ctrl+Shift+M"
