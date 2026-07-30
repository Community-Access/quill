"""Parse Unicode code points for the Insert Special Character command (EDS-1).

Insert Special Character accepts a code point as hexadecimal, or
as decimal when prefixed with ``d``. This module is UI-framework agnostic so the
parsing can be unit-tested without ``wx``.

Migration note: the same logic is now vendored into
``quill/quillins_bundled/insert-character/codepoints.py`` so the feature can
run as a sandboxed Quillin (``ext.insert.character``) alongside the first-party
``power.insert_special_character`` command. When the first-party command is
retired (migration plan Wave N), this module can be removed.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

__all__ = ["CodepointError", "parse_codepoint"]

_MAX_CODEPOINT = 0x10FFFF


class CodepointError(CodedError):
    """Raised when a code point string cannot be turned into a character."""

    code = "QUILL-UNICODE-CODEPOINT-INVALID"


def parse_codepoint(value: str) -> str:
    """Return the character for ``value``.

    ``value`` is interpreted as hexadecimal by default (``"41"`` -> ``"A"``), as
    decimal when prefixed with a lowercase ``d`` (``"d65"`` -> ``"A"``), or as a
    ``U+`` escape (``"U+1F600"``). Surrogate and out-of-range values are rejected.
    A leading uppercase ``D`` is treated as a hexadecimal digit, not a prefix.
    """
    raw = value.strip()
    if not raw:
        raise CodepointError("Enter a Unicode code point")
    try:
        if raw[0] == "d" and raw[1:].isdigit():
            number = int(raw[1:], 10)
        elif raw[:2].lower() == "u+":
            number = int(raw[2:], 16)
        else:
            number = int(raw, 16)
    except ValueError as exc:
        raise CodepointError(f"Invalid code point: {value}") from exc
    if number < 0 or number > _MAX_CODEPOINT:
        raise CodepointError(f"Code point out of range: {value}")
    if 0xD800 <= number <= 0xDFFF:
        raise CodepointError(f"Code point is an unpaired surrogate: {value}")
    return chr(number)
