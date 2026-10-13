"""Record Key: a pressed combination written out the way the family writes keys."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.key_record import chord_from_key_event

_WX = SimpleNamespace(
    WXK_CONTROL=308, WXK_ALT=307, WXK_SHIFT=306, WXK_PAGEDOWN=367, WXK_F9=348, WXK_ESCAPE=27
)


def _event(code: int, *, vk: int = 0, ctrl=False, alt=False, shift=False):
    return SimpleNamespace(
        GetKeyCode=lambda: code,
        GetRawKeyCode=lambda: vk,
        ControlDown=lambda: ctrl,
        AltDown=lambda: alt,
        ShiftDown=lambda: shift,
    )


def test_alt_shift_backslash_is_written_as_the_guides_write_it() -> None:
    """The backslash key by its virtual-key code, whatever the character."""
    event = _event(ord("\\"), vk=0xDC, alt=True, shift=True)
    assert chord_from_key_event(_WX, event) == "Alt+Shift+\\"


def test_modifiers_come_in_family_order() -> None:
    event = _event(ord("K"), vk=0x4B, ctrl=True, alt=True, shift=True)
    assert chord_from_key_event(_WX, event) == "Ctrl+Alt+Shift+K"
    assert chord_from_key_event(_WX, _event(367, ctrl=True, alt=True)) == "Ctrl+Alt+PageDown"
    assert chord_from_key_event(_WX, _event(348, ctrl=True)) == "Ctrl+F9"


def test_a_lone_modifier_is_still_waiting_for_the_key() -> None:
    for code in (308, 307, 306):
        assert chord_from_key_event(_WX, _event(code, ctrl=True)) is None


def test_a_recorded_key_passes_the_pickers_own_rules() -> None:
    """What Record Key writes is something the picker accepts as typed."""
    from quill.core.family_chords import show_hide_key_problem
    from quill.core.lite.keymap import normalise_chord

    chord = chord_from_key_event(_WX, _event(367, ctrl=True, alt=True))
    assert chord is not None and normalise_chord(chord)
    assert show_hide_key_problem(chord, app_id="weather", taken={}, own={}) == ""
    # And Alt+Shift+\ is now QUILL Transcribe's, so another app is told whose.
    taken = chord_from_key_event(_WX, _event(ord("\\"), vk=0xDC, alt=True, shift=True))
    said = show_hide_key_problem(str(taken), app_id="weather", taken={}, own={})
    assert "QUILL Transcribe" in said
