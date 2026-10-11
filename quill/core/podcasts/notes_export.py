"""The four ways to copy show notes, and the page View in Browser opens (qc.md 5c).

Jeff: "copy show notes to the clipboard in full form either as plain text without
links or fully formatted, configurable." So Copy Notes copies the *whole* notes in
the format chosen in Preferences, and its menu offers all four:

* **Plain text** -- paragraphs and list items as lines, headings as lines, links
  reduced to their text, timestamps kept. The shipped default: what pastes cleanly
  into an email or a chat.
* **Plain text with links** -- the same, with each link's address in brackets after
  its text, so nothing is lost and nothing is hidden.
* **Markdown** -- headings, lists, links and emphasis. QUILL is a writing app, and
  this is the format a QUILL document, or a listener's notes file, wants.
* **Formatted** -- HTML (for ``CF_HTML``) with an RTF copy beside it, so Word,
  Outlook and QUILL's rich editor paste the formatting and Notepad pastes text.
  Images are referenced by address, never embedded.

Every format is built from one reading of the notes
(:class:`~quill.core.podcasts.notes_document.NotesDocument`), never by a second
parse, and each has a test: "copy as Markdown" that drops a heading is worse than
no Markdown at all. The same four apply to a podcast's description and to a
transcript, so there is one Copy vocabulary in the app.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html import escape

from quill.core.podcasts import _notes_export_legacy as legacy
from quill.core.podcasts._notes_export_legacy import NotesDocument as LegacyNotesDocument
from quill.core.podcasts.notes_document import (
    BLOCK_HEADING,
    BLOCK_ITEM,
    Block,
    NotesDocument,
    Run,
)

__all__ = [
    "DEFAULT_FORMAT",
    "FORMATS",
    "FORMATTED",
    "FORMAT_LABELS",
    "MARKDOWN",
    "PLAIN",
    "PLAIN_LINKS",
    "browser_page",
    "copied_sentence",
    "export",
    "normalize_format",
    "render",
    "spoken_copy",
    "to_html",
    "to_markdown",
    "to_plain",
    "to_rtf",
    "word_count",
]

PLAIN = "plain"
PLAIN_LINKS = "plain_links"
MARKDOWN = "markdown"
FORMATTED = "formatted"

#: The formats in the order every menu and the Preferences row offers them.
FORMATS: tuple[str, ...] = (PLAIN, PLAIN_LINKS, MARKDOWN, FORMATTED)
DEFAULT_FORMAT = PLAIN

#: What each format is called, in a menu and in the sentence a copy speaks.
FORMAT_LABELS: dict[str, str] = {
    PLAIN: "Plain text",
    PLAIN_LINKS: "Plain text with links",
    MARKDOWN: "Markdown",
    FORMATTED: "Formatted",
}


#: The same names inside a sentence ("Copied the show notes as Markdown").
_SPOKEN: dict[str, str] = {
    PLAIN: "plain text",
    PLAIN_LINKS: "plain text with links",
    MARKDOWN: "Markdown",
    FORMATTED: "formatted text",
}


def normalize_format(value: object) -> str:
    """A stored format, or the default for anything unrecognised."""
    text = str(value or "").strip().lower()
    return text if text in FORMATS else DEFAULT_FORMAT


def word_count(text: str) -> int:
    return len(re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text or ""))


def copied_sentence(fmt: str, words: int, *, what: str = "the show notes") -> str:
    """ "Copied the show notes as plain text, 412 words." -- spoken after every copy."""
    noun = "word" if words == 1 else "words"
    return f"Copied {what} as {_SPOKEN[normalize_format(fmt)]}, {words:,} {noun}."


def _groups(runs: tuple[Run, ...]) -> list[tuple[str, list[Run]]]:
    """Consecutive runs that share one link, as one group.

    A link whose own text is partly bold or italic arrives as several runs with
    the same address; every format writes it as *one* link, or "Support **the**
    show" would be three links to one place.
    """
    groups: list[tuple[str, list[Run]]] = []
    for run in runs:
        if run.href and groups and groups[-1][0] == run.href:
            groups[-1][1].append(run)
        else:
            groups.append((run.href, [run]))
    return groups


def _split_edges(text: str) -> tuple[str, str, str]:
    """``(leading space, core, trailing space)`` -- markup goes round the core."""
    core = text.strip()
    if not core:
        return text, "", ""
    lead = text[: len(text) - len(text.lstrip())]
    tail = text[len(text.rstrip()) :]
    return lead, core, tail


# -- plain --------------------------------------------------------------------


def _plain_runs(runs: tuple[Run, ...], *, with_links: bool) -> str:
    parts: list[str] = []
    for href, group in _groups(runs):
        text = "".join(run.text for run in group if not run.image)
        parts.append(text)
        if with_links and href and text.strip() != href:
            parts.append(f" ({href})")
    return "".join(parts)


def _join(blocks: tuple[Block, ...], render_block: Callable[[Block], str]) -> str:
    pieces: list[str] = []
    previous: Block | None = None
    for block in blocks:
        body = render_block(block)
        if not body.strip():
            continue
        if previous is not None:
            pieces.append("\n" if previous.kind == block.kind == BLOCK_ITEM else "\n\n")
        pieces.append(body)
        previous = block
    return "".join(pieces)


def _document_to_plain(document: NotesDocument, *, with_links: bool = False) -> str:
    """Headings, paragraphs and list items as lines; links as their text, or as
    their text then their address in brackets."""
    return _join(
        document.blocks,
        lambda block: block.marker + _plain_runs(block.runs, with_links=with_links),
    )


# -- Markdown -----------------------------------------------------------------

_MD_SPECIAL = re.compile(r"([\\`*_\[\]])")


def _md_escape(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def _md_styled(run: Run) -> str:
    lead, core, tail = _split_edges(_md_escape(run.text))
    if not core:
        return lead
    if run.bold:
        core = f"**{core}**"
    if run.italic:
        core = f"*{core}*"
    return f"{lead}{core}{tail}"


def _md_runs(runs: tuple[Run, ...]) -> str:
    parts: list[str] = []
    for href, group in _groups(runs):
        inner = "".join(_md_styled(run) for run in group if not run.image)
        if href:
            lead, core, tail = _split_edges(inner)
            target = href.replace(")", "%29").replace(" ", "%20")
            inner = f"{lead}[{core}]({target}){tail}" if core else inner
        parts.append(inner)
    return "".join(parts).replace("\n", "  \n")


def _document_to_markdown(document: NotesDocument) -> str:
    def block_md(block: Block) -> str:
        body = _md_runs(block.runs)
        if block.kind == BLOCK_HEADING:
            return f"{'#' * max(1, min(6, block.level))} {body.strip()}"
        if block.kind == BLOCK_ITEM:
            return block.marker + body
        # A paragraph that happens to start like Markdown structure is text.
        return re.sub(r"^(\s*)([#>+-]|\d+\.)(\s)", r"\1\\\2\3", body)

    return _join(document.blocks, block_md)


# -- HTML ---------------------------------------------------------------------


def _html_styled(run: Run, *, images: bool) -> str:
    if run.image:
        return f'<img src="{escape(run.image)}" alt="{escape(run.text)}">' if images else ""
    text = escape(run.text).replace("\n", "<br>")
    if run.bold:
        text = f"<strong>{text}</strong>"
    if run.italic:
        text = f"<em>{text}</em>"
    return text


def _html_runs(runs: tuple[Run, ...], *, images: bool) -> str:
    parts: list[str] = []
    for href, group in _groups(runs):
        inner = "".join(_html_styled(run, images=images) for run in group)
        parts.append(f'<a href="{escape(href)}">{inner}</a>' if href else inner)
    return "".join(parts)


def _document_to_html(
    document: NotesDocument, *, images: bool = True, heading_shift: int = 0
) -> str:
    """An HTML fragment rebuilt from the blocks -- no scripts, no styles, no
    attributes but ``href``, ``src`` and ``alt``, whatever the feed sent."""
    out: list[str] = []
    open_list = ""
    for block in document.blocks:
        body = _html_runs(block.runs, images=images)
        if block.kind == BLOCK_ITEM:
            kind = "ol" if block.marker.strip()[:1].isdigit() else "ul"
            if open_list != kind:
                if open_list:
                    out.append(f"</{open_list}>")
                out.append(f"<{kind}>")
                open_list = kind
            out.append(f"<li>{body}</li>")
            continue
        if open_list:
            out.append(f"</{open_list}>")
            open_list = ""
        if block.kind == BLOCK_HEADING:
            level = max(1, min(6, block.level + heading_shift))
            out.append(f"<h{level}>{body}</h{level}>")
        else:
            out.append(f"<p>{body}</p>")
    if open_list:
        out.append(f"</{open_list}>")
    return "\n".join(out)


def _document_browser_page(
    document: NotesDocument, *, episode_title: str, podcast_title: str
) -> str:
    """The page View in Browser opens: the episode's title as its heading, the
    podcast's name as the page title, the notes as the podcast wrote them, images
    included -- and no scripts, which the policy line enforces as well as omits."""
    title = escape(podcast_title or episode_title or "Show notes")
    heading = escape(episode_title or podcast_title or "Show notes")
    body = _document_to_html(document, images=True, heading_shift=1)
    if document.is_empty and not document.image_count:
        body = "<p>This episode has no show notes.</p>"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "img-src http: https:; style-src 'unsafe-inline'\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n"
        "<style>body{max-width:42em;margin:1em auto;padding:0 1em;"
        "font-family:system-ui,sans-serif;line-height:1.5}img{max-width:100%}</style>\n"
        f"</head>\n<body>\n<main>\n<h1>{heading}</h1>\n{body}\n</main>\n</body>\n</html>\n"
    )


# -- RTF ----------------------------------------------------------------------


def _rtf_escape(text: str) -> str:
    out: list[str] = []
    for char in text:
        code = ord(char)
        if char in "\\{}":
            out.append("\\" + char)
        elif char == "\n":
            out.append("\\line ")
        elif code < 128:
            out.append(char)
        else:
            data = char.encode("utf-16-le")
            for index in range(0, len(data), 2):
                value = int.from_bytes(data[index : index + 2], "little")
                out.append(f"\\u{value - 65536 if value > 32767 else value}?")
    return "".join(out)


def _rtf_styled(run: Run) -> str:
    if run.image:
        return ""
    text = _rtf_escape(run.text)
    if run.bold:
        text = f"{{\\b {text}}}"
    if run.italic:
        text = f"{{\\i {text}}}"
    return text


def _rtf_runs(runs: tuple[Run, ...]) -> str:
    parts: list[str] = []
    for href, group in _groups(runs):
        text = "".join(_rtf_styled(run) for run in group)
        if href:
            target = _rtf_escape(href).replace('"', "%22")
            text = (
                f'{{\\field{{\\*\\fldinst{{HYPERLINK "{target}"}}}}{{\\fldrslt{{\\ul {text}}}}}}}'
            )
        parts.append(text)
    return "".join(parts)


#: Heading sizes in half-points, h1 to h6.
_RTF_HEADING_SIZES = (36, 32, 28, 26, 24, 22)


def _document_to_rtf(document: NotesDocument) -> str:
    out = ["{\\rtf1\\ansi\\ansicpg1252\\deff0{\\fonttbl{\\f0\\fswiss Segoe UI;}}\\f0\\fs22 "]
    previous: Block | None = None
    for block in document.blocks:
        if not block.text.strip():
            continue
        if previous is not None and not (previous.kind == block.kind == BLOCK_ITEM):
            out.append("\\par ")
        body = _rtf_runs(block.runs)
        if block.kind == BLOCK_HEADING:
            size = _RTF_HEADING_SIZES[max(1, min(6, block.level)) - 1]
            out.append(f"{{\\b\\fs{size} {body}}}\\par ")
        else:
            out.append(f"{_rtf_escape(block.marker)}{body}\\par ")
        previous = block
    out.append("}")
    return "".join(out)


def render(document: NotesDocument, fmt: str) -> str:
    """The text a copy in *fmt* puts on the clipboard as its text flavour."""
    fmt = normalize_format(fmt)
    if fmt == PLAIN_LINKS:
        return _document_to_plain(document, with_links=True)
    if fmt == MARKDOWN:
        return _document_to_markdown(document)
    return _document_to_plain(document)


def to_plain(document: NotesDocument | LegacyNotesDocument, *, with_links: bool = False) -> str:
    """Render either generation of the show-notes document as plain text."""
    if isinstance(document, NotesDocument):
        return _document_to_plain(document, with_links=with_links)
    return legacy.to_plain(document, with_links=with_links)


def to_markdown(document: NotesDocument | LegacyNotesDocument) -> str:
    """Render either generation of the show-notes document as Markdown."""
    if isinstance(document, NotesDocument):
        return _document_to_markdown(document)
    return legacy.to_markdown(document)


def to_html(
    document: NotesDocument | LegacyNotesDocument,
    *,
    images: bool = True,
    heading_shift: int = 0,
    title: str = "",
    page_title: str = "",
) -> str:
    """Render either generation of the show-notes document as HTML."""
    if isinstance(document, NotesDocument):
        return _document_to_html(document, images=images, heading_shift=heading_shift)
    return legacy.to_html(document, title=title, page_title=page_title)


def browser_page(
    document: NotesDocument | str,
    *,
    episode_title: str = "",
    podcast_title: str = "",
    title: str = "",
    page_title: str = "",
) -> str:
    """Build a browser page for the structured or legacy show-notes source."""
    if isinstance(document, NotesDocument):
        return _document_browser_page(
            document,
            episode_title=episode_title,
            podcast_title=podcast_title,
        )
    return legacy.browser_page(document, title=title, page_title=page_title)


def to_rtf(document: NotesDocument | LegacyNotesDocument) -> str:
    """Render either generation of the show-notes document as RTF."""
    if isinstance(document, NotesDocument):
        return _document_to_rtf(document)
    return legacy.to_rtf(document)


def export(document: NotesDocument | LegacyNotesDocument, fmt: str) -> str:
    """Return the text flavour for either generation of notes document."""
    if isinstance(document, NotesDocument):
        if normalize_format(fmt) == FORMATTED:
            return _document_to_html(document)
        return render(document, fmt)
    return legacy.export(document, fmt)


def spoken_copy(
    fmt: str,
    document: NotesDocument | LegacyNotesDocument,
    *,
    what: str = "the show notes",
) -> str:
    """Describe a successful copy for either generation of notes document."""
    if isinstance(document, NotesDocument):
        return copied_sentence(fmt, word_count(to_plain(document)), what=what)
    return legacy.spoken_copy(fmt, document, what=what)
