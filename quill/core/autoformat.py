"""Pure typography autoformat helpers (SET-4).

These are wx-free transforms applied as the user types: straight quotes become
curly quotes and a double hyphen becomes an em dash. The UI layer owns the
insertion-point manipulation; these functions only decide the replacement.
"""

from __future__ import annotations

__all__ = [
    "autoformat_allows",
    "LEFT_DOUBLE",
    "RIGHT_DOUBLE",
    "LEFT_SINGLE",
    "RIGHT_SINGLE",
    "EM_DASH",
    "smart_quote_for",
    "is_dash_merge",
]

LEFT_DOUBLE = "\u201c"
RIGHT_DOUBLE = "\u201d"
LEFT_SINGLE = "\u2018"
RIGHT_SINGLE = "\u2019"
EM_DASH = "\u2014"

#: Characters before which a straight quote should open (rather than close).
_OPENING_CONTEXT = " \t\n\r([{" + LEFT_DOUBLE + LEFT_SINGLE


def smart_quote_for(preceding_char: str, typed_quote: str) -> str:
    """Return the curly replacement for a straight quote typed at a position.

    ``preceding_char`` is the character immediately before the insertion point
    (empty string at the start of the buffer). A quote opens at the start of a
    word (start of buffer, after whitespace, or after an opening bracket) and
    closes otherwise. Non-quote input is returned unchanged.
    """
    if typed_quote == '"':
        opening, closing = LEFT_DOUBLE, RIGHT_DOUBLE
    elif typed_quote == "'":
        opening, closing = LEFT_SINGLE, RIGHT_SINGLE
    else:
        return typed_quote
    if preceding_char == "" or preceding_char in _OPENING_CONTEXT:
        return opening
    return closing


def is_dash_merge(preceding_char: str) -> bool:
    """Return ``True`` when a typed hyphen should merge with the prior one."""
    return preceding_char == "-"


#: Document kinds a typed quote must stay straight in. Not a blocklist of
#: suffixes -- the kinds both editors already classify a document into.
_LITERAL_KINDS = frozenset({"plain", "code", "json", "yaml", "toml", "ini", "conf"})


def autoformat_allows(kind: str | None) -> bool:
    """Whether autocorrect may touch a document of this *kind* (bad.md T4).

    Autoformat was gated by **app** in both editors and by document kind in
    neither, so once it was switched on a typed quote curled inside a ``.json``
    and a ``--`` became an em dash inside a ``.py``. In prose those rules are
    what the feature is for; in a configuration file they are a syntax error
    somebody then has to find by reading, having never been told a substitution
    happened.

    The gate belongs on the kind because both editors already know the kind --
    it decides what Ctrl+B writes, what the status bar's Format cell says and
    whether a leading ``#`` is a heading. A setting cannot express "except in
    code", and asking somebody to remember to switch it off per file is asking
    them to do the classification the app has already done.

    ``None`` means "unknown", which is treated as prose: an untitled buffer is
    far more often a note than a config file, and the failure in that direction
    is a curly quote somebody can undo.
    """
    if kind is None:
        return True
    return kind.strip().lower() not in _LITERAL_KINDS
