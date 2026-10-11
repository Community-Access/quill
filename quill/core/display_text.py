"""Publisher text, made fit to read: entities decoded however often they were encoded.

Show notes, episode and show titles, station names and calendar entries all
arrive from somebody else's software, and a great deal of that software encodes
its text more than once. WordPress and its podcast plugins are the common case:
an apostrophe goes out as ``&amp;#8217;``, the feed parser takes one layer off,
the HTML parser takes another, and what is left is ``&#8217;`` -- which a screen
reader spells out, code and all, in the middle of every contraction (reported
on the QUILLVille list, 2026-10-11, against Quill Radio 3.2).

Plain-text notes had the same fault from the other direction: a description
with no tags in it was passed through untouched, so its entities were never
decoded at all.

Two rules keep this safe:

* **Only well-formed references are decoded** -- ``&name;``, ``&#123;`` and
  ``&#x7B;``, each with its semicolon. ``html.unescape`` on its own also
  decodes legacy names *without* a semicolon, which turns a query string such
  as ``?a=1&copy=2`` in a plain-text note into ``?a=1(c)=2``.
* **Decoding repeats until nothing changes, at most three times.** That covers
  every double and triple encoding seen in real feeds, and the cap means text
  that is genuinely about entities ("write &amp;amp; for an ampersand") is not
  ground down to nothing.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import html
import re

__all__ = [
    "clean_display_text",
    "decode_entities",
    "unwrap_escaped_html",
]

#: A complete character reference: named, decimal or hexadecimal, semicolon
#: required. Nothing looser, for the reason in the module docstring.
_ENTITY_RE = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")

#: How many layers of encoding are taken off before stopping.
_MAX_PASSES = 3

#: An escaped tag, such as ``&lt;p&gt;`` or ``&lt;/a&gt;``: HTML that was
#: published as text.
_ESCAPED_TAG_RE = re.compile(r"&lt;\s*/?\s*[A-Za-z][A-Za-z0-9]*[\s/&]")

#: Characters that look like nothing, or like a space, and read badly. A
#: non-breaking space becomes a space; zero-width characters and a stray
#: byte-order mark are removed.
_INVISIBLE = str.maketrans({
    "\u00a0": " ",
    "\u2007": " ",
    "\u202f": " ",
    "\u200b": None,
    "\u200c": None,
    "\u200d": None,
    "\u2060": None,
    "\ufeff": None,
})


def _decode_one(match: re.Match[str]) -> str:
    return html.unescape(match.group(0))


def decode_entities(text: str) -> str:
    """*text* with every well-formed character reference decoded, repeatedly.

    ``Don&amp;#8217;t`` and ``Don&#8217;t`` both come back as ``Don\u2019t``;
    an unknown name such as ``&nosuch;`` is left as it is.
    """
    if not text:
        return ""
    for _ in range(_MAX_PASSES):
        if "&" not in text:
            break
        decoded = _ENTITY_RE.sub(_decode_one, text)
        if decoded == text:
            break
        text = decoded
    return text


def clean_display_text(text: str) -> str:
    """Decode entities and tidy invisible characters, for text a person reads.

    Lengths can change (a zero-width space is removed), so call this on text
    *before* recording positions in it, never after.
    """
    return decode_entities(text or "").translate(_INVISIBLE)


def unwrap_escaped_html(content: str) -> str:
    """Real markup for HTML that was published as escaped text.

    A good many feeds put ``&lt;p&gt;Hello&lt;/p&gt;`` in a plain-text field. Read
    as text, that shows its tags; this takes the escaping off so the caller's
    HTML parser sees ``<p>Hello</p>``. Content that already has tags, or has no
    escaped ones, is returned unchanged.
    """
    content = content or ""
    if "<" in content or not _ESCAPED_TAG_RE.search(content):
        return content
    return decode_entities(content)
