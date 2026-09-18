"""One window for how this file gets written (bad.md P1.8, F6, 3.7).

QUILL could *read* a document's encoding and line ending in two status-bar
cells and change them only there -- no BOM option, no File menu row, and,
worst, without marking the document modified. Somebody who fixed a file's
encoding and pressed nothing else closed it to "no changes to save" and lost
the fix without being told.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "file_format_dialog.py").read_text(
    encoding="utf-8"
)
FRAME = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_it_offers_the_same_four_encodings_as_quilllite() -> None:
    from quill.core.lite.textfile import ENCODING_CHOICES

    assert [name for _codec, name in ENCODING_CHOICES] == [
        "UTF-8",
        "UTF-8 with BOM",
        "UTF-16",
        "Windows-1252 (ANSI)",
    ]
    assert "from quill.core.lite.textfile import (" in SOURCE
    assert "encoding_rows," in SOURCE and "newline_rows," in SOURCE


def test_bom_is_reachable_at_last() -> None:
    """The row's own words: "offering UTF-8 with BOM". The old chooser had four
    codecs and none of them was one with a BOM, so a file that arrived with one
    could not be saved back with it."""
    from quill.core.lite.textfile import ENCODING_CHOICES

    assert any(codec == "utf-8-sig" for codec, _name in ENCODING_CHOICES)


def test_the_names_are_speakable_both_ways() -> None:
    from quill.ui.file_format_dialog import describe_encoding, describe_line_ending

    assert describe_encoding("utf-8-sig") == "UTF-8 with BOM"
    assert describe_encoding("something-else") == "something-else"
    assert describe_line_ending(chr(13) + chr(10)) == "CRLF (Windows)"
    # A line ending the chooser does not offer is NAMED now rather than called
    # Unknown -- it becomes a "keep as is" row so OK cannot silently convert
    # the document (bad.md F8). Only a genuinely unrecognised value is Mixed.
    assert describe_line_ending(chr(13)) == "CR (classic Mac)"
    assert describe_line_ending("") == "Unknown"


def test_changing_the_format_dirties_the_document() -> None:
    assert "self.document.modified = True" in _method(FRAME, "open_file_format_dialog")


def test_the_status_bar_cells_dirty_it_too() -> None:
    """Both of them, because either one is a change to how the file is written."""
    assert "self.document.modified = True" in _method(FRAME, "choose_document_encoding")
    assert "self.document.modified = True" in _method(FRAME, "toggle_line_endings")


def test_cancelling_says_so_and_changes_nothing() -> None:
    body = _method(FRAME, "open_file_format_dialog")
    assert 'self._set_status("File format unchanged")' in body


def test_it_goes_through_the_hardened_modal_path() -> None:
    """The dialog shows itself, which is what the hardening contract asks.

    A surface whose caller decides how to show it is a surface that gets shown
    the wrong way exactly once, in the one place nobody re-reads.
    """
    assert "dialog.show()" in _method(FRAME, "open_file_format_dialog")
    assert "from quill.ui.dialog_contract import show_modal_dialog" in SOURCE
    assert 'show_modal_dialog(self.dialog, "File Format")' in SOURCE
    assert "apply_modal_ids(" in SOURCE


def _method(source: str, name: str) -> str:
    start = source.index("    def " + name + "(")
    end = source.index("\n    def ", start + 1)
    return source[start:end]
