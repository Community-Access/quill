"""The Command Palette and Keyboard Shortcuts show Quill Radio's own keys.

Both read a command's key through ``_binding_for``. Radio's transport commands
default to QUILL-key *chords* in the shared keymap (Ctrl+Shift+Grave, then a
letter) -- right in the editor, meaningless in an app with no QUILL key -- so
until 2026-09-25 the palette listed Play/Pause and Mute on chords that do
nothing here, while Radio's real keys (Ctrl+P, Ctrl+., Ctrl+M, Ctrl+Up/Down)
went unshown. And the Keyboard Shortcuts editor listed fourteen "QUILL Quick
Nav" rows on bare letters, for a document Radio does not have.

Built on a real ``RadioAppFrame``, because the registry the palette walks only
exists there.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def radio_frame(quill_data_dir):
    app = wx.App()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    try:
        yield frame
    finally:
        # Building the app installs a process-global dialog-transition policy.
        set_transition_announcement_policy(None)
        frame.frame.Destroy()
        del app


def _shown(frame, command) -> str:
    """What the palette shows (``CommandPaletteDialog._binding``)."""
    return frame._binding_for(command.id) or command.keybinding or ""


def _is_leader_chord(binding: str) -> bool:
    # "Ctrl+Shift+," is the comma key, not a chord; a chord is "prefix, key".
    return ", " in binding or "Grave" in binding


def test_no_palette_command_shows_a_quill_key_chord(radio_frame) -> None:
    chords = [
        f"{command.id} ({_shown(radio_frame, command)})"
        for command in radio_frame.commands.list()
        if _is_leader_chord(_shown(radio_frame, command))
    ]
    assert chords == [], "Radio palette rows on QUILL-key chords: " + "; ".join(chords)


@pytest.mark.parametrize(
    ("command_id", "key"),
    [
        ("radio.play_pause", "Ctrl+P"),
        ("radio.stop", "Ctrl+."),
        ("radio.mute_toggle", "Ctrl+M"),
        ("radio.volume_up", "Ctrl+Up"),
        ("radio.volume_down", "Ctrl+Down"),
    ],
)
def test_the_transport_rows_show_radios_own_keys(radio_frame, command_id, key) -> None:
    command = radio_frame.commands.get(command_id)
    assert command is not None
    assert _shown(radio_frame, command) == key


def test_keyboard_shortcuts_lists_no_editor_quick_nav_rows(radio_frame) -> None:
    listed = [command_id for _title, command_id in radio_frame._keymap_listed_entries()]
    assert listed, "the editor would open empty"
    assert not [cid for cid in listed if cid.startswith("quill.quick_nav.")]
    assert "radio.play_pause" in listed
