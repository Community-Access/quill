"""Text encoding tools (issue #197).

Three pure, screen-reader-friendly helpers for the encoding friction that
comes up when preparing text for the web:

1. :func:`find_non_ascii` / :func:`summarize_non_ascii` — locate every
   non-ASCII character and report whether it survives a lossless conversion
   to Latin-1 and Windows-1252 (MS-ANSI). This replaces the common
   ``iconv ... --unicode-subst`` + sentinel-search hack.
2. :func:`encode_non_ascii_to_entities` — replace every character above
   U+007F with its HTML named entity (or a numeric ``&#NNNN;`` fallback),
   so downstream tools such as Pandoc never see a high codepoint.
3. :func:`reencode_text` — encode text to a chosen charset, writing any
   character that does not fit as a numeric HTML entity so nothing is
   silently dropped.

No ``wx`` imports; pure data and stdlib only.
"""

from __future__ import annotations

import html.entities
import unicodedata
from dataclasses import dataclass

#: Selectable target encodings for "Re-encode As", as ``(codec, label)`` pairs.
#: ``codec`` is passed straight to :func:`reencode_text`.
ENCODING_CHOICES: tuple[tuple[str, str], ...] = (
    ("utf-8", "UTF-8 (no BOM)"),
    ("utf-8-sig", "UTF-8 with byte-order mark"),
    ("latin-1", "Latin-1 / ISO-8859-1"),
    ("cp1252", "Windows-1252 / MS-ANSI"),
    ("ascii", "ASCII (HTML entities for the rest)"),
)


@dataclass(frozen=True)
class NonAsciiOccurrence:
    """One non-ASCII character and where it sits in the text."""

    line: int  # 1-based line number
    column: int  # 1-based character index within the line
    char: str
    codepoint: int
    name: str  # Unicode name, or "<unnamed>"
    latin1_ok: bool  # losslessly representable in Latin-1 / ISO-8859-1
    cp1252_ok: bool  # losslessly representable in Windows-1252 / MS-ANSI


def find_non_ascii(text: str) -> list[NonAsciiOccurrence]:
    """Return every character above U+007F, in document order."""
    out: list[NonAsciiOccurrence] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for col, ch in enumerate(line, start=1):
            cp = ord(ch)
            if cp < 0x80:
                continue
            try:
                name = unicodedata.name(ch)
            except ValueError:
                name = "<unnamed>"
            out.append(
                NonAsciiOccurrence(
                    line=line_no,
                    column=col,
                    char=ch,
                    codepoint=cp,
                    name=name,
                    latin1_ok=_encodable(ch, "latin-1"),
                    cp1252_ok=_encodable(ch, "cp1252"),
                )
            )
    return out


def _encodable(ch: str, encoding: str) -> bool:
    try:
        ch.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def summarize_non_ascii(text: str) -> str:
    """Render a plain-text report of the non-ASCII characters in *text*.

    Designed to be opened in a read-only buffer and reviewed with a screen
    reader: one character per line, with codepoint, convertibility, and name.
    """
    occurrences = find_non_ascii(text)
    if not occurrences:
        return "No non-ASCII characters found. This document is pure ASCII.\n"

    lines = [
        f"Found {len(occurrences)} non-ASCII character(s).",
        "",
        "Each row: line:column, character, codepoint, Latin-1 ok, Windows-1252 ok, Unicode name.",
        "",
    ]
    for occ in occurrences:
        shown = occ.char if occ.char.isprintable() else "(non-printing)"
        latin1 = "Latin-1 yes" if occ.latin1_ok else "Latin-1 NO"
        cp1252 = "Win-1252 yes" if occ.cp1252_ok else "Win-1252 NO"
        lines.append(
            f"{occ.line}:{occ.column}\t{shown}\tU+{occ.codepoint:04X}\t"
            f"{latin1}\t{cp1252}\t{occ.name}"
        )

    lossy = [occ for occ in occurrences if not occ.cp1252_ok]
    if lossy:
        lines += [
            "",
            f"{len(lossy)} character(s) cannot be converted losslessly to "
            "Windows-1252 (MS-ANSI). First occurrence of each:",
        ]
        seen: set[int] = set()
        for occ in lossy:
            if occ.codepoint in seen:
                continue
            seen.add(occ.codepoint)
            lines.append(
                f"  U+{occ.codepoint:04X} {occ.name} (line {occ.line}, column {occ.column})"
            )
    return "\n".join(lines) + "\n"


def encode_non_ascii_to_entities(text: str, *, prefer_named: bool = True) -> str:
    """Replace every character above U+007F with an HTML entity.

    Named entities (``&eacute;``) are used when one exists and
    ``prefer_named`` is true; otherwise a numeric entity (``&#233;``) is
    emitted. ASCII characters, including ``&`` and ``<``, are left untouched
    so already-valid markup is preserved.
    """
    parts: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x80:
            parts.append(ch)
            continue
        name = html.entities.codepoint2name.get(cp) if prefer_named else None
        parts.append(f"&{name};" if name else f"&#{cp};")
    return "".join(parts)


def reencode_text(text: str, encoding: str) -> bytes:
    """Encode *text* to *encoding*, never losing data.

    For narrow encodings (ASCII, Latin-1, Windows-1252) any character that
    does not fit is written as a numeric HTML entity (``xmlcharrefreplace``),
    so the round-trip is visible and recoverable rather than a silent ``?``.
    UTF-8 variants encode everything directly.
    """
    if encoding in ("utf-8", "utf-8-sig"):
        return text.encode(encoding)
    return text.encode(encoding, errors="xmlcharrefreplace")
