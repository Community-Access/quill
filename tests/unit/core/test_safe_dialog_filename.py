"""Filenames handed to a native save panel are sanitized first (#1345).

A macOS ``SystemError: ActivateEvent returned a result with an exception set``
was reported while creating a notebook from a folder whose name began with an
emoji: the folder name became the save panel's ``defaultFile`` unmodified, and
the underlying ``wxAssertionError`` came out of native code during that panel's
activation. Containment (the try/except around ``_on_frame_activate``) stops the
crash; this stops the input that provoked it from reaching the panel at all.
"""

from __future__ import annotations

from quill.core.paths import safe_dialog_filename


def test_emoji_are_stripped_but_the_rest_of_the_name_survives() -> None:
    assert safe_dialog_filename("🎉 Party Notes") == "Party Notes"
    assert safe_dialog_filename("Trip 2026 ✈️") == "Trip 2026"


def test_reserved_and_control_characters_go() -> None:
    assert safe_dialog_filename('a/b\\c:d*e?f"g<h>i|j') == "abcdefghij"
    assert safe_dialog_filename("line\nbreak\ttab") == "linebreaktab"


def test_suffix_is_appended_after_cleaning() -> None:
    assert safe_dialog_filename("🎉Ideas", suffix=".quillnotebook") == "Ideas.quillnotebook"


def test_a_name_that_cleans_to_nothing_falls_back() -> None:
    assert safe_dialog_filename("🎉🎉🎉", fallback="Notebook") == "Notebook"
    assert safe_dialog_filename("   ") == "Untitled"
    assert safe_dialog_filename("...", suffix=".x") == "Untitled.x"


def test_ordinary_names_are_left_exactly_alone() -> None:
    for name in ("Meeting notes", "budget-2026", "Café accounts", "naïve draft"):
        assert safe_dialog_filename(name) == name
