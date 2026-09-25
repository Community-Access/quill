"""Moving a document between plain text, Markdown, HTML and Rich Text.

The switcher used to do one conversion and then relabel the result. Leaving
rich mode always produced *Markdown* -- ``rtf_to_markdown`` -- and then pinned
whatever format the user actually asked for on top of it, so:

* **RTF to plain text** handed back ``# Heading`` and ``**bold**`` and called it
  plain text, which is the one thing plain text is not.
* **RTF to HTML**, and **Markdown to HTML**, produced ``# Heading`` under an
  HTML label -- a document that claims to be HTML and contains none.

Both are the same bug: *the label moved and the text did not.* Nothing on
screen says so, because the words are all still there and only their markers
are wrong, which is exactly the kind of mistake that surfaces later in a
published file rather than now.

So every switch runs a real conversion, and **Markdown is the pivot**: each
format converts into Markdown and back out again, which is what makes six
direction pairs out of four converters instead of twelve bespoke ones. The
pivot is not arbitrary -- it is already the canonical form the editor buffer
holds, so the markup/markup switches cost nothing when the pivot *is* the
destination.

**Plain text is a question, not a conversion.** Going to plain text with
Markdown in the buffer has two honest answers -- keep ``# Heading`` as the
literal characters a plain-text file is allowed to contain, or strip it to
``Heading`` and mean it -- and no way to guess which one somebody wants.
:func:`plan_transition` reports when the question has to be asked;
:class:`PlainStyle` is the answer. It is only asked when there is something to
ask about: plain text that contains no markers converts silently either way.

wx-free and strict-typed: every rule above is directly unit-testable, and the
dialog that asks the question owns none of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "FORMATS",
    "FORMAT_LABELS",
    "PlainStyle",
    "TransitionPlan",
    "convert_text",
    "has_markdown_markup",
    "plan_transition",
]

#: The four formats the editor can hold a document in and move between.
FORMATS: tuple[str, ...] = ("plain", "markdown", "html", "rtf")

#: Spoken names, so a dialog and a status line never word the same format two
#: ways. Matches ``DOCUMENT_FORMATS`` in the UI, which owns the file suffixes.
FORMAT_LABELS: dict[str, str] = {
    "plain": "Plain text",
    "markdown": "Markdown",
    "html": "HTML",
    "rtf": "Rich Text (RTF)",
}


class PlainStyle(StrEnum):
    """What "convert to plain text" should do with Markdown already in the text."""

    #: Take the markers off: ``# Heading`` becomes ``Heading``. Strictly plain.
    STRIP = "strip"
    #: Leave them as the literal characters they are. A plain-text file may
    #: perfectly well contain a ``#``; some people keep their notes that way and
    #: would rather nothing touched them.
    KEEP = "keep"


#: Markers that mean a plain-text conversion has a real question to ask. Kept
#: deliberately conservative -- each one has to be unambiguous enough that its
#: presence is worth interrupting somebody over. A lone ``*`` in prose is not.
_MARKDOWN_SIGNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?m)^\s{0,3}#{1,6}\s+\S"),  # ATX heading
    re.compile(r"\*\*[^*\n]+\*\*"),  # bold
    re.compile(r"(?m)^\s{0,3}(?:[-+*]|\d+[.)])\s+\S"),  # list item
    re.compile(r"\[[^\]\n]+\]\([^)\n]+\)"),  # inline link
    re.compile(r"(?m)^```"),  # fenced code
    re.compile(r"(?m)^\s{0,3}>\s"),  # block quote
    re.compile(r"~~[^~\n]+~~"),  # strikethrough
)


def has_markdown_markup(text: str) -> bool:
    """Whether *text* carries Markdown worth asking about before flattening it.

    The question this answers is not "is this a Markdown document" but the much
    narrower "would converting this to plain text visibly change it". A document
    of ordinary prose answers False and is converted without a prompt, because a
    dialog that appears when nothing is at stake is how people learn to dismiss
    dialogs without reading them.
    """
    return any(pattern.search(text) for pattern in _MARKDOWN_SIGNS)


@dataclass(frozen=True, slots=True)
class TransitionPlan:
    """What a switch is about to do, decided before anything has been converted.

    The caller asks first and converts second, so a cancelled prompt costs
    nothing and a confirmed one converts exactly what was described.
    """

    source: str
    target: str
    #: True when the target is plain text and the buffer has Markdown in it, so
    #: the caller must ask which :class:`PlainStyle` the person wants.
    asks_plain_style: bool = False
    #: True when the conversion cannot carry everything the document has. Real
    #: formatting (an RTF document's bold runs, fonts and colours) becomes
    #: characters or nothing at all, and the buffer is the only copy.
    warns_lossy: bool = False
    #: One sentence naming what will happen, for the dialog and the status line.
    summary: str = ""

    @property
    def needs_prompt(self) -> bool:
        """Whether anything has to be asked before converting."""
        return self.asks_plain_style or self.warns_lossy


def plan_transition(text: str, source: str, target: str) -> TransitionPlan:
    """Decide what switching *source* to *target* involves, and what to ask.

    Unknown formats and a switch to the format you are already in both plan to
    do nothing, so a caller may plan unconditionally.
    """
    if source not in FORMATS or target not in FORMATS or source == target:
        return TransitionPlan(source=source, target=target)

    source_label = FORMAT_LABELS.get(source, source)
    target_label = FORMAT_LABELS.get(target, target)

    if target == "plain":
        # Rich text is lossy *and* -- once it has been through the pivot -- has
        # markers to ask about, so it can legitimately raise both.
        asks = source == "rtf" or has_markdown_markup(text)
        lossy = source == "rtf"
        if lossy:
            summary = (
                f"{source_label} to {target_label} cannot carry real formatting. "
                "Bold, fonts and colours become plain characters or are dropped."
            )
        else:
            summary = (
                f"{source_label} to {target_label}: the markers are the question. "
                "They can stay as ordinary characters, or come off entirely."
            )
        return TransitionPlan(
            source, target, asks_plain_style=asks, warns_lossy=lossy, summary=summary
        )

    if source == "rtf":
        return TransitionPlan(
            source,
            target,
            warns_lossy=True,
            summary=(
                f"{source_label} to {target_label} keeps headings, bold and italic as "
                f"{target_label} markup. Fonts, colours and page layout are not carried."
            ),
        )

    return TransitionPlan(
        source,
        target,
        summary=f"{source_label} to {target_label}: the markup is rewritten, the words are kept.",
    )


def _to_markdown(text: str, source: str) -> str:
    """*text* as Markdown, whatever it started as. The pivot's inbound half."""
    if source == "html":
        from quill.core.html_to_markdown import contains_html_markup, html_to_markdown

        # Guarded on the content, not the label: a document pinned as HTML that
        # holds no tags is already Markdown, and running it through the reader
        # would only risk mangling text it has no business touching.
        if not contains_html_markup(text):
            return text
        converted = html_to_markdown(text)
        return converted if converted.strip() else text
    if source == "rtf":
        from quill.io.rtf import rtf_to_markdown

        return rtf_to_markdown(text)
    # "plain" and "markdown" alike: plain text *is* valid Markdown, and treating
    # it as such is what lets a plain note become a heading by typing one.
    return text


