"""Every link in a piece of text or HTML, as a list somebody can act on.

Show notes and transcripts are full of addresses -- the thing the host said to
go and look at, the sponsor, the guest's site, the paper being discussed -- and
until now the only way to reach one was to read the address out of a read-only
text box and retype it. That is the least accessible possible way to follow a
link, and it is the one QUILL was offering.

So this pulls them out. It handles both shapes the app actually has:

* **HTML** (a podcast's ``description``), where the address is in an ``href``
  and the useful name is the link's own text -- "the paper we discussed" is a
  better row than ``https://arxiv.org/abs/2408.01234``.
* **Plain text** (a transcript, or notes already flattened), where an address
  is whatever looks like one. Trailing punctuation is trimmed, because a
  sentence ending "...see https://example.com/thing." does not contain a link
  whose last character is a full stop.

Two rules worth stating:

**The same address twice is one row.** A show note that links a sponsor in the
first paragraph and again in the last is one place to go, not two -- but the
first link's *text* wins, because that is where it was explained.

**Only addresses a browser can open.** ``http`` and ``https`` and nothing else:
a ``javascript:`` or ``file:`` href in somebody else's show notes is not
something this app hands to a listener as a thing to click.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

#: What counts as a link in plain text: a scheme we can open, then anything
#: that is not whitespace or a quote. Brackets are *allowed* through here and
#: sorted out by :func:`_tidy`, because plenty of real addresses carry balanced
#: parentheses -- excluding them outright truncated every Wikipedia link.
_BARE_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

#: Punctuation that ends a sentence rather than an address.
_TRAILING = ".,;:!?'\"’”)]}"


@dataclass(frozen=True, slots=True)
class Link:
    """One address, and what to call it in a list."""

    url: str
    #: The link's own text where there was one, else "".
    text: str = ""

    @property
    def label(self) -> str:
        """The row a listener hears: the name, then the address.

        Both, always. The name alone hides where a link goes, which is the one
        fact somebody deciding whether to open it actually needs; the address
        alone is a string of characters nobody can skim.
        """
        name = " ".join(self.text.split())
        return f"{name} -- {self.url}" if name and name != self.url else self.url

    @property
    def row(self) -> str:
        """The row the Links window reads: the title, then where it goes.

        "Support the show on Patreon, patreon.com/thedaily" (qc.md 5c): the title
        is what somebody arrows through, and the address -- shortened to where it
        goes -- is there at the end of the row for whoever wants it. A link with no
        title of its own is its address.
        """
        name = " ".join(self.text.split())
        where = where_it_goes(self.url)
        if not name or name in (self.url, where):
            return where or self.url
        return f"{name}, {where}"


def _tidy(url: str) -> str:
    """One raw address, trimmed of the sentence it was sitting in.

    One character at a time from the right, because the balance test has to run
    *before* a closing bracket is taken: a blanket strip removes the one in
    ``.../Turing_(disambiguation)`` along with the full stop in "...see
    example.com/thing." and only one of those is punctuation.
    """
    cleaned = unescape(url.strip())
    while cleaned:
        last = cleaned[-1]
        # A closing bracket is only rubbish when nothing opened it -- plenty of
        # real addresses carry balanced parentheses (Wikipedia's, for one).
        if last == ")" and cleaned.count("(") >= cleaned.count(")"):
            break
        if last not in _TRAILING:
            break
        cleaned = cleaned[:-1]
    return cleaned


def _openable(url: str) -> bool:
    return url.lower().startswith(("http://", "https://"))


class _LinkParser(HTMLParser):
    """Collects ``(href, link text)`` pairs in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[Link] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._flush()
        self._href = next((value or "" for name, value in attrs if name.lower() == "href"), "")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self._flush()

    def _flush(self) -> None:
        if self._href:
            url = _tidy(self._href)
            if _openable(url):
                self.found.append(Link(url=url, text="".join(self._text).strip()))
        self._href = ""
        self._text = []

    def close(self) -> None:
        super().close()
        self._flush()


def _dedupe(links: list[Link]) -> list[Link]:
    """First mention wins, and keeps its text."""
    seen: set[str] = set()
    kept: list[Link] = []
    for link in links:
        key = link.url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(link)
    return kept


def links_in_html(html: str) -> list[Link]:
    """Every openable link in *html*, in document order. Never raises."""
    if not html or "<" not in html:
        return links_in_text(html or "")
    parser = _LinkParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - somebody else's HTML must never crash a menu
        pass
    # Plus any bare address that was typed rather than linked, which is most of
    # them in a hand-written show note.
    return _dedupe([*parser.found, *links_in_text(html)])


def links_in_text(text: str) -> list[Link]:
    """Every openable address in plain *text*, in the order it appears."""
    found = [Link(url=_tidy(match.group(0))) for match in _BARE_URL.finditer(text or "")]
    return _dedupe([link for link in found if _openable(link.url)])


def bare_url_spans(text: str) -> list[tuple[int, int, str]]:
    """``(start, end, address)`` for every openable address typed into *text*.

    The span is the *tidied* address, so trailing sentence punctuation stays
    outside it: the Notes reader (qc.md 5c) turns these into links in place, and
    a link that swallowed the full stop after it would underline the end of the
    sentence as well.
    """
    spans: list[tuple[int, int, str]] = []
    for match in _BARE_URL.finditer(text or ""):
        url = _tidy(match.group(0))
        if url and _openable(url):
            spans.append((match.start(), match.start() + len(url), url))
    return spans


def where_it_goes(url: str) -> str:
    """The address as a listener wants to hear it: no scheme, no ``www.``.

    "patreon.com/thedaily" rather than "https colon slash slash www dot...":
    the Links window reads the title first and this second (qc.md 5c), so the
    part worth hearing is where the link goes, not how.
    """
    shown = re.sub(r"^[a-z][a-z0-9+.-]*://", "", (url or "").strip(), flags=re.IGNORECASE)
    if shown.lower().startswith("www."):
        shown = shown[4:]
    return shown.rstrip("/")


def find_links(content: str, *, is_html: bool = False) -> list[Link]:
    """Links in *content*, treating it as HTML or as plain text."""
    return links_in_html(content) if is_html else links_in_text(content)


def describe(links: list[Link]) -> str:
    """What to say when the list opens, or when there is nothing in it."""
    if not links:
        return "No links here."
    return f"{len(links)} link{'' if len(links) == 1 else 's'}."
