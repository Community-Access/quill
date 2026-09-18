"""A character the encoding cannot hold says so, by name (bad.md P0.9, F3).

A cp1252 document that gains a character the code page cannot hold failed to
save with "Command failed:
file.save" and nothing else: `UnicodeEncodeError` is not an `OSError`, so it
escaped the save path's error handling entirely. The writer was left to work
out which character did it, in a document they cannot see.
"""

from __future__ import annotations

import errno

from quill.ui.main_frame_write_safety import WriteSafetyMixin


class _WX:
    ICON_ERROR = 1
    OK = 2


class _Host(WriteSafetyMixin):
    def __init__(self) -> None:
        self._wx = _WX()
        self.boxes: list[str] = []
        self.status: list[str] = []

    def _show_message_box(self, message: str, title: str, style: int) -> None:
        self.boxes.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)


#: A character Windows-1252 has no byte for, which is the everyday case: a
#: name pasted from elsewhere, or a symbol from the emoji picker.
UNENCODABLE = chr(0x4E2D)


def _encode_failure() -> UnicodeEncodeError:
    try:
        ("a name with " + UNENCODABLE + " in it").encode("cp1252")
    except UnicodeEncodeError as error:
        return error
    raise AssertionError("cp1252 encoded " + UNENCODABLE)


def test_it_names_the_character_rather_than_a_byte_offset() -> None:
    host = _Host()
    host._report_save_failure("notes.txt", _encode_failure(), "Save")
    assert UNENCODABLE in host.boxes[0]


def test_it_names_the_encoding_the_document_was_opened_as() -> None:
    """Not `error.encoding`, which says "charmap" for every Windows code page."""
    host = _Host()
    host.document = type("Doc", (), {"encoding": "cp1252"})()
    host._report_save_failure("notes.txt", _encode_failure(), "Save")
    assert "as cp1252" in host.boxes[0]


def test_with_no_document_to_ask_it_still_makes_sense() -> None:
    host = _Host()
    host._report_save_failure("notes.txt", _encode_failure(), "Save")
    assert "in its current encoding" in host.boxes[0]


def test_it_says_what_to_do_about_it() -> None:
    host = _Host()
    host._report_save_failure("notes.txt", _encode_failure(), "Save")
    assert "Save As" in host.boxes[0]
    assert "still open and unsaved" in host.boxes[0]


def test_the_disk_full_sentence_still_works() -> None:
    host = _Host()
    host._report_save_failure("notes.md", OSError(errno.ENOSPC, "No space"), "Save")
    assert "The disk is full" in host.boxes[0]


def test_an_unclassified_error_still_keeps_its_text() -> None:
    host = _Host()
    host._report_save_failure("notes.md", OSError(errno.EIO, "I/O error"), "Save")
    assert "Could not save notes.md" in host.boxes[0]
    assert "I/O error" in host.boxes[0]


def test_the_save_path_actually_catches_it() -> None:
    import inspect

    from quill.ui.main_frame import MainFrame

    assert "(OSError, UnicodeEncodeError)" in inspect.getsource(MainFrame.save_file)
