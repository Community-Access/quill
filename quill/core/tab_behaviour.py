"""What the Tab key does, decided by the kind of document you are in.

Two editors had two answers and neither asked the document: QUILL indented the
line always, QUILL Lite typed a tab always, and each had a toggle to get the
other behaviour (bad.md T3, P1.21). Both defaults are right somewhere and wrong
somewhere else -- typing a tab into a Markdown list item breaks the list, and
indenting the line in a plain note is not what a Notepad replacement does --
which is the shape of a decision that belongs on the document kind, next to
``autoformat_allows`` and for the same reason: both editors already know the
kind, and it is the thing that decides what Ctrl+B writes and whether a leading
``#`` is a heading.

The rule is one sentence: **in markup, Tab indents; everywhere else it types a
tab.** Markdown and HTML are structures where indentation *means* something --
a nested list item, a continuation line -- and a literal tab in them is at best
invisible and at worst a broken list. Plain text and rich text have no such
structure, so the key does what every plain-text editor on Windows does with
it, which is type one.

The toggle stays, in both editors, and still wins: this decides only what a
document starts out doing, so nobody who has said "type a tab here" is
overruled by the file's extension.

wx-free and directly tested.
"""

from __future__ import annotations

__all__ = ["MARKUP_KINDS", "tab_inserts_a_tab"]

#: Kinds where indentation is structure rather than whitespace.
MARKUP_KINDS = frozenset({"markdown", "html", "xhtml", "htm"})


def tab_inserts_a_tab(kind: str | None) -> bool:
    """Whether Tab types a tab character in a document of this *kind*.

    ``True`` for plain text, rich text and anything unrecognised; ``False`` for
    Markdown and HTML, where the key indents instead.

    ``None`` means "unknown", which types a tab: an untitled buffer is a note
    far more often than it is a structured document, and the failure in that
    direction is one character somebody can see and delete, where the other
    direction silently re-indents a line they did not ask to move.
    """
    if kind is None:
        return True
    return kind.strip().lower() not in MARKUP_KINDS
