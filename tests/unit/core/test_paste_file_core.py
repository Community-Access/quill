"""Paste File's decisions and sentences (quill/core/paste_file.py), wx-free."""

from __future__ import annotations

from pathlib import Path

from quill.core import paste_file
from quill.core.paste_file import describe_paste, plan_paste, refusal


def test_paths_are_one_per_line(tmp_path) -> None:
    a, b = tmp_path / "a.txt", tmp_path / "b.docx"

    plan = plan_paste([a, b], "path")

    assert plan.text == f"{a}\n{b}"
    assert describe_paste(plan, "path") == "Pasted 2 paths"


def test_text_files_are_read_and_separated_by_a_blank_line(tmp_path) -> None:
    a = tmp_path / "a.txt"
    a.write_text("First file\n", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("# Second", encoding="utf-8")

    plan = plan_paste([a, b], "text")

    assert plan.text == "First file\n\n# Second"
    assert describe_paste(plan, "text") == "Pasted the text of 2 files"


def test_a_file_over_the_limit_is_refused_by_name(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(paste_file, "MAX_FILE_BYTES", 10)
    big = tmp_path / "big.txt"
    big.write_text("x" * 50, encoding="utf-8")
    small = tmp_path / "small.txt"
    small.write_text("ok", encoding="utf-8")

    plan = plan_paste([big, small], "text")

    assert plan.text == "ok"
    assert plan.refused and plan.refused[0].startswith("big.txt is ")
    assert "limit" in describe_paste(plan, "text")


def test_a_binary_file_is_refused_not_pasted_as_nonsense(tmp_path) -> None:
    picture = tmp_path / "photo.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

    assert refusal(picture) == "photo.png is not a text file"
    plan = plan_paste([picture], "text")
    assert describe_paste(plan, "text") == (
        "Nothing was pasted. Not pasted: photo.png is not a text file"
    )


def test_utf16_text_is_text(tmp_path) -> None:
    note = tmp_path / "note.log"
    note.write_bytes("hello".encode("utf-16"))

    assert refusal(note) == ""


def test_a_folder_and_a_reader_failure_are_named(tmp_path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    doc = tmp_path / "broken.docx"
    doc.write_bytes(b"not really a docx")

    def failing(_path: Path) -> str:
        raise ValueError("bad zip")

    plan = plan_paste([folder, doc], "text", reader=failing)

    assert plan.refused == ["folder is a folder", "broken.docx could not be read: bad zip"]


def test_a_word_document_goes_through_the_readers(tmp_path) -> None:
    """Formats QUILL opens are read the way it opens them, not as raw bytes."""
    seen: list[Path] = []
    doc = tmp_path / "letter.docx"
    doc.write_bytes(b"PK\x03\x04\x00\x00")  # a zip header: binary, but a format QUILL reads

    plan = plan_paste([doc], "text", reader=lambda p: seen.append(p) or "Dear Sam")

    assert seen == [doc]
    assert plan.text == "Dear Sam"
