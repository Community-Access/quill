"""The four chords a QUILL Lite habit fired in QUILL and got something else.

``Ctrl+Shift+V`` is Paste Without Formatting in Word 365, Notepad, every
browser and QUILL Lite. In QUILL it opened a preview pane -- so the one chord
everybody reaches for when a paste would otherwise carry a web page's styling
did the one thing you cannot undo by pressing it again.

``Ctrl+Alt+V`` is Paste from Tray in QUILL Lite and was Paste Text Only here.
``Ctrl+K`` is Word's Insert Hyperlink. ``Ctrl+Alt+K`` is Remove Every Blank
Line in QUILL Lite and was Insert Link here.

The Ctrl+K half is the more interesting fix. QUILL already answered it -- three
separate key handlers hard-coded the key code and called ``insert_link`` by
name, because the native control eats the chord before wx's accelerator table
sees it. Each was a second binding the keymap did not know about: absent from
the generated reference, unreachable from the Keyboard Manager, and deaf to a
rebinding. They now ask the registry what ``Ctrl+K`` is bound to, so the hooks
deliver a chord instead of deciding what it means (bad.md 7.2, which recorded
one site; there were three).
"""

from __future__ import annotations

import pytest

# -- the chords ------------------------------------------------------------------


def test_paste_text_only_is_on_the_chord_every_other_product_uses() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["edit.paste_plain_text"] == "Ctrl+Shift+V"
    assert lite["cmd_paste_plain"] == "Ctrl+Shift+V"


def test_paste_from_tray_is_on_quilllite_s_chord_in_both() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["edit.open_copy_tray"] == "Ctrl+Alt+V"
    assert lite["cmd_paste_from_tray"] == "Ctrl+Alt+V"


def test_preview_moved_rather_than_disappeared() -> None:
    # A displaced command that quietly becomes keyless is the failure this
    # whole exercise exists to prevent.
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["view.preview"] == "Alt+Shift+V"


def test_insert_link_is_words_key_and_remove_blank_lines_took_the_old_one() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["edit.insert_link"] == "Ctrl+K"
    assert DEFAULT_KEYMAP["power.remove_blank_lines"] == "Ctrl+Alt+K"
    assert lite["cmd_remove_blank_lines"] == "Ctrl+Alt+K"


def test_trim_trailing_spaces_has_a_key_and_the_divergence_is_deliberate() -> None:
    """The one row in bad.md 3.2 that does not converge, on purpose.

    QUILL Lite trims trailing spaces on Ctrl+Alt+T. In QUILL that is Insert
    Table -- an authorized x.md authoring chord for a verb that builds
    structure, kept over one that strips whitespace (decided 2026-09-16). So
    QUILL's trim takes Ctrl+Alt+R, and the divergence is written down rather
    than discovered.
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["edit.trim_trailing_whitespace"] == "Ctrl+Alt+R"
    assert DEFAULT_KEYMAP["format.insert_table"] == "Ctrl+Alt+T"


@pytest.mark.parametrize(
    "chord",
    ("Ctrl+K", "Ctrl+Shift+V", "Ctrl+Alt+V", "Ctrl+Alt+K", "Alt+Shift+V", "Ctrl+Alt+R"),
)
def test_no_chord_in_this_family_is_claimed_twice(chord: str) -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    owners = [cmd for cmd, bound in DEFAULT_KEYMAP.items() if bound == chord]
    assert len(owners) == 1, f"{chord} is claimed by {owners}"


# -- the hooks stopped being a second keymap -------------------------------------


def test_no_key_handler_calls_insert_link_by_name() -> None:
    """Three did. Each was a binding the keymap could not see or change."""
    from pathlib import Path

    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    assert "self.insert_link()" not in source, (
        "a key handler is calling insert_link by name again; dispatch the chord "
        "through the registry so a rebinding is followed"
    )


def test_every_ctrl_k_handler_goes_through_the_registry() -> None:
    from pathlib import Path

    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    # One helper, three call sites.
    assert source.count("_run_chord_through_registry") == 4


def test_the_registry_dispatch_finds_the_command_bound_to_a_chord() -> None:
    from quill.core.commands import CommandRegistry

    registry = CommandRegistry()
    ran: list[str] = []
    registry.register("edit.insert_link", "Insert Link", lambda: ran.append("link"), "Ctrl+K")
    registry.register("edit.other", "Other", lambda: ran.append("other"), "Ctrl+J")

    class _Host:
        commands = registry

        _run_chord_through_registry = None  # replaced below

    from quill.ui.main_frame import MainFrame

    host = _Host()
    assert MainFrame._run_chord_through_registry(host, "Ctrl+K") is True
    assert ran == ["link"]
    # Spelling and spacing of the chord must not decide the answer.
    assert MainFrame._run_chord_through_registry(host, "ctrl+k") is True
    assert MainFrame._run_chord_through_registry(host, "Ctrl+Q") is False
    assert ran == ["link", "link"]


def test_a_rebinding_is_followed_rather_than_ignored() -> None:
    """The whole point: Ctrl+K means whatever the user says it means."""
    from quill.core.commands import CommandRegistry
    from quill.ui.main_frame import MainFrame

    registry = CommandRegistry()
    ran: list[str] = []
    # Somebody has rebound Ctrl+K to something else entirely.
    registry.register("edit.insert_link", "Insert Link", lambda: ran.append("link"), "Ctrl+Alt+K")
    registry.register("power.word_count", "Word Count", lambda: ran.append("count"), "Ctrl+K")

    class _Host:
        commands = registry

    assert MainFrame._run_chord_through_registry(_Host(), "Ctrl+K") is True
    assert ran == ["count"], "the hook ran the old command instead of the bound one"


# -- P0.5: the last destructive-by-habit collision --------------------------------


def test_select_paragraph_beats_replace_all_on_ctrl_shift_h() -> None:
    """The reflex that selected a paragraph in QUILL Lite ran a replace in QUILL.

    bad.md rule 4: a habit that does damage is fixed before one that merely
    opens the wrong dialog. Replace All keeps a key rather than losing one --
    and Ctrl+H still opens the Replace dialog, which is where most people start.
    """
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _m, _label, key, handler, _flag in COMMANDS if key}
    assert DEFAULT_KEYMAP["edit.select_paragraph"] == "Ctrl+Shift+H"
    assert lite["cmd_select_paragraph"] == "Ctrl+Shift+H"
    assert DEFAULT_KEYMAP["edit.replace_all"] == "Ctrl+Shift+Grave, X"
    assert DEFAULT_KEYMAP["edit.replace"] == "Ctrl+H"
