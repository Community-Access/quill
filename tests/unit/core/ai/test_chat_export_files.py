"""Export Conversation (todo item 44): a whole conversation to its own text or
Word file, through the document writers File > Save As uses, never touching
the document being written. The Word file is read back with python-docx."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.chat_export import (
    conversation_markdown,
    conversation_text,
    export_conversation,
)
from quill.core.document import Document

REPLY = (
    "# Comparison\n\n"
    "| Pet | Sound |\n| --- | --- |\n| Cat | Meow |\n| Dog | Woof |\n\n"
    "## Verdict\n\nBoth are fine.\n\n"
    "```python\n# a comment, not a heading\nprint('hi')\n```"
)
CONVERSATION = [
    ("You", "Compare cats and dogs."),
    ("AI", REPLY),
    ("You", "Thanks — and ünïcode?"),
    ("AI", "Yes: ünïcode is kept."),
]


def test_text_keeps_every_speaker_in_order(tmp_path: Path) -> None:
    target = export_conversation(CONVERSATION, tmp_path / "chat.txt")
    text = target.read_text(encoding="utf-8")
    assert text.startswith("AI conversation")
    positions = [text.index(f"{speaker}: {body}") for speaker, body in CONVERSATION]
    assert positions == sorted(positions)
    assert "Thanks — and ünïcode?" in text


def test_markdown_for_word_has_a_heading_per_message() -> None:
    markdown = conversation_markdown(CONVERSATION, "Pets")
    assert markdown.startswith("# Pets\n")
    for heading in (
        "## Message 1 of 4, You",
        "## Message 2 of 4, AI",
        "### Comparison",
        "#### Verdict",
        "## Message 4 of 4, AI",
    ):
        assert heading in markdown.splitlines()


def test_a_real_word_file_round_trips(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    target = export_conversation(CONVERSATION, tmp_path / "chat.docx", title="Pets")
    document = docx.Document(str(target))
    headings = [
        (p.style.name, p.text) for p in document.paragraphs if p.style.name.startswith("Heading")
    ]
    assert headings == [
        ("Heading 1", "Pets"),
        ("Heading 2", "Message 1 of 4, You"),
        ("Heading 2", "Message 2 of 4, AI"),
        ("Heading 3", "Comparison"),
        ("Heading 4", "Verdict"),
        ("Heading 2", "Message 3 of 4, You"),
        ("Heading 2", "Message 4 of 4, AI"),
    ]
    body = "\n".join(p.text for p in document.paragraphs)
    assert "Compare cats and dogs." in body
    assert "Thanks — and ünïcode?" in body
    assert "# a comment, not a heading" in body
    # The Markdown table became a real Word table with its header row.
    assert len(document.tables) == 1
    rows = [[cell.text for cell in row.cells] for row in document.tables[0].rows]
    assert rows == [["Pet", "Sound"], ["Cat", "Meow"], ["Dog", "Woof"]]


def test_an_existing_file_is_replaced(tmp_path: Path) -> None:
    target = tmp_path / "chat.txt"
    target.write_text("old", encoding="utf-8")
    export_conversation(CONVERSATION[:1], target)
    assert "Compare cats and dogs." in target.read_text(encoding="utf-8")
    assert "old" not in target.read_text(encoding="utf-8")


def test_a_failed_write_leaves_the_old_file(tmp_path: Path, monkeypatch) -> None:
    import quill.io.text as text_io

    target = tmp_path / "chat.txt"
    target.write_text("keep me", encoding="utf-8")

    def refuse(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(text_io, "write_text_atomic", refuse)
    with pytest.raises(OSError):
        export_conversation(CONVERSATION, target)
    assert target.read_text(encoding="utf-8") == "keep me"


def test_nothing_to_export_and_unknown_formats_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nothing"):
        export_conversation([], tmp_path / "a.txt")
    with pytest.raises(ValueError, match=".pdf"):
        export_conversation(CONVERSATION, tmp_path / "a.pdf")
    assert not (tmp_path / "a.pdf").exists()


def test_the_active_document_is_never_involved(tmp_path: Path) -> None:
    active = Document(text="My novel, chapter one.", path=tmp_path / "novel.md")
    export_conversation(CONVERSATION, tmp_path / "chat.docx")
    export_conversation(CONVERSATION, tmp_path / "chat.txt")
    assert active.text == "My novel, chapter one."
    assert active.path == tmp_path / "novel.md"
    assert not (tmp_path / "novel.md").exists()


def test_plain_text_title_defaults_when_blank() -> None:
    assert conversation_text([("You", "x")], "  ").startswith("AI conversation\n\nYou: x")
