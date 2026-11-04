"""Where a link goes, read by the site itself (wordpress.md 9.16, ``url-details``).

WordPress's block editor asks its own site to fetch a page and say its title
and description (``wp-block-editor/v1/url-details``); QUILL asks the same route,
so the address is fetched by the site and not by this computer. Three uses:

* **Hear Where a Link Goes:** the title and description of the link at the
  caret, so a typo in an address is caught before anyone follows it;
* **Fix Link Text:** a "click here" or "read more" link gets the target
  page's own title as its words;
* **Dead links** in Check This Page: a link whose page the site cannot fetch.

Wx-free.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.checks import _VAGUE_LINK_TEXT

URL_DETAILS = "wp-block-editor/v1/url-details"

#: How many links Check This Page looks at, so a long page cannot run for minutes.
MAX_LINKS = 40


@dataclass(frozen=True)
class LinkTarget:
    url: str
    title: str = ""
    description: str = ""
    #: False when the site could not fetch the page: gone, moved, or refusing.
    reachable: bool = True
    why: str = ""

    def spoken(self) -> str:
        if not self.reachable:
            return f"{self.url} could not be reached: {self.why}"
        if not self.title:
            return f"{self.url} has no title."
        about = f" {self.description.rstrip('.')}." if self.description else ""
        return f"Goes to '{self.title}'.{about}"


def read_target(api: WordPressApi, url: str) -> LinkTarget:
    """Ask the site to fetch *url* and say what it is."""
    try:
        raw = api.get(URL_DETAILS, url=url)
    except WordPressApiError as exc:
        if exc.status in (401, 403) and exc.wp_code != "no_response":
            raise
        return LinkTarget(url, reachable=False, why=_gone(exc))
    raw = raw if isinstance(raw, dict) else {}
    return LinkTarget(
        url,
        title=_clean(str(raw.get("title", "") or "")),
        description=_clean(str(raw.get("description", "") or "")),
    )


def _gone(exc: WordPressApiError) -> str:
    if exc.wp_code == "no_response" or exc.status == 404:
        return "the page is not there."
    return exc.plain.rstrip(".") + "."


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


# --------------------------------------------------------------------------- #
# Links in the document's own text


@dataclass(frozen=True)
class DocLink:
    """A link in the document: where it sits, its words, and where it goes."""

    start: int
    end: int
    words: str
    url: str
    text_format: str

    @property
    def vague(self) -> bool:
        return self.words.casefold().strip(" .:!>") in _VAGUE_LINK_TEXT

    def with_words(self, words: str) -> str:
        """This link's markup with new words, in the document's own format."""
        if self.text_format == "html":
            return (
                f'<a href="{html.escape(self.url, quote=True)}">'
                f"{html.escape(words, quote=False)}</a>"
            )
        safe = words.replace("[", r"\[").replace("]", r"\]")
        return f"[{safe}]({self.url})"


_MD_LINK = re.compile(r"(?<!!)\[((?:\\.|[^\]\\])*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_HTML_LINK = re.compile(r"<a\b[^>]*?\bhref\s*=\s*([\"'])(.*?)\1[^>]*>(.*?)</a>", re.I | re.S)


def links_in(text: str, text_format: str) -> list[DocLink]:
    """Every link in *text*, in order. HTML links are found in either format."""
    found: list[DocLink] = []
    if text_format != "html":
        for m in _MD_LINK.finditer(text):
            words = re.sub(r"\\(.)", r"\1", m.group(1))
            found.append(DocLink(m.start(), m.end(), words, m.group(2), "markdown"))
    for m in _HTML_LINK.finditer(text):
        words = _clean(re.sub(r"<[^>]+>", "", m.group(3)))
        found.append(DocLink(m.start(), m.end(), words, html.unescape(m.group(2)), "html"))
    return sorted(found, key=lambda link: link.start)


def link_at(text: str, offset: int, text_format: str) -> DocLink | None:
    """The link the caret is in (or touching), or None."""
    for link in links_in(text, text_format):
        if link.start <= offset <= link.end:
            return link
    return None


def web_links(links: Iterable[DocLink]) -> list[str]:
    """Distinct http and https addresses, in order, at most :data:`MAX_LINKS`."""
    seen: dict[str, None] = {}
    for link in links:
        if link.url.lower().startswith(("http://", "https://")):
            seen.setdefault(link.url, None)
    return list(seen)[:MAX_LINKS]


def dead_links(
    api: WordPressApi, urls: Iterable[str], progress: Callable[[int, int], None] | None = None
) -> list[LinkTarget]:
    """The links among *urls* whose pages the site could not fetch."""
    wanted = list(urls)
    dead: list[LinkTarget] = []
    for number, url in enumerate(wanted, 1):
        target = read_target(api, url)
        if not target.reachable:
            dead.append(target)
        if progress is not None:
            progress(number, len(wanted))
    return dead


def dead_link_sentence(dead: list[LinkTarget], checked: int) -> str:
    if not checked:
        return "No links to other pages."
    if not dead:
        return f"All {checked} links reach their pages."
    noun = "link goes" if len(dead) == 1 else "links go"
    return f"{len(dead)} of {checked} {noun} nowhere."


def fixed_text(text: str, link: DocLink, title: str) -> str:
    """*text* with *link*'s words replaced by *title*."""
    return text[: link.start] + link.with_words(title) + text[link.end :]
