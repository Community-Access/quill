"""What happens to each Scribe output when it is ready (PRD section 9).

| Format | Default action | Where |
|---|---|---|
| Word, EPUB | open in the editor | ``editor`` |
| HTML | open in the editor as a readable document (converted, never markup) | ``editor`` |
| Tagged PDF | open in the editor as text, on the person's command only | ``editor`` |
| BRF | open in QUILL's braille view (QUILL opens a .brf as braille) | ``braille`` |
| MP3, DAISY | open in Media Player | ``player`` |
| MOBI | open in the editor as a readable document (``quill.io.mobi_open``) | ``editor`` |
| Offline web page | saved; the sentence says where | ``save`` |

The offline web page is the accessible HTML with its pictures inside. It is
saved and offered in the browser, never in an editor, where each picture
would be one long line of base64; the accessible HTML is what opens in the
editor (F2). An app that cannot convert it there (one that hands off to
QUILL or Lite) shows it in the browser instead.

"Open each result when it is ready" decides whether the default action runs
or is only offered (7.7). wx-free.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from urllib.parse import unquote

DEFAULT_ACTION: dict[str, str] = {
    "html": "editor",
    "docx": "editor",
    "epub": "editor",
    "brf": "braille",
    "mp3": "player",
    "daisy": "player",
    "pdf": "editor",
    "mobi": "editor",  # QUILL and QUILL Lite read a Kindle book (2026-11-23)
    "offline_html": "save",
}

#: Opened only when the person asks (Open Result, Next Steps), never by itself:
#: a tagged PDF is read as text, a lesser copy of what Word or the HTML gives.
ON_COMMAND_ONLY: frozenset[str] = frozenset({"pdf"})

#: The open result's name in the sentence: "Word is open in QUILL".
OPENED_NAME: dict[str, str] = {
    "html": "The accessible HTML",
    "docx": "Word",
    "pdf": "The tagged PDF",
    "epub": "The EPUB",
    "mobi": "The Kindle book",
    "brf": "The braille",
    "mp3": "The MP3 audio",
    "daisy": "The DAISY book",
}


def open_step(editor: str, format_id: str) -> str:
    """The Next Step that opens a result in *editor*: "Open in QUILL (Word)", and
    for the Kindle book, whose label has brackets of its own, "Open the Kindle
    Book in QUILL" (nested brackets read badly aloud)."""
    from quill.core.scribe.model import format_label

    if format_id == "mobi":
        return f"Open the Kindle Book in {editor}"
    return f"Open in {editor} ({format_label(format_id)})"


def default_action(format_id: str) -> str:
    return DEFAULT_ACTION.get(format_id, "save")


def opened_phrase(format_id: str, where: str) -> str:
    """``"Word is open in QUILL"``."""
    return f"{OPENED_NAME.get(format_id, 'The result')} is open in {where}"


#: Said once, at the end of the result sentence, when the accessible HTML came
#: without its pictures (F2): without the offline web page, how to get it...
PICTURES_NOTE = (
    "The accessible HTML came without its pictures; Download Formats in My Scribe "
    "Documents can add the Web page for offline reading, which has them."
)
#: ...and with it, where it opens.
ZIPPED_PICTURES_NOTE = (
    "Its pictures are in the Web page for offline reading, saved as a zip; "
    "Open Folder in Scribe Conversions shows it."
)
OFFLINE_PICTURES_NOTE = (
    "Its pictures are in the Web page for offline reading; Next Steps opens that in your browser."
)
#: Said once when a Kindle book was made: where it can be read.
MOBI_NOTE = (
    "A Kindle (MOBI) book is for older Kindles: copy it to the Kindle's documents "
    "folder over USB. Amazon's Send to Kindle takes the EPUB instead."
)
#: The Next Step that shows the offline web page, pictures and all.
BROWSER_STEP = "Open in Your Browser (Web page for offline reading)"

_IMG_SRC = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)


