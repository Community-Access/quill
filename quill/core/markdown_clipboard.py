"""The "Markdown clipboard format" setting (markdown_clipboard_format).

Copy With Source always puts plain text on the clipboard -- the Markdown as you
wrote it, with the source note under it. In a Markdown document this setting can
add a *formatted* copy beside that text, so pasting into Word, Outlook or a web
form shows headings, bold and links instead of the symbols:

* ``text`` -- plain text only (the default, and what QUILL always did).
* ``html`` -- plain text plus an HTML copy.
* ``rtf``  -- plain text plus a Rich Text copy, for programs that prefer it.

A program that only takes plain text (Notepad, QUILL itself) still gets the
plain text either way, because the clipboard holds both.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

MODES = ("text", "html", "rtf")
DEFAULT_MODE = "text"


@dataclass(frozen=True, slots=True)
class FormattedCopy:
    """The extra clipboard flavour: ``kind`` is "html" or "rtf"."""

    kind: str
    data: str


def clipboard_mode(settings: object) -> str:
    raw = str(getattr(settings, "markdown_clipboard_format", DEFAULT_MODE) or "").strip().lower()
    return raw if raw in MODES else DEFAULT_MODE


def formatted_copy(text: str, *, document_kind: str, mode: str) -> FormattedCopy | None:
    """The formatted flavour to place beside *text*, or None for plain text only.

    Only a Markdown document gets one: rendering plain prose or HTML source as
    "formatted Markdown" would change what the user copied.
    """
    if document_kind != "markdown" or mode not in {"html", "rtf"} or not text.strip():
        return None
    if mode == "html":
        from quill.core.browser_preview import render_preview_body

        return FormattedCopy("html", render_preview_body(text, "markdown"))
    from quill.io.rtf import markdown_to_rtf

    return FormattedCopy("rtf", markdown_to_rtf(text))


__all__ = ["DEFAULT_MODE", "MODES", "FormattedCopy", "clipboard_mode", "formatted_copy"]
