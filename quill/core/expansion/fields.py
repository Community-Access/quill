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
from collections.abc import Iterator
from dataclasses import dataclass

#: ``${field:Label}`` or ``${field:Label=default}``. The label runs to the first
#: ``=`` or the closing brace; neither may contain a brace, so an unclosed token
#: is left alone as literal text rather than swallowing the rest of the
#: expansion.
_FIELD_RE = re.compile(r"\$\{field:([^}=]+)(?:=([^}]*))?\}")

#: ``${choice:Label|one|two|three}``. The richer half of a fill-in: a template
#: whose answer is one of a known few should offer them rather than ask for
#: typing. That matters more here than in most forms -- picking from a list is
#: one arrow key and a confirmation, and typing "Second reminder" exactly right
#: is a spelling test somebody has to pass to send an email.
#:
#: The first option is the default, so a choice behaves like a field with a
#: default when nobody changes it.
_CHOICE_RE = re.compile(r"\$\{choice:([^}|]+)\|([^}]*)\}")


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One thing to ask for."""

    label: str
    default: str = ""
    #: When non-empty, the answer is one of these rather than free text.
    choices: tuple[str, ...] = ()

    @property
    def is_choice(self) -> bool:
        return bool(self.choices)

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
    return _FIELD_RE.search(expansion) is not None or _CHOICE_RE.search(expansion) is not None


def _parse_choices(raw: str) -> tuple[str, ...]:
    """The options of a choice field, in the order written, blanks dropped."""
    options: list[str] = []
    for part in raw.split("|"):
        option = part.strip()
        if option and option not in options:
            options.append(option)
    return tuple(options)


def parse_fields(expansion: str) -> list[FieldSpec]:
    """Every distinct field in *expansion*, in the order they are first asked.

    Repeats collapse onto the first occurrence, and the first non-empty default
    wins -- so a template can give the default once and reuse the field bare.
    """
    found: list[FieldSpec] = []
    seen: dict[str, int] = {}
    for match in _iter_specs(expansion):
        spec = match
        if not spec.label:
            continue
        index = seen.get(spec.key)
        if index is None:
            seen[spec.key] = len(found)
            found.append(spec)
        elif spec.default and not found[index].default:
            found[index] = FieldSpec(
                label=found[index].label,
                default=spec.default,
                choices=found[index].choices or spec.choices,
            )
    return found


def fill_fields(expansion: str, values: dict[str, str]) -> str:
    """Replace every field in *expansion* with its value from *values*.

    *values* is keyed by :attr:`FieldSpec.key`. A field with no value falls back
    to its default, and then to the empty string: a half-answered form should
    leave a gap, never the literal ``${field:...}`` text, which would be both
    ugly and confusing to hear read back.
    """

    def _replace_field(match: re.Match[str]) -> str:
        spec = FieldSpec(label=match.group(1).strip(), default=(match.group(2) or "").strip())
        value = values.get(spec.key)
        return spec.default if value is None or value == "" else value

    def _replace_choice(match: re.Match[str]) -> str:
        options = _parse_choices(match.group(2))
        spec = FieldSpec(
            label=match.group(1).strip(),
            default=options[0] if options else "",
            choices=options,
        )
        value = values.get(spec.key)
        # An answer that is not one of the options falls back to the first,
        # rather than being typed through: a choice whose result can be anything
        # is not a choice, and a stale saved answer must not survive an edit
        # that removed the option it named.
        if value is None or value not in options:
            return spec.default
        return value

    return _CHOICE_RE.sub(_replace_choice, _FIELD_RE.sub(_replace_field, expansion))


def _iter_specs(expansion: str) -> Iterator[FieldSpec]:
    """Every field and choice, in the order they appear in the text.

    One pass in document order rather than fields-then-choices, because the
    order the form asks in should be the order the template reads in -- being
    asked for the closing before the greeting is disorienting when the form is
    being heard rather than seen.
    """
    matches = [(m.start(), "field", m) for m in _FIELD_RE.finditer(expansion)]
    matches.extend((m.start(), "choice", m) for m in _CHOICE_RE.finditer(expansion))
    for _position, kind, match in sorted(matches, key=lambda row: row[0]):
        if kind == "field":
            yield FieldSpec(label=match.group(1).strip(), default=(match.group(2) or "").strip())
        else:
            options = _parse_choices(match.group(2))
            yield FieldSpec(
                label=match.group(1).strip(),
                default=options[0] if options else "",
                choices=options,
            )


def default_values(specs: list[FieldSpec]) -> dict[str, str]:
    """The starting answers for a form built from *specs*."""
    return {spec.key: spec.default for spec in specs}
