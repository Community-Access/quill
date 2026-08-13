"""Expansions that ask you something before they finish.

A signature or an address is the same every time, and a plain expansion is
perfect for it. A letter opening, a bug report, a booking confirmation is *not*:
it is the same except for a name, a date, a reference number. Without a way to
ask, those become "expand, then arrow back through the text hunting for the bits
to change", which is exactly the fiddly work an expander is supposed to remove --
and it is worse for someone reviewing by ear.

A field is written ``${field:Label}``, or ``${field:Label=default}`` to offer a
starting value. The same label used twice is asked once and filled everywhere,
so a name typed in the greeting also lands in the sign-off.

Pure and wx-free: this module finds the fields and fills them in. Asking is the
UI's job (:mod:`quill.ui.fill_in_dialog`), so both QUILL's editor and Quill
Inkwell ask the same way from the same definition.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: ``${field:Label}`` or ``${field:Label=default}``. The label runs to the first
#: ``=`` or the closing brace; neither may contain a brace, so an unclosed token
#: is left alone as literal text rather than swallowing the rest of the
#: expansion.
_FIELD_RE = re.compile(r"\$\{field:([^}=]+)(?:=([^}]*))?\}")


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One thing to ask for."""

    label: str
    default: str = ""

    @property
    def key(self) -> str:
        """What repeated uses of this field are matched on.

        Case- and space-insensitive, so ``${field:First name}`` and
        ``${field:first name}`` are one question, not two -- nobody types a
        template that carefully, and being asked the same thing twice is the
        kind of small insult that makes a feature feel unfinished.
        """
        return " ".join(self.label.split()).casefold()


def has_fields(expansion: str) -> bool:
    """Whether *expansion* asks for anything."""
    return _FIELD_RE.search(expansion) is not None


def parse_fields(expansion: str) -> list[FieldSpec]:
    """Every distinct field in *expansion*, in the order they are first asked.

    Repeats collapse onto the first occurrence, and the first non-empty default
    wins -- so a template can give the default once and reuse the field bare.
    """
    found: list[FieldSpec] = []
    seen: dict[str, int] = {}
    for match in _FIELD_RE.finditer(expansion):
        spec = FieldSpec(label=match.group(1).strip(), default=(match.group(2) or "").strip())
        if not spec.label:
            continue
        index = seen.get(spec.key)
        if index is None:
            seen[spec.key] = len(found)
            found.append(spec)
        elif spec.default and not found[index].default:
            found[index] = FieldSpec(label=found[index].label, default=spec.default)
    return found


def fill_fields(expansion: str, values: dict[str, str]) -> str:
    """Replace every field in *expansion* with its value from *values*.

    *values* is keyed by :attr:`FieldSpec.key`. A field with no value falls back
    to its default, and then to the empty string: a half-answered form should
    leave a gap, never the literal ``${field:...}`` text, which would be both
    ugly and confusing to hear read back.
    """

    def _replace(match: re.Match[str]) -> str:
        spec = FieldSpec(label=match.group(1).strip(), default=(match.group(2) or "").strip())
        value = values.get(spec.key)
        if value is None or value == "":
            return spec.default
        return value

    return _FIELD_RE.sub(_replace, expansion)


def default_values(specs: list[FieldSpec]) -> dict[str, str]:
    """The starting answers for a form built from *specs*."""
    return {spec.key: spec.default for spec in specs}
