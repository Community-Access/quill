"""Match the typed-character buffer against the shared abbreviation library.

The library is exactly the one QUILL's editor uses
(:mod:`quill.core.abbreviations`) -- same file, same per-entry settings, no
sync and no second copy. What differs is only the input: the editor knows the
document text and a caret offset, while system-wide expansion knows a buffer of
recent keys and must say how many characters to erase.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.abbreviations import (
    Abbreviation,
    AbbreviationLibrary,
    resolve_expansion,
)
from quill.core.expansion.ring_buffer import RingBuffer

#: The characters that end a word and so can fire an expansion. An entry's own
#: ``triggers`` setting then decides whether *it* accepts the one that fired.
TRIGGER_CHARS: frozenset[str] = frozenset({
    " ",
    "\t",
    "\n",
    ".",
    ",",
    ";",
    ":",
    "!",
    "?",
    ")",
    "]",
    "}",
    '"',
    "'",
})

_SPACE_TRIGGERS: frozenset[str] = frozenset({" ", "\t", "\n"})


@dataclass(slots=True)
class GlobalMatch:
    """One expansion to perform in whatever application has focus."""

    abbreviation: Abbreviation
    #: The expansion, with variables resolved and any ``${cursor}`` removed.
    text: str
    #: How many characters to erase before typing :attr:`text`: the length of
    #: the abbreviation only. The trigger character is *swallowed by the hook*
    #: rather than erased -- it has not reached the application yet when the
    #: match is found, and racing it with backspaces is exactly how an expander
    #: corrupts text. The worker types it back after the expansion.
    backspace_count: int
    #: Where the caret should end up, as an offset into :attr:`text`.
    cursor_offset: int
    has_cursor: bool
    #: Type one more space after the trigger character. Only set when the entry
    #: asked for a trailing space and the trigger was punctuation.
    trailing_space: bool
    #: The character that fired this expansion, retyped after the expansion so
    #: the user's own keystroke still lands where they put it.
    trigger_char: str = ""


def apply_typed_case(typed: str, expansion: str) -> str:
    """Carry the case the user typed over to *expansion*.

    Typing "BTW" gives "BY THE WAY" and "Btw" gives "By The Way", while the
    ordinary "btw" is left exactly as the entry defines it. Only applies to
    case-insensitive entries -- a case-sensitive entry matched one exact
    spelling, so its expansion is used verbatim.
    """
    if len(typed) > 1 and typed.isupper():
        return expansion.upper()
    if typed.istitle():
        return " ".join(word.capitalize() for word in expansion.split(" "))
    return expansion


def match_buffer(
    buffer: RingBuffer,
    library: AbbreviationLibrary,
    clipboard_text: str = "",
) -> GlobalMatch | None:
    """Return the expansion the buffer's last word just triggered, if any.

    The buffer must end with a trigger character. The buffer is not modified --
    the caller clears it when it acts on the result.
    """
    text = buffer.text()
    if len(text) < 2:
        return None
    trigger_char = text[-1]
    if trigger_char not in TRIGGER_CHARS:
        return None

    token_end = len(text) - 1
    token_start = token_end
    while token_start > 0:
        previous = text[token_start - 1]
        if previous.isspace() or previous in TRIGGER_CHARS:
            break
        token_start -= 1
    if token_start >= token_end:
        return None
    token = text[token_start:token_end]

    # Longest abbreviation wins, so "addr" cannot be shadowed by "ad".
    for entry in sorted(library.enabled_only(), key=lambda a: len(a.abbreviation), reverse=True):
        if not entry.accepts_trigger(trigger_char):
            continue
        if entry.case_sensitive:
            if token != entry.abbreviation:
                continue
        elif token.lower() != entry.abbreviation.lower():
            continue
        resolved, cursor_offset, has_cursor = resolve_expansion(entry.expansion, clipboard_text)
        if not entry.case_sensitive:
            cased = apply_typed_case(token, resolved)
            # Case folding must not move the caret marker, so only take it when
            # the length is unchanged (it always is for ASCII, and this keeps a
            # locale-specific surprise from misplacing the caret).
            if len(cased) == len(resolved):
                resolved = cased
        return GlobalMatch(
            abbreviation=entry,
            text=resolved,
            backspace_count=len(token),
            cursor_offset=cursor_offset,
            has_cursor=has_cursor,
            trailing_space=entry.trailing_space and trigger_char not in _SPACE_TRIGGERS,
            trigger_char=trigger_char,
        )
    return None
