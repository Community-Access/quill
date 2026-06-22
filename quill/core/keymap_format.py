"""User-facing display rewriter for stored key bindings.

The QUILL Key is the editor's signature chord prefix. Its saved
grammar (the ``"Ctrl+Shift+Grave, <second-key>"`` string stored in
``DEFAULT_KEYMAP`` and on disk in ``keymap.json``) is the binding
the dispatch layer parses. The user-visible display layer
(menus, About > Keyboard Reference, cheat sheet, status bar) shows
the chord in a friendlier branded form: ``"QUILL Key + S"`` rather
than ``"Ctrl+Shift+Grave, S"``.

This module owns that one rewrite. It accepts a stored binding and
returns the label that should appear to the user. The dispatch
grammar is never altered; only the label moves.

The prefix string is itself per-user (the ``quill_key_binding``
setting, default ``"Ctrl+Shift+Grave"``). When a user rebinds the
prefix, callers pass their active ``settings.quill_key_binding``
into :func:`format_binding_for_display` so the rewrite follows the
configured prefix. Bindings that do not match the prefix grammar
are returned unchanged, so the helper is safe to call on every
binding in the keymap.
"""

from __future__ import annotations

from quill.branding import QUILL_KEY_LABEL

__all__ = [
    "format_binding_for_display",
    "format_quill_key_chord",
]

#: The default QUILL Key prefix. Used when callers do not pass a
#: custom prefix (i.e. when ``settings.quill_key_binding`` has not
#: been rebound). Mirrors ``Settings.quill_key_binding`` default.
_DEFAULT_PREFIX = "Ctrl+Shift+Grave"


def format_binding_for_display(
    binding: str | None,
    *,
    prefix: str | None = None,
) -> str:
    """Rewrite a stored binding for human display.

    If ``binding`` starts with ``<prefix>, `` (the QUILL-key chord
    grammar: prefix, comma, single space, then the second-key), the
    prefix portion is replaced with ``"QUILL Key + "`` and the
    second-key is preserved. Other bindings — including the bare
    prefix alone, non-chord bindings, and empty strings — are
    returned unchanged. The dispatch grammar is never altered; only
    the user-visible label moves.

    Args:
        binding: The stored binding string, or ``None`` for unbound.
        prefix: The active QUILL Key prefix. Defaults to
            ``"Ctrl+Shift+Grave"``; pass ``settings.quill_key_binding``
            to follow a user rebind.

    Returns:
        The display label. Empty string for empty or ``None``
        input. ``"QUILL Key"`` for the bare prefix alone.
    """
    if not binding:
        return binding or ""
    text = str(binding).strip()
    if not text:
        return ""
    p = (prefix or _DEFAULT_PREFIX).strip()
    needle = p + ", "
    if text.startswith(needle):
        return f"{QUILL_KEY_LABEL} + " + text[len(needle) :]
    if text == p:
        return QUILL_KEY_LABEL
    return text


def format_quill_key_chord(prefix: str, second_key: str) -> str:
    """Build a user-facing chord label from a prefix and second key.

    Convenience wrapper for callers that already have the two
    pieces of a chord and want the branded label without having to
    format the full binding string first. ``second_key`` is appended
    verbatim, preserving any ``Shift+`` / ``Alt+`` modifiers the
    user has bound.

    Args:
        prefix: The active QUILL Key prefix string.
        second_key: The chord's second-key portion (e.g. ``"F"``,
            ``"Shift+S"``, ``"1"``). Whitespace is trimmed.

    Returns:
        ``"QUILL Key + <second_key>"`` for a normal call, or the
        bare label when either argument is empty.
    """
    if not prefix or not second_key:
        return QUILL_KEY_LABEL
    return f"{QUILL_KEY_LABEL} + {second_key.strip()}"