def missing_pictures(path: Path) -> int:
    """How many pictures *path* (an HTML file) points at that are not beside it.

    Scribe's accessible HTML names its pictures by relative file name, but the
    download is the HTML alone, so opened on its own its pictures are broken
    (F2). Embedded (``data:``) and web (``http:``) pictures are never missing.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    missing = 0
    for _quote, src in _IMG_SRC.findall(text):
        source = src.strip()
        if not source or re.match(r"^[a-z][a-z0-9+.-]*:", source, re.IGNORECASE):
            continue  # data:, http:, https:, file: ...
        relative = unquote(source.split("#", 1)[0].split("?", 1)[0])
        if not (path.parent / relative).exists():
            missing += 1
    return missing


def open_order(outputs: dict[str, str]) -> list[tuple[str, Path]]:
    """``(format, path)`` in the order Open Result tries them (section 9): the
    accessible HTML stays the HTML, and the offline web page is only saved."""
    from quill.core.scribe.model import valid_formats

    return [(f, Path(outputs[f])) for f in valid_formats(list(outputs))]


def library_order(files: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    """A document's downloaded files (the library's ``(format, path)``) in the
    order Open Result tries them, the newest of each format: what My Scribe
    Documents and Beacon open, rather than whichever was downloaded last (a
    Kindle book or the offline page, which open nowhere)."""
    newest: dict[str, str] = {}
    for format_id, path in files:
        newest[format_id] = str(path)
    return open_order(newest)


#: What a Beacon place points at, best first: a document to read (where a
#: heading can be), then the rest. Never an MP3, a DAISY zip or a BRF while a
#: document is there.
PLACE_ORDER: tuple[str, ...] = (
    "docx",
    "html",
    "epub",
    "pdf",
    "offline_html",
    "brf",
    "daisy",
    "mp3",
    "mobi",
)


def place_order(files: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    """A document's downloaded files in :data:`PLACE_ORDER`, the newest of each."""
    newest: dict[str, Path] = {}
    for format_id, path in files:
        newest[format_id] = Path(path)
    rank = {format_id: index for index, format_id in enumerate(PLACE_ORDER)}
    return sorted(newest.items(), key=lambda item: rank.get(item[0], len(rank)))


def browser_page(outputs: dict[str, str]) -> Path | None:
    """The offline web page when it is one HTML file that exists, else ``None``."""
    offline = outputs.get("offline_html")
    if not offline:
        return None
    path = Path(offline)
    return path if path.suffix.lower() == ".html" and path.exists() else None


def pictures_note(outputs: dict[str, str]) -> str:
    """What to say about the accessible HTML's missing pictures, or ``""``."""
    html = outputs.get("html")
    if not html or not missing_pictures(Path(html)):
        return ""
    if browser_page(outputs) is not None:
        return OFFLINE_PICTURES_NOTE
    if "offline_html" in outputs:
        return ZIPPED_PICTURES_NOTE
    return PICTURES_NOTE


def result_notes(outputs: dict[str, str]) -> str:
    """The sentences said last in the one result sentence: the pictures, then
    the Kindle book."""
    notes = [pictures_note(outputs), MOBI_NOTE if "mobi" in outputs else ""]
    return " ".join(note for note in notes if note)


def daisy_entry(path: Path) -> Path | None:
    """The navigation file of a DAISY result: its ``.ncx`` (DAISY 3) or
    ``ncc.html`` (DAISY 2.02). A zip is unpacked beside itself first, into a
    folder of the same name, never outside it. Which DAISY Scribe writes is
    unconfirmed (PRD 16); both are looked for."""
    folder = path
    if path.is_file() and zipfile.is_zipfile(path):
        folder = path.with_suffix("")
        if not folder.exists():
            folder.mkdir(parents=True)
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    target = (folder / member.filename).resolve()
                    if folder.resolve() not in target.parents and target != folder.resolve():
                        continue  # a name that would leave the folder
                    archive.extract(member, folder)
    if not folder.is_dir():
        return None
    for pattern in ("*.ncx", "ncc.html", "NCC.HTML", "*.opf"):
        found = sorted(folder.rglob(pattern))
        if found:
            return found[0]
    return None


__all__ = [
    "DEFAULT_ACTION",
    "BROWSER_STEP",
    "MOBI_NOTE",
    "ON_COMMAND_ONLY",
    "OFFLINE_PICTURES_NOTE",
    "ZIPPED_PICTURES_NOTE",
    "OPENED_NAME",
    "PLACE_ORDER",
    "PICTURES_NOTE",
    "browser_page",
    "daisy_entry",
    "default_action",
    "library_order",
    "missing_pictures",
    "open_order",
    "open_step",
    "opened_phrase",
    "pictures_note",
    "place_order",
    "result_notes",
]
