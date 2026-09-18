"""The close prompt names the document, in both editors (bad.md F12, P2.10).

QuillLite asked "Save changes to notes.txt?" and QUILL asked "You have unsaved
changes. Save before closing?" -- the right question about the wrong number of
documents. With nine tabs open and no way to glance at a title bar, *which one*
is the whole answer a listener needs.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.close_prompt import (
    CANCEL_LABEL,
    DISCARD_LABEL,
    SAVE_LABEL,
    can_relabel_buttons,
    unsaved_changes_question,
    unsaved_changes_title,
)


def test_it_names_the_document() -> None:
    assert unsaved_changes_question("notes.txt") == "Save changes to notes.txt?"


def test_it_names_what_is_about_to_happen_when_the_caller_knows() -> None:
    """QUILL asks this from four places and "before what?" differs in each."""
    assert unsaved_changes_question("notes.txt", "closing") == (
        "Save changes to notes.txt before closing?"
    )


def test_a_document_with_no_name_still_gets_a_sentence() -> None:
    """The unnamed one is the document somebody is most surprised to lose."""
    assert unsaved_changes_question("") == "Save changes to this document?"
    assert unsaved_changes_question("   ") == "Save changes to this document?"


def test_a_name_with_odd_whitespace_reads_cleanly() -> None:
    assert unsaved_changes_question("my  notes\n.txt") == "Save changes to my notes .txt?"


def test_the_title_does_not_repeat_the_question() -> None:
    """A title is announced on arrival and the question read after it."""
    assert unsaved_changes_title() == "Unsaved changes"
    assert "Save changes" not in unsaved_changes_title()


def test_the_buttons_say_what_word_says() -> None:
    assert (SAVE_LABEL, DISCARD_LABEL, CANCEL_LABEL) == ("Save", "Don't Save", "Cancel")


def test_macos_keeps_its_native_labels_and_therefore_its_accelerators() -> None:
    """#23: relabelling on Cocoa disabled Y/N/Escape, which is the worse loss."""
    assert can_relabel_buttons("win32") is True
    assert can_relabel_buttons("linux") is True
    assert can_relabel_buttons("darwin") is False


def test_both_editors_ask_the_same_question() -> None:
    root = Path(__file__).resolve().parents[3]
    quill_side = (root / "quill" / "ui" / "main_frame.py").read_text(encoding="utf-8")
    lite_side = (root / "quill" / "apps" / "lite_window.py").read_text(encoding="utf-8")
    for source in (quill_side, lite_side):
        assert "unsaved_changes_question(" in source
    # And the sentence is not spelled out a second time anywhere.
    assert "You have unsaved changes. Save before" not in quill_side
    assert 'f"Save changes to {self.document_name()}?"' not in lite_side