def _from_markdown(
    markdown: str, target: str, *, plain_style: PlainStyle, title: str, charset: str
) -> str:
    """Markdown rendered as *target*. The pivot's outbound half."""
    if target == "html":
        from quill.io.export import markdown_to_html

        return markdown_to_html(markdown, title, charset=charset)
    if target == "rtf":
        from quill.io.rtf import markdown_to_rtf

        return markdown_to_rtf(markdown)
    if target == "plain" and plain_style is PlainStyle.STRIP:
        from quill.io.export import markdown_to_plain_text

        return markdown_to_plain_text(markdown)
    return markdown


def convert_text(
    text: str,
    source: str,
    target: str,
    *,
    plain_style: PlainStyle = PlainStyle.STRIP,
    title: str = "Document",
    charset: str = "utf-8",
) -> str:
    """Convert *text* from *source* to *target*, through the Markdown pivot.

    ``plain_style`` is read only when *target* is ``"plain"``; ask for it with
    :func:`plan_transition` rather than guessing, and note that the default is
    :attr:`PlainStyle.STRIP` so a caller that forgets produces plain text that
    really is plain rather than Markdown wearing a plain label -- the failure
    this module exists to end.

    A switch to the format you are already in, or either side being unknown,
    returns *text* untouched: a no-op switch must never rewrite a buffer.
    """
    if source not in FORMATS or target not in FORMATS or source == target:
        return text
    markdown = _to_markdown(text, source)
    return _from_markdown(markdown, target, plain_style=plain_style, title=title, charset=charset)
