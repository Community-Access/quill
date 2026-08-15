"""One book, several libraries: grouping editions into works.

*Middlemarch* found in Project Gutenberg, in Standard Ebooks, as a LibriVox
recording and as an Open Library record is **one book and four rows**, and a
result list that shows it four times has made the listener do the grouping.
Under a screen reader that is worse than it sounds: four near-identical rows,
each read in full, differing only in a source name near the end.

So results group into :class:`Work` -- one row per book, carrying every edition
found, and saying in one sentence what you can do with it: *read it, listen to
it, or neither.*

Three decisions:

* **Grouping is on title and first author, normalised** -- articles, punctuation,
  case and subtitles removed. Deliberately not on ISBN: a public-domain text and
  a volunteer recording of it share no identifier at all, and those are exactly
  the two rows worth putting together.
* **Nothing is hidden.** A grouped row still names every library it was found
  in, and the editions stay reachable, because "which edition" is a real
  question -- a professionally proofread text is not the same as a raw scan.
* **Audio and text are equals.** The hub is for finding a *book*; whether it
  reaches you as a page or a voice is a property of the edition, not a separate
  search. This is what nothing in QUILL previously unified: Quill Radio finds the
  recording, the Library finds the text, and until now they never met.

**The recommended edition.** Where the same work exists as a Standard Ebooks
edition and anywhere else, that one is marked *professionally proofread and
formatted* and sorted first. Not a judgement about the others -- Gutenberg's
texts are the reason most of these exist -- but a proofread, semantically marked
EPUB is materially better with a screen reader, and that is worth saying rather
than leaving somebody to discover.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.library import availability
from quill.core.library.model import Book

#: The source whose editions are marked as recommended, and the phrase used.
RECOMMENDED_SOURCE = "standard-ebooks"
RECOMMENDED_NOTE = "professionally proofread and formatted"

#: Format keys that are audio rather than text. Audio arrives from LibriVox and
#: from the Internet Archive's own recordings; everything else here is reading.
AUDIO_FORMATS: frozenset[str] = frozenset({"audio"})

#: How each source is named out loud. A row says where a book was found, and
#: "standard-ebooks" is an identifier, not a name.
SOURCE_NAMES: dict[str, str] = {
    "gutenberg": "Project Gutenberg",
    "standard-ebooks": "Standard Ebooks",
    "feedbooks": "Feedbooks",
    "googlebooks": "Google Books",
    "openlibrary": "Open Library",
    "bard": "the BARD catalog",
    "librivox": "LibriVox",
    "archive": "the Internet Archive",
}

_ARTICLES = ("the ", "a ", "an ")
_PUNCTUATION = re.compile(r"[^\w\s]+")
_SPACES = re.compile(r"\s+")


def source_name(source: str) -> str:
    """A library's name as a person would say it."""
    return SOURCE_NAMES.get((source or "").strip().lower(), source or "an unnamed source")


def normalise_title(title: str) -> str:
    """A title reduced to what two libraries would agree on.

    Subtitles go, because one catalogue's *Middlemarch* is another's
    *Middlemarch: A Study of Provincial Life* and they are the same book.
    """
    text = (title or "").strip().lower()
    text = text.split(":", 1)[0]
    text = _PUNCTUATION.sub(" ", text)
    text = _SPACES.sub(" ", text).strip()
    for article in _ARTICLES:
        if text.startswith(article):
            text = text[len(article) :]
            break
    return text


def normalise_author(authors: tuple[str, ...]) -> str:
    """The first author reduced to a surname, which is what catalogues share.

    "Eliot, George", "George Eliot" and "Eliot, George, 1819-1880" are one
    person written three ways, and the surname is the only part all three agree
    on -- dates, initials and ordering do not survive a trip through four
    catalogues.
    """
    if not authors:
        return ""
    raw = authors[0].strip().lower()
    raw = re.sub(r"\b\d{3,4}\b", "", raw)  # life dates
    raw = _PUNCTUATION.sub(" ", raw)
    parts = [part for part in _SPACES.sub(" ", raw).split(" ") if len(part) > 1]
    if not parts:
        return ""
    # "eliot george" (comma form, punctuation stripped) -> first token is the
    # surname; "george eliot" -> last. Both reduce to the longest-lived clue
    # available: take whichever token is the surname under each shape.
    return parts[0] if "," in authors[0] else parts[-1]


def work_key(book: Book) -> tuple[str, str]:
    """The identity two editions of one book share."""
    return (normalise_title(book.title), normalise_author(book.authors))


