"""Citation and bibliography formatting (issue #203).

Pure formatting for the three styles students meet most often — MLA 9,
Chicago 17 (author-date), and APA 7 — across the three most common source
types (book, journal article, website). The user supplies structured fields;
this module renders both the in-text citation and the bibliography entry.

No ``wx``; pure data and string formatting, fully unit-tested. The deliberate
scope limit (these styles and source types, manual entry) keeps the output
trustworthy: every rule here is covered by a test rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Supported citation styles (value, human label).
CITATION_STYLES: tuple[tuple[str, str], ...] = (
    ("mla", "MLA 9"),
    ("chicago", "Chicago 17 (author-date)"),
    ("apa", "APA 7"),
)

#: Supported source types (value, human label).
SOURCE_TYPES: tuple[tuple[str, str], ...] = (
    ("book", "Book"),
    ("article", "Journal article"),
    ("website", "Website"),
)

_STYLE_VALUES = {value for value, _ in CITATION_STYLES}
_TYPE_VALUES = {value for value, _ in SOURCE_TYPES}


@dataclass(frozen=True, slots=True)
class Source:
    """One cited source. Only the fields relevant to its ``source_type`` are used."""

    source_type: str  # "book" | "article" | "website"
    authors: tuple[str, ...] = ()  # each "First Last"
    title: str = ""
    container: str = ""  # journal name (article) or site name (website)
    publisher: str = ""  # publisher (book)
    year: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    url: str = ""
    accessed: str = ""  # human date, e.g. "3 Mar. 2026"
    metadata: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Name helpers
# --------------------------------------------------------------------------- #


def _split_name(name: str) -> tuple[str, str]:
    """Split "First Middle Last" into (first-and-middle, last)."""
    parts = name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def _initials(given: str) -> str:
    """Turn "Jane Q" into "J. Q." for APA-style initials."""
    return " ".join(f"{p[0]}." for p in given.split() if p)


def _last_name(name: str) -> str:
    return _split_name(name)[1]


def _authors_mla(authors: tuple[str, ...]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        given, last = _split_name(authors[0])
        return f"{last}, {given}".rstrip(", ") if given else last
    if len(authors) == 2:
        given1, last1 = _split_name(authors[0])
        first = f"{last1}, {given1}".rstrip(", ") if given1 else last1
        return f"{first}, and {authors[1]}"
    given1, last1 = _split_name(authors[0])
    first = f"{last1}, {given1}".rstrip(", ") if given1 else last1
    return f"{first}, et al."


def _authors_apa(authors: tuple[str, ...]) -> str:
    formatted = []
    for name in authors:
        given, last = _split_name(name)
        formatted.append(f"{last}, {_initials(given)}".rstrip(", ") if given else last)
    if not formatted:
        return ""
    if len(formatted) == 1:
        return formatted[0]
    return ", ".join(formatted[:-1]) + ", & " + formatted[-1]


def _authors_chicago(authors: tuple[str, ...]) -> str:
    if not authors:
        return ""
    given1, last1 = _split_name(authors[0])
    first = f"{last1}, {given1}".rstrip(", ") if given1 else last1
    if len(authors) == 1:
        return first
    rest = ", and ".join(authors[1:]) if len(authors) == 2 else ", ".join(authors[1:])
    return f"{first}, and {rest}" if len(authors) == 2 else f"{first}, et al."


def _in_text_names(authors: tuple[str, ...]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        return _last_name(authors[0])
    if len(authors) == 2:
        return f"{_last_name(authors[0])} and {_last_name(authors[1])}"
    return f"{_last_name(authors[0])} et al."


def _dot(text: str) -> str:
    """Ensure a trailing period without doubling one."""
    text = text.rstrip()
    return text if text.endswith((".", "?", "!")) else text + "."


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def format_in_text(source: Source, style: str) -> str:
    """Render the parenthetical in-text citation for *source* in *style*."""
    _validate(source, style)
    names = _in_text_names(source.authors) or source.title
    if style == "mla":
        page = f" {source.pages}" if source.pages else ""
        return f"({names}{page})"
    if style == "chicago":
        page = f", {source.pages}" if source.pages else ""
        return f"({names} {source.year}{page})".replace("  ", " ")
    # apa
    page = f", p. {source.pages}" if source.pages else ""
    return f"({names}, {source.year}{page})"


def format_bibliography_entry(source: Source, style: str) -> str:
    """Render the full bibliography / works-cited / references entry."""
    _validate(source, style)
    if style == "mla":
        return _mla_entry(source)
    if style == "chicago":
        return _chicago_entry(source)
    return _apa_entry(source)


def _mla_entry(s: Source) -> str:
    authors = _authors_mla(s.authors)
    parts: list[str] = []
    if authors:
        parts.append(_dot(authors))
    if s.source_type == "book":
        parts.append(f"*{s.title}*." if s.title else "")
        tail = ", ".join(p for p in (s.publisher, s.year) if p)
        if tail:
            parts.append(_dot(tail))
    elif s.source_type == "article":
        parts.append(f'"{s.title}."' if s.title else "")
        meta = [f"*{s.container}*"] if s.container else []
        if s.volume:
            meta.append(f"vol. {s.volume}")
        if s.issue:
            meta.append(f"no. {s.issue}")
        if s.year:
            meta.append(s.year)
        if s.pages:
            meta.append(f"pp. {s.pages}")
        if meta:
            parts.append(_dot(", ".join(meta)))
    else:  # website
        parts.append(f'"{s.title}."' if s.title else "")
        meta = [f"*{s.container}*"] if s.container else []
        if s.year:
            meta.append(s.year)
        if s.url:
            meta.append(s.url)
        if meta:
            parts.append(_dot(", ".join(meta)))
        if s.accessed:
            parts.append(_dot(f"Accessed {s.accessed}"))
    return " ".join(p for p in parts if p)


def _chicago_entry(s: Source) -> str:
    authors = _authors_chicago(s.authors)
    parts: list[str] = []
    if authors:
        parts.append(_dot(authors))
    if s.year:
        parts.append(_dot(s.year))
    if s.source_type == "book":
        parts.append(f"*{s.title}*." if s.title else "")
        if s.publisher:
            parts.append(_dot(s.publisher))
    elif s.source_type == "article":
        parts.append(f'"{s.title}."' if s.title else "")
        loc = f"*{s.container}*" if s.container else ""
        if s.volume:
            loc += f" {s.volume}"
        if s.issue:
            loc += f" ({s.issue})"
        if s.pages:
            loc += f": {s.pages}"
        if loc:
            parts.append(_dot(loc.strip()))
    else:  # website
        parts.append(f'"{s.title}."' if s.title else "")
        if s.container:
            parts.append(_dot(s.container))
        if s.url:
            parts.append(_dot(s.url))
    return " ".join(p for p in parts if p)


def _apa_entry(s: Source) -> str:
    authors = _authors_apa(s.authors)
    parts: list[str] = []
    if authors:
        parts.append(_dot(authors))
    parts.append(f"({s.year}).") if s.year else None
    if s.source_type == "book":
        parts.append(f"*{s.title}*." if s.title else "")
        if s.publisher:
            parts.append(_dot(s.publisher))
    elif s.source_type == "article":
        parts.append(_dot(s.title) if s.title else "")
        loc = f"*{s.container}*" if s.container else ""
        if s.volume:
            loc += f", {s.volume}"
        if s.issue:
            loc += f"({s.issue})"
        if s.pages:
            loc += f", {s.pages}"
        if loc:
            parts.append(_dot(loc))
    else:  # website
        parts.append(f"*{s.title}*." if s.title else "")
        if s.container:
            parts.append(_dot(s.container))
        if s.url:
            parts.append(s.url)
    return " ".join(p for p in parts if p)


def _validate(source: Source, style: str) -> None:
    if style not in _STYLE_VALUES:
        raise ValueError(f"Unknown citation style: {style!r}")
    if source.source_type not in _TYPE_VALUES:
        raise ValueError(f"Unknown source type: {source.source_type!r}")
