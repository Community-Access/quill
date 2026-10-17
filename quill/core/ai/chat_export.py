"""Render AI conversation content: into the document, or out to a file.

Pure and wx-free so it is unit-tested without a UI: turns a single message or a
whole transcript into plain text, Markdown, or HTML, which the chat dialog drops
into the document in the format the user picks.

**Export Conversation** (2026-10-17, todo item 44) writes a whole conversation
straight to its own file -- plain text or Word -- through the same document
writers File > Save As uses (:mod:`quill.io.export`). It builds a fresh
:class:`~quill.core.document.Document` for the purpose and never sees the
document being written in the editor, so exporting cannot change it, mark it
saved, or take its name. Every message keeps its speaker and its place: in a
text file as the transcript reads ("You: ...", "AI: ..."); in a Word file as a
level-2 heading per message ("Message 3 of 12, AI") with the message beneath
it, the reply's own headings nested under that one
(:func:`quill.core.ai.chat_navigation.nest_reply_headings`) and its Markdown
tables and lists as real Word tables and lists.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import escape
from pathlib import Path

FORMATS: tuple[str, ...] = ("plain", "markdown", "html")


def normalize_format(fmt: str) -> str:
    """Return a supported format id, defaulting to ``plain``."""
    value = (fmt or "").strip().lower()
    return value if value in FORMATS else "plain"


def render_message(speaker: str, text: str, fmt: str) -> str:
    """Render one message. An empty *speaker* renders just the content."""
    fmt = normalize_format(fmt)
    name = (speaker or "").strip()
    body = text or ""
    if fmt == "html":
        safe_body = escape(body).replace("\n", "<br>\n")
        if name:
            return f"<p><strong>{escape(name)}:</strong> {safe_body}</p>"
        return f"<p>{safe_body}</p>"
    if fmt == "markdown":
        return f"**{name}:** {body}" if name else body
    # plain
    return f"{name}: {body}" if name else body


def render_transcript(messages: Iterable[tuple[str, str]], fmt: str) -> str:
    """Render a whole transcript of ``(speaker, text)`` turns."""
    fmt = normalize_format(fmt)
    rendered = [render_message(speaker, text, fmt) for speaker, text in messages]
    if not rendered:
        return ""
    separator = "\n" if fmt == "html" else "\n\n"
    return separator.join(rendered) + "\n"


#: What Export Conversation can write, by file extension.
EXPORT_SUFFIXES: dict[str, str] = {".txt": "text", ".docx": "Word"}

#: The title a conversation file starts with when nobody names it.
DEFAULT_EXPORT_TITLE = "AI conversation"


def conversation_markdown(
    messages: Sequence[tuple[str, str]], title: str = DEFAULT_EXPORT_TITLE
) -> str:
    """A whole conversation as Markdown for a Word file.

    A level-1 title, then one level-2 heading per message naming its number
    and speaker, the message beneath it with its own headings nested lower.
    """
    from quill.core.ai.chat_navigation import nest_reply_headings, number_messages

    parts = [f"# {title.strip() or DEFAULT_EXPORT_TITLE}"]
    for message in number_messages(messages):
        parts.append(f"## {message.position}")
        body = _indent_fenced_code(nest_reply_headings(message.text.strip(), 3))
        if body:
            parts.append(body)
    return "\n\n".join(parts) + "\n"


def _indent_fenced_code(markdown: str) -> str:
    """Indent the lines inside fenced code by four spaces.

    The Word writer reads Markdown a line at a time and does not know fences,
    so a ``# comment`` in a reply's Python would become a level-1 heading and
    break the file's outline. Indented, it stays a line of code; every line of
    the block moves together, so the code's own indentation is kept.
    """
    out: list[str] = []
    in_fence = False
    for line in markdown.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line)
        else:
            out.append("    " + line if in_fence and line else line)
    return "\n".join(out)


def conversation_text(
    messages: Sequence[tuple[str, str]], title: str = DEFAULT_EXPORT_TITLE
) -> str:
    """A whole conversation as plain text: the title, then the transcript."""
    body = render_transcript(messages, "plain")
    return f"{title.strip() or DEFAULT_EXPORT_TITLE}\n\n{body}"


def export_conversation(
    messages: Sequence[tuple[str, str]], path: Path, *, title: str = DEFAULT_EXPORT_TITLE
) -> Path:
    """Write *messages* to *path* as text (``.txt``) or Word (``.docx``).

    The format follows the extension, as File > Save As does. Raises
    ``ValueError`` for an empty conversation or another extension, and lets
    the writers' ``OSError`` through for a folder that will not take the file;
    the caller says either in words. The write is atomic, so a failure leaves
    any file already at *path* as it was.
    """
    from quill.core.document import Document

    if not messages:
        raise ValueError("There is nothing in this conversation to export yet.")
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix not in EXPORT_SUFFIXES:
        raise ValueError(
            f"A conversation can be exported as .txt or .docx, not {suffix or 'that'}."
        )
    if suffix == ".docx":
        from quill.io.export import write_docx_document

        document = Document(text=conversation_markdown(messages, title))
        return write_docx_document(document, target)
    from quill.io.text import write_text_document

    document = Document(text=conversation_text(messages, title))
    return write_text_document(document, target)