@dataclass(slots=True)
class Work:
    """One book, and every edition of it this search found."""

    title: str
    authors: tuple[str, ...] = ()
    editions: list[Book] = field(default_factory=list)

    @property
    def authors_label(self) -> str:
        return ", ".join(self.authors) if self.authors else "Unknown author"

    @property
    def sources(self) -> list[str]:
        """Every library this work was found in, in the order found."""
        return list(dict.fromkeys(edition.source for edition in self.editions if edition.source))

    @property
    def has_audio(self) -> bool:
        return any(set(edition.formats) & AUDIO_FORMATS for edition in self.editions)

    @property
    def has_text(self) -> bool:
        return any(set(edition.formats) - AUDIO_FORMATS for edition in self.editions)

    @property
    def is_recommended(self) -> bool:
        """Whether a professionally proofread edition is among these."""
        return any(edition.source == RECOMMENDED_SOURCE for edition in self.editions)

    @property
    def best_edition(self) -> Book | None:
        """The edition to act on when somebody just presses Enter.

        A recommended edition first, then anything openable here, then whatever
        there is -- because a work with only a catalogue record still has one
        thing worth doing with it, which is opening the library's own page.
        """
        if not self.editions:
            return None
        return sorted(self.editions, key=_edition_rank)[0]

    @property
    def category(self) -> int:
        """The best thing that can be done with this work, across its editions."""
        best = self.best_edition
        return availability.category(best) if best is not None else availability.CATALOG_RECORD

    def row_label(self) -> str:
        """The whole row, as one sentence.

        Order is chosen for listening: the title first because it is what
        somebody is scanning for, then the author, then what can be done with
        it, then where it came from. The category never moves and never varies
        in wording, so it can be recognised without being read to the end.
        """
        parts = [f"{self.title}, by {self.authors_label}"]
        what = _what_you_can_do(self)
        if what:
            parts.append(what)
        parts.append(availability.CATEGORY_LABELS.get(self.category, "catalog record"))
        found_in = ", ".join(source_name(source) for source in self.sources)
        if found_in:
            parts.append(f"in {found_in}")
        if self.is_recommended:
            parts.append(RECOMMENDED_NOTE)
        return " -- ".join(parts)


def _what_you_can_do(work: Work) -> str:
    if work.has_audio and work.has_text:
        return "read or listen"
    if work.has_audio:
        return "listen"
    if work.has_text:
        return "read"
    return ""


def _edition_rank(book: Book) -> tuple[int, int, str]:
    recommended = 0 if book.source == RECOMMENDED_SOURCE else 1
    openable = 0 if book.formats else 1
    return (recommended, openable, book.source or "")


def group(books: list[Book]) -> list[Work]:
    """Group *books* into works, keeping the order they arrived in.

    Order is preserved rather than re-sorted because the provider order is
    itself a ranking -- the free, openable sources are searched first -- and a
    result list that reshuffles between searches is one nobody can navigate by
    memory.
    """
    works: dict[tuple[str, str], Work] = {}
    ordered: list[Work] = []
    for book in books:
        key = work_key(book)
        existing = works.get(key)
        if existing is None:
            work = Work(title=book.title, authors=book.authors, editions=[book])
            works[key] = work
            ordered.append(work)
            continue
        existing.editions.append(book)
        # Keep the fullest metadata: a record from a bibliographic catalogue
        # often has the author a bare download link lacked.
        if not existing.authors and book.authors:
            existing.authors = book.authors
        # And the plainest title. One catalogue's "Middlemarch" is another's
        # "Middlemarch: A Study of Provincial Life, Volume 1 (Illustrated)", and
        # the shorter one is the book's name -- which is what a row should read
        # as, and what somebody is scanning the list for.
        if len(book.title) < len(existing.title):
            existing.title = book.title
    return ordered


def describe(work: Work) -> str:
    """The details pane: what this is, where it is, and what happens next."""
    lines = [f"{work.title}", f"By {work.authors_label}"]
    if work.has_audio and work.has_text:
        lines.append("Available both to read and to listen to.")
    elif work.has_audio:
        lines.append("Available as a recording.")
    elif work.has_text:
        lines.append("Available to read.")
    best = work.best_edition
    if best is not None:
        lines.append(availability.describe(best))
    for edition in work.editions:
        formats = ", ".join(sorted(edition.formats)) or "no download"
        lines.append(f"{source_name(edition.source)}: {formats}")
    if work.is_recommended:
        lines.append(
            f"Standard Ebooks' edition is {RECOMMENDED_NOTE}, which reads more "
            "reliably with a screen reader than a plain scan."
        )
    return "\n".join(lines)


#: The result filters, as ``(id, label)`` in menu order. Local to the results
#: already fetched: a filter that re-searched would make "show me only the ones
#: I can open" cost a second wait, and the answer is already in hand.
FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "Everything found"),
    ("open", "Only what QUILL can open now"),
    ("read", "Only books to read"),
    ("listen", "Only recordings to listen to"),
)


def apply_filter(works: list[Work], mode: str) -> list[Work]:
    """The subset of *works* a filter shows. An unknown mode shows everything."""
    if mode == "open":
        return [work for work in works if work.category == availability.OPEN_NOW]
    if mode == "read":
        return [work for work in works if work.has_text]
    if mode == "listen":
        return [work for work in works if work.has_audio]
    return list(works)


def summarise(works: list[Work]) -> str:
    """What a search found, counted the way it matters.

    By what can be *done* rather than by how many rows there are: "40 results"
    of which two are openable is a worse answer than the truth, and the whole
    point of the four categories is that the difference is audible.
    """
    if not works:
        return "Nothing found. Try different words."
    openable = sum(1 for work in works if work.category == availability.OPEN_NOW)
    listenable = sum(1 for work in works if work.has_audio)
    total = len(works)
    parts = [f"{total} book{'' if total == 1 else 's'} found"]
    if openable:
        parts.append(f"{openable} you can open here")
    if listenable:
        parts.append(f"{listenable} you can listen to")
    if not openable:
        parts.append("none of them openable in QUILL -- these are catalog records")
    return ", ".join(parts) + "."
