"""GATE-9: the editor can change the size of its own text, and still can.

bad.md section 9, item 9, and it is a one-file gate on purpose: "the absence of a
whole capability is exactly the kind of thing no test notices". QUILL shipped for
two years with no ``SetFont`` on any editor control, no font setting and no zoom
command, and nothing failed -- because nothing was asserting that the capability
existed at all. Every test it had was about features it *had*.

So this asserts the three parts by inspection rather than by behaviour: a
settings field to hold the choice, a command to change it, and a ``SetFont`` that
reaches an editor. A behavioural test would need a display; the point of this one
is that it runs everywhere and fails the moment the capability is deleted.
"""

from __future__ import annotations

from pathlib import Path

UI = Path("quill/ui")


def _ui_sources() -> list[str]:
    return [path.read_text(encoding="utf-8") for path in UI.rglob("*.py")]


def test_settings_hold_a_font_name_and_a_font_size() -> None:
    from quill.core.settings import Settings

    settings = Settings()
    assert isinstance(settings.font_name, str)
    assert isinstance(settings.font_size, int)


def test_both_editors_agree_on_what_the_two_settings_are_called() -> None:
    """One name, so a settings file carried between them means one thing, and
    so the QUILL Lite profile in QUILL has two fewer rows to map (bad.md G1)."""
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    quill, lite = QuillSettings(), LiteSettings()
    assert type(quill.font_name) is type(lite.font_name)
    assert type(quill.font_size) is type(lite.font_size)


def test_some_editor_control_is_actually_given_a_font() -> None:
    """The whole gate in one line: a SetFont call somewhere in quill/ui.

    Not a count and not a location, because either would break on a refactor
    that kept the capability. What must never be true again is *zero*.
    """
    assert any("SetFont(" in source for source in _ui_sources())


def test_the_three_text_size_commands_are_registered_and_bound() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    for command_id in ("view.text_size_up", "view.text_size_down", "view.text_size_reset"):
        assert DEFAULT_KEYMAP.get(command_id), f"{command_id} has no default key"


def test_the_text_size_keys_are_notepads() -> None:
    """Ctrl+=, Ctrl+- and Ctrl+0 -- the keys the hands already know, and the
    ones QUILL Lite uses, so the family answers one way."""
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["view.text_size_up"] == "Ctrl+="
    assert DEFAULT_KEYMAP["view.text_size_down"] == "Ctrl+-"
    assert DEFAULT_KEYMAP["view.text_size_reset"] == "Ctrl+0"


def test_the_font_commands_are_on_words_keys() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["format.editor_font"] == "Ctrl+Alt+F"
    assert DEFAULT_KEYMAP["format.selection_font"] == "Ctrl+Shift+F"


def test_the_format_menu_says_font() -> None:
    """WordPad and Notepad both have Format > Font. QUILL's only font row was
    "More Font Options...", which refuses outside Markdown and writes hidden
    codes -- so the menu never said the word (bad.md M2)."""
    rows = (UI / "main_frame_editor_font.py").read_text(encoding="utf-8")
    assert '_("&Font...")' in rows
    assert '_("Font for Se&lection...")' in rows
    codes = (UI / "main_frame_format_codes.py").read_text(encoding="utf-8")
    assert "add_font_menu_items(format_menu)" in codes
    assert '"&More Font Options..."' not in codes
