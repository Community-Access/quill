"""Full-text article fetch for truncated feeds (plan xxx.md 1.5 "Full-text fetch").

Many feeds ship only a summary. When a subscription opts in (``full_text``), the
reader fetches the linked article and replaces the truncated body with the whole
piece -- rendered the same safe way as feed content: fetched over HTTPS with the
RSS fetch guards (TLS, timeout, size cap, transparent gzip/deflate), narrowed to
the main article region, then run through :func:`sanitize_to_text` so it lands in
the caret stream as accessible plain text (never HTML, never a WebView).

Security lives in the sanitizer, not here: this module only *narrows* hostile
HTML to the readable region as a best effort. If narrowing fails it hands the
whole document to the sanitizer, which still drops script/style/iframe content.
The article is untrusted, so every failure degrades to keeping the summary.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from quill_social.adapters.rss import default_fetch
from quill_social.services.html_sanitize import sanitize_to_text

# A fetch takes a URL and returns the raw article bytes (HTTPS-guarded).
Fetch = Callable[[str], bytes]

# Regions whose content is site chrome, not the article. Dropped best-effort
# before sanitizing (the sanitizer already drops script/style/iframe itself).
_BOILERPLATE_TAGS = ("nav", "aside", "footer", "form")

_TAG_RE = re.compile(r"<(/?)([a-zA-Z][\w:-]*)([^>]*?)>")


def _balanced_region(html: str, tag: str) -> tuple[int, int] | None:
    """Span ``(start, end)`` of the first balanced ``<tag>...</tag>``, or None.

    Only same-tag nesting is counted, so ``<article><article>...`` closes
    correctly. Self-closing occurrences are ignored. This is a best-effort
    narrower over untrusted HTML, never a security boundary.
    """
    depth = 0
    start: int | None = None
    for m in _TAG_RE.finditer(html):
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if name != tag:
            continue
        if attrs.endswith("/"):
            continue  # self-closing, e.g. <br/>
        if not closing:
            if depth == 0:
                start = m.start()
            depth += 1
        elif depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                return start, m.end()
    return None


def _strip_boilerplate(html: str) -> str:
    """Remove site-chrome regions (nav/aside/footer/form) best-effort."""
    for tag in _BOILERPLATE_TAGS:
        # Bounded loop: each pass removes one region and shrinks the string.
        for _ in range(50):
            region = _balanced_region(html, tag)
            if region is None:
                break
            html = html[: region[0]] + html[region[1] :]
    return html


def extract_main_html(html: str) -> str:
    """Narrow a full HTML document to its main article region, best effort.

    Prefers the first ``<article>`` then ``<main>`` region; otherwise keeps the
    whole document. Site chrome is stripped either way. Never raises.
    """
    if not html:
        return ""
    for tag in ("article", "main"):
        region = _balanced_region(html, tag)
        if region is not None:
            return _strip_boilerplate(html[region[0] : region[1]])
    return _strip_boilerplate(html)


def fetch_full_text(url: str, *, fetch: Fetch | None = None) -> str:
    """Fetch ``url`` and return its article as safe, readable plain text.

    Returns ``""`` when the URL is empty, the fetch yields nothing, or extraction
    produces no text. Raises whatever the fetch raises (HTTPS/validation/
    transient errors) so the caller can decide to keep the summary.
    """
    if not url:
        return ""
    raw = (fetch or default_fetch)(url)
    if not raw:
        return ""
    html = raw.decode("utf-8", "replace")
    return sanitize_to_text(extract_main_html(html), base_url=url)


def enrich_item_text(title_and_body: str, full_text: str) -> str:
    """Replace an item's body with ``full_text`` while keeping its title line.

    ``entry_to_item`` builds item text as ``"{title}\\n\\n{body}"``; this swaps
    the body for the full article, or returns the original when there is nothing
    better to show.
    """
    full_text = (full_text or "").strip()
    if not full_text:
        return title_and_body
    head, sep, body = title_and_body.partition("\n\n")
    if sep and len(full_text) > len(body.strip()):
        return f"{head}\n\n{full_text}"
    if not sep and len(full_text) > len(title_and_body.strip()):
        return full_text
    return title_and_body
