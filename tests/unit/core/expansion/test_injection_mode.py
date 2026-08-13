"""Unit tests for choosing how an expansion is delivered, per application."""

from __future__ import annotations

from quill.core.expansion.targets import injection_mode_for


def test_typing_is_the_default() -> None:
    assert injection_mode_for("notepad.exe") == "type"


def test_an_application_on_the_paste_list_gets_the_clipboard_route() -> None:
    assert injection_mode_for("stubborn.exe", paste_processes={"stubborn.exe"}) == "paste"


def test_the_paste_list_ignores_case() -> None:
    assert injection_mode_for("Stubborn.EXE", paste_processes={"stubborn.exe"}) == "paste"


def test_one_listed_application_does_not_affect_the_others() -> None:
    listed = {"stubborn.exe"}
    assert injection_mode_for("notepad.exe", paste_processes=listed) == "type"


def test_the_global_preference_applies_when_nothing_is_listed() -> None:
    assert injection_mode_for("notepad.exe", default_mode="paste") == "paste"


def test_a_listed_application_still_pastes_when_the_default_is_typing() -> None:
    assert (
        injection_mode_for("stubborn.exe", default_mode="type", paste_processes={"stubborn.exe"})
        == "paste"
    )


def test_an_unknown_default_falls_back_to_typing() -> None:
    # Typing is the safe default: it never touches the clipboard.
    assert injection_mode_for("notepad.exe", default_mode="carrier pigeon") == "type"


def test_an_unknown_process_uses_the_default() -> None:
    assert injection_mode_for("", paste_processes={"stubborn.exe"}) == "type"
