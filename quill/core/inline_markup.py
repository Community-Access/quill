"""One spelling for emphasis, so a conversion cannot quietly drop it.

QUILL writes emphasis in Markdown two ways, and until this module existed only
one of them survived a format switch:

* **Pandoc spans** -- ``[text]{underline}``, ``[text]{strike}`` -- which
  ``markdown_to_rtf`` renders to real ``\\ul`` / ``\\strike`` runs and
  ``rtf_to_markdown`` writes back out. This is the canonical form, because it is
  the one the rich-text bridge round-trips.
* **Inline HTML and GFM** -- ``<u>text</u>`` (Markdown has no underline syntax,
  so Insert Tag emits HTML, which is legal Markdown) and ``~~text~~`` for
  strikethrough.

The second group was invisible to every converter. Underline typed into a
Markdown document therefore reached Rich Text as the literal characters
``<u>text</u>`` sitting in the paragraph, and reached plain text the same way --
not underlined, not stripped, just *there*, looking like something the author
typed on purpose. The words were all present, so nothing looked broken enough
to report.

This module normalises the second group into the first, once, in front of the
converters that only understand the first. It is deliberately **narrow**: only
tags that mean emphasis, only when properly closed, and never inside a code
span, because ``<u>`` inside backticks is a person writing *about* HTML.
"""

from __future__ import annotations

import re

__all__ = ["normalize_inline_markup"]

#: ``(pattern, replacement)`` in application order. Bold before italic so
#: ``<strong>`` is not seen as a stray ``<s>``-alike, and the HTML forms before
#: the GFM ones purely for readability -- they cannot overlap.
_NORMALISERS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Underline: the whole reason this module exists. No Markdown syntax means
    # HTML is the only way to write it, and the span is the only way to carry it.
    (re.compile(r"<u>(.+?)</u>", re.IGNORECASE | re.DOTALL), r"[\1]{underline}"),
    (re.compile(r"<ins>(.+?)</ins>", re.IGNORECASE | re.DOTALL), r"[\1]{underline}"),
    # Strikethrough: GFM's own syntax and the three HTML spellings of it.
    (re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.DOTALL), r"[\1]{strike}"),
    (re.compile(r"<s>(.+?)</s>", re.IGNORECASE | re.DOTALL), r"[\1]{strike}"),
    (re.compile(r"<strike>(.+?)</strike>", re.IGNORECASE | re.DOTALL), r"[\1]{strike}"),
    (re.compile(r"<del>(.+?)</del>", re.IGNORECASE | re.DOTALL), r"[\1]{strike}"),
    # Bold and italic have native Markdown, so they normalise to *that* rather
    # than to a span -- the span form exists for what Markdown cannot say.
    (re.compile(r"<(?:b|strong)>(.+?)</(?:b|strong)>", re.IGNORECASE | re.DOTALL), r"**\1**"),
    (re.compile(r"<(?:i|em)>(.+?)</(?:i|em)>", re.IGNORECASE | re.DOTALL), r"*\1*"),
)

#: Fenced blocks and inline code spans, matched together so their contents can
#: be lifted out before any rewriting and put back afterwards untouched.
_PROTECTED = re.compile(r"(?s)(```.*?```|~~~.*?~~~|``.*?``|`[^`\n]*`)")


def normalize_inline_markup(text: str) -> str:
    """Rewrite inline HTML and GFM emphasis into the forms converters understand.

    Code is protected: ```<u>hello</u>``` is somebody writing about the tag
    and must survive verbatim, which is also why the fenced-block forms are
    matched here and not only the inline one.

    Idempotent -- running it twice changes nothing the second time, which
    matters because a document may be converted back and forth all afternoon.
    """
    if not text:
        return text
    parts = _PROTECTED.split(text)
    # split() with one capture group alternates: text, code, text, code, ...
    for index in range(0, len(parts), 2):
        chunk = parts[index]
        for pattern, replacement in _NORMALISERS:
            chunk = pattern.sub(replacement, chunk)
        parts[index] = chunk
    return "".join(parts)
