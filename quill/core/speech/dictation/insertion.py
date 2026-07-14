"""Conservative transcript normalization for insertion (PRD §17).

A single pure function that decides exactly what string to splice into the editor
given the raw Whisper transcript and the one character on each side of the caret.
The PRD is explicit that the first release must be *conservative* — trim stray
whitespace, add at most one joining space between adjoining words, avoid a space
before punctuation — and must **not** rewrite grammar or capitalization
aggressively. Keeping this wx-free and pure makes the spacing rules directly
unit-testable (PRD §32.4).
"""

from __future__ import annotations

# Punctuation that should hug the preceding word: never emit a space before it.
_NO_LEADING_SPACE_BEFORE = set(".,;:!?)]}%")
# Characters after which we should not inject a joining space (open brackets,
# whitespace, or a hard line break already present in the document).
_NO_JOIN_AFTER = set("([{ \t\n\r")


def normalize_for_insertion(
    transcript: str,
    *,
    prefix_char: str = "",
    suffix_char: str = "",
    intelligent_spacing: bool = True,
) -> str:
    """Return the exact text to insert at the caret.

    ``prefix_char`` is the character immediately before the caret (empty at the
    start of the document); ``suffix_char`` the character immediately after.
    When ``intelligent_spacing`` is on (the default), a single joining space is
    added before the transcript if the previous character is a word character
    and the transcript does not already start with punctuation, and a trailing
    space is added when the caret is not immediately before more text — matching
    the everyday "dictate a phrase, keep typing" flow. With it off, only
    surrounding whitespace is trimmed.
    """
    text = transcript.strip()
    if not text:
        return ""
    if not intelligent_spacing:
        return text

    first = text[0]
    last = text[-1]

    lead = ""
    if prefix_char and prefix_char not in _NO_JOIN_AFTER and first not in _NO_LEADING_SPACE_BEFORE:
        lead = " "

    trail = ""
    # Add a trailing space so the next spoken phrase or typed word does not run
    # into this one — but only when we are not butting up against existing text
    # or punctuation that should hug the word.
    if last not in _NO_LEADING_SPACE_BEFORE:
        if suffix_char == "" or suffix_char in {" ", "\t", "\n", "\r"}:
            trail = " "

    return f"{lead}{text}{trail}"
