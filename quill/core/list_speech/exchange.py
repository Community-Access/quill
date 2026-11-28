"""Sharing List Speech Templates as a file: what a person exports and imports.

An export holds the person's **saved templates** only. Which template each list
uses is a choice about this computer, so it is neither written nor read: after
importing, the person picks what to use in the editor.

Reading is forgiving and every problem is one plain sentence for the person:

- text that is not a template file at all says so, and changes nothing;
- a file from a newer QUILL is refused rather than half-understood;
- a file with no version (an older export) is read as version 1;
- a template for a list this QUILL does not have, or with a built-in name, is
  skipped and counted, never silently dropped;
- a template whose name is already saved is a **conflict**: it replaces the
  saved one only when the caller names it in ``replace``, so nothing is ever
  overwritten without the person being asked first.

Wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from quill.core.list_speech.catalog import get_list_type
from quill.core.list_speech.library import RESERVED_NAMES, Library, add_template, find_template
from quill.core.list_speech.template import Template, template_from_dict, template_to_dict

__all__ = [
    "FORMAT_TAG",
    "Incoming",
    "apply_import",
    "conflicts",
    "export_templates",
    "read_import",
    "template_key",
]

FORMAT_TAG = "quill-list-speech-templates"
#: The newest file version this build reads (the same as the store's schema).
CURRENT_VERSION = 1


@dataclass(frozen=True, slots=True)
class Incoming:
    """What an import file holds, ready to be offered to the person."""

    templates: tuple[Template, ...] = ()
    #: Sentences about what was adjusted or skipped while reading.
    notes: tuple[str, ...] = ()
    #: A sentence when the file could not be used at all (and nothing else is set).
    error: str = ""


def template_key(template: Template) -> tuple[str, str]:
    """A template's identity: its list type and its name, ignoring case."""
    return template.list_type, template.name.casefold()


def export_templates(library: Library) -> str:
    """The saved templates as text for a file, in a stable order."""
    ordered = sorted(library.templates, key=lambda t: (t.list_type, t.name.casefold()))
    return json.dumps(
        {
            "format": FORMAT_TAG,
            "version": CURRENT_VERSION,
            "templates": [template_to_dict(t) for t in ordered],
        },
        indent=2,
        ensure_ascii=False,
    )


def _plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many.format(n=count)


def read_import(text: str) -> Incoming:
    """The templates in *text*, or an :class:`Incoming` whose ``error`` says why not."""
    try:
        data = json.loads(text)
    except ValueError:
        return Incoming(error="That file is not a List Speech Templates file.")
    if not isinstance(data, dict) or not isinstance(data.get("templates"), list):
        return Incoming(error="That file is not a List Speech Templates file.")
    tag = data.get("format")
    if tag is not None and tag != FORMAT_TAG:
        return Incoming(error="That file is not a List Speech Templates file.")
    version = data.get("version")
    notes: list[str] = []
    if version is not None and not (
        isinstance(version, int) and not isinstance(version, bool) and version >= 1
    ):
        return Incoming(error="That file has a version this QUILL does not understand.")
    if version is not None:
        if version > CURRENT_VERSION:
            return Incoming(
                error=(
                    "That file was made by a newer QUILL, so it is not safe to read here. "
                    "Update QUILL and try again."
                )
            )
    else:
        notes.append("That file has no version, so it was read as an older export.")
    templates: list[Template] = []
    unreadable = unknown_list = reserved = repeated = 0
    seen: set[tuple[str, str]] = set()
    for raw in data["templates"]:
        template = template_from_dict(raw) if isinstance(raw, dict) else None
        if template is None:
            unreadable += 1
        elif get_list_type(template.list_type) is None:
            unknown_list += 1
        elif template.name.casefold() in RESERVED_NAMES:
            reserved += 1
        elif template_key(template) in seen:
            repeated += 1
        else:
            seen.add(template_key(template))
            templates.append(template)
    for count, one, many in (
        (
            unreadable,
            "One template had no name or list and was skipped.",
            "{n} templates had no name or list and were skipped.",
        ),
        (
            unknown_list,
            "One template is for a list this QUILL does not have and was skipped.",
            "{n} templates are for lists this QUILL does not have and were skipped.",
        ),
        (
            reserved,
            "One template used the name of a built-in choice and was skipped.",
            "{n} templates used the names of built-in choices and were skipped.",
        ),
        (
            repeated,
            "One template repeated an earlier name and was skipped.",
            "{n} templates repeated earlier names and were skipped.",
        ),
    ):
        if count:
            notes.append(_plural(count, one, many))
    if not templates:
        return Incoming(notes=tuple(notes), error="That file has no templates to import.")
    return Incoming(tuple(templates), tuple(notes))


def conflicts(library: Library, templates: Iterable[Template]) -> tuple[Template, ...]:
    """The incoming templates whose name is already saved for the same list."""
    return tuple(t for t in templates if find_template(library, t.list_type, t.name) is not None)


def apply_import(
    library: Library,
    templates: Iterable[Template],
    replace: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[Library, str]:
    """Add the templates; a name already saved is replaced only when listed in *replace*.

    Returns the new library and one sentence saying how many were added,
    replaced and left alone.
    """
    added = replaced = kept = 0
    for template in templates:
        exists = find_template(library, template.list_type, template.name) is not None
        if exists and template_key(template) not in replace:
            kept += 1
            continue
        library = add_template(library, template)
        if exists:
            replaced += 1
        else:
            added += 1
    parts = []
    if added:
        parts.append(_plural(added, "1 added", "{n} added"))
    if replaced:
        parts.append(_plural(replaced, "1 replaced", "{n} replaced"))
    if kept:
        parts.append(_plural(kept, "1 kept as it was", "{n} kept as they were"))
    if not parts:
        return library, "Nothing was imported."
    if not added and not replaced:
        return library, "Nothing was imported. " + parts[0][0].upper() + parts[0][1:] + "."
    return library, "Imported: " + ", ".join(parts) + "."
