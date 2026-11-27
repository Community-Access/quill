"""A person's saved templates and which one each list uses.

:class:`Library` is immutable; every change returns a new one, so the editor
can cancel by simply not saving. A list's *assignment* is a short reference:

- ``""``            the app's existing wording (the default; nothing changes);
- ``"builtin:brief"`` (or ``balanced``, ``detailed``);
- ``"user:Name"``   a template this person saved for that list type.

Wx-free and strict-typed. Reading and writing the file is in
:mod:`quill.core.list_speech.store`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from quill.core.list_speech.catalog import get_list_type
from quill.core.list_speech.template import MAX_NAME, Template, from_preset, unavailable_fields

__all__ = [
    "BUILTIN_PREFIX",
    "DEFAULT_REF",
    "RESERVED_NAMES",
    "USER_PREFIX",
    "Library",
    "Resolved",
    "add_template",
    "assign",
    "assign_family",
    "delete_template",
    "find_template",
    "rename_template",
    "resolve",
]

BUILTIN_PREFIX = "builtin:"
USER_PREFIX = "user:"
DEFAULT_REF = ""

#: Names a saved template may not take: the built-ins and the unchanged wording.
RESERVED_NAMES: frozenset[str] = frozenset({"brief", "balanced", "detailed", "default"})


@dataclass(frozen=True, slots=True)
class Library:
    templates: tuple[Template, ...] = ()
    assignments: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Resolved:
    """The template a list should use, or None to use the existing wording."""

    template: Template | None
    #: A sentence for the person when their choice could not be honoured.
    note: str = ""


def find_template(library: Library, list_type: str, name: str) -> Template | None:
    wanted = name.strip().casefold()
    return next(
        (t for t in library.templates if t.list_type == list_type and t.name.casefold() == wanted),
        None,
    )


def _check_name(name: str) -> str:
    clean = " ".join(name.split())[:MAX_NAME]
    if not clean:
        raise ValueError("Give the template a name.")
    if clean.casefold() in RESERVED_NAMES:
        raise ValueError(f"{clean} is the name of a built-in choice. Pick another name.")
    return clean


def add_template(library: Library, template: Template) -> Library:
    """Save *template*, replacing a saved one of the same name for the same list type."""
    named = replace(template, name=_check_name(template.name))
    kept = tuple(
        t
        for t in library.templates
        if not (t.list_type == named.list_type and t.name.casefold() == named.name.casefold())
    )
    return replace(library, templates=(*kept, named))


def delete_template(library: Library, list_type: str, name: str) -> Library:
    """Remove a saved template; any list using it goes back to the existing wording."""
    target = find_template(library, list_type, name)
    if target is None:
        return library
    ref = USER_PREFIX + target.name
    assignments = {
        k: v for k, v in library.assignments.items() if not (k == list_type and v == ref)
    }
    kept = tuple(t for t in library.templates if t is not target)
    return replace(library, templates=kept, assignments=assignments)


def rename_template(library: Library, list_type: str, old: str, new: str) -> Library:
    """Rename a saved template, keeping the list that uses it pointed at it."""
    target = find_template(library, list_type, old)
    if target is None:
        raise ValueError("That template is not saved.")
    clean = _check_name(new)
    clash = find_template(library, list_type, clean)
    if clash is not None and clash is not target:
        raise ValueError(f"A template named {clean} is already saved for this list.")
    renamed = replace(target, name=clean)
    kept = tuple(renamed if t is target else t for t in library.templates)
    assignments = dict(library.assignments)
    if assignments.get(list_type) == USER_PREFIX + target.name:
        assignments[list_type] = USER_PREFIX + clean
    return replace(library, templates=kept, assignments=assignments)


def assign(library: Library, list_type: str, ref: str) -> Library:
    """Make *list_type* use *ref*; the empty reference restores the existing wording."""
    assignments = {k: v for k, v in library.assignments.items() if k != list_type}
    if ref != DEFAULT_REF:
        assignments[list_type] = ref
    return replace(library, assignments=assignments)


def assign_family(library: Library, list_type: str, ref: str) -> tuple[Library, tuple[str, ...]]:
    """Use *ref* for every list that reads like *list_type*.

    Returns the new library and the titles of similar lists it could not serve
    because the template names a field they do not have; those keep their own
    choice.
    """
    source = get_list_type(list_type)
    if source is None:
        return library, ()
    template = _template_for(library, list_type, ref)
    result = assign(library, list_type, ref)
    skipped: list[str] = []
    from quill.core.list_speech.catalog import LIST_TYPES

    for other in LIST_TYPES:
        if other.id == list_type or other.family != source.family:
            continue
        if template is not None and unavailable_fields(template, other):
            skipped.append(other.title)
            continue
        if ref.startswith(USER_PREFIX) and template is not None:
            result = add_template(result, replace(template, list_type=other.id))
        result = assign(result, other.id, ref)
    return result, tuple(skipped)


def _template_for(library: Library, list_type: str, ref: str) -> Template | None:
    kind = get_list_type(list_type)
    if kind is None:
        return None
    if ref.startswith(BUILTIN_PREFIX):
        preset = kind.preset(ref.removeprefix(BUILTIN_PREFIX))
        return from_preset(kind, preset) if preset is not None else None
    if ref.startswith(USER_PREFIX):
        return find_template(library, list_type, ref.removeprefix(USER_PREFIX))
    return None


def resolve(library: Library, list_type: str) -> Resolved:
    """The template *list_type* should use, with a sentence when a choice was lost."""
    ref = library.assignments.get(list_type, DEFAULT_REF)
    if ref == DEFAULT_REF:
        return Resolved(None)
    template = _template_for(library, list_type, ref)
    if template is None:
        return Resolved(
            None, "The saved speech template for this list is gone, so the usual wording is used."
        )
    return Resolved(template)
