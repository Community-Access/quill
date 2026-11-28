"""The state behind the List Speech Templates editor, without any widgets.

The dialog is a thin skin over this: every button calls one function here,
gets back the new :class:`EditorState` and **one clear sentence** to announce.
That keeps the rules (what a move does at the top of the list, what a deleted
template falls back to) testable with no window.

``state.draft`` is the template being edited. ``state.source`` is where it came
from: ``""`` (the usual wording; the draft is only a starting point), a
``builtin:`` preset, or a saved ``user:`` template. Presets cannot be edited in
place: changing one makes the draft a custom template waiting for a name.

Wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from quill.core.list_speech import library as lib
from quill.core.list_speech.catalog import ListType, get_list_type
from quill.core.list_speech.render import render_row
from quill.core.list_speech.template import (
    MAX_FALLBACK,
    MAX_SEPARATOR,
    Template,
    from_preset,
    move_field,
    unavailable_fields,
)

__all__ = [
    "EditorState",
    "add_field",
    "assign_current",
    "choose_source",
    "delete_saved",
    "move",
    "preview",
    "remove_field",
    "rename_saved",
    "save_draft",
    "set_fallback",
    "set_labels",
    "set_omit_empty",
    "set_separator",
    "source_choices",
    "start",
    "unavailable_note",
]

DRAFT_NAME = "Custom"


@dataclass(frozen=True, slots=True)
class EditorState:
    library: lib.Library
    list_type: str
    source: str
    draft: Template
    dirty: bool = False

    @property
    def kind(self) -> ListType:
        found = get_list_type(self.list_type)
        if found is None:
            raise KeyError(self.list_type)
        return found


def _draft_for(library: lib.Library, kind: ListType, ref: str) -> Template:
    if ref.startswith(lib.BUILTIN_PREFIX):
        preset = kind.preset(ref.removeprefix(lib.BUILTIN_PREFIX))
        if preset is not None:
            return from_preset(kind, preset)
    if ref.startswith(lib.USER_PREFIX):
        saved = lib.find_template(library, kind.id, ref.removeprefix(lib.USER_PREFIX))
        if saved is not None:
            return saved
    balanced = kind.presets[1]
    return Template(kind.id, DRAFT_NAME, balanced.fields, ", ", balanced.labels)


def start(library: lib.Library, list_type: str) -> EditorState:
    """Open on the template this list uses now (or the usual wording)."""
    kind = get_list_type(list_type)
    if kind is None:
        raise KeyError(list_type)
    ref = library.assignments.get(list_type, lib.DEFAULT_REF)
    if lib.resolve(library, list_type).template is None:
        ref = lib.DEFAULT_REF
    return EditorState(library, list_type, ref, _draft_for(library, kind, ref))


def source_choices(state: EditorState) -> list[tuple[str, str]]:
    """(reference, title) for the chooser: usual wording, presets, then saved templates."""
    choices = [(lib.DEFAULT_REF, "Usual wording")]
    choices += [(lib.BUILTIN_PREFIX + p.id, p.title) for p in state.kind.presets]
    choices += [
        (lib.USER_PREFIX + t.name, t.name)
        for t in state.library.templates
        if t.list_type == state.list_type
    ]
    return choices


def choose_source(state: EditorState, ref: str) -> tuple[EditorState, str]:
    draft = _draft_for(state.library, state.kind, ref)
    known = {r for r, _t in source_choices(state)}
    chosen = ref if ref in known else lib.DEFAULT_REF
    title = dict(source_choices(state))[chosen]
    return replace(state, source=chosen, draft=draft, dirty=False), f"{title} chosen."


def _edited(state: EditorState, draft: Template) -> EditorState:
    """A preset or the usual wording becomes a custom draft the moment it is changed."""
    source = state.source if state.source.startswith(lib.USER_PREFIX) else lib.DEFAULT_REF
    name = draft.name if source.startswith(lib.USER_PREFIX) else DRAFT_NAME
    return replace(state, source=source, draft=replace(draft, name=name), dirty=True)


def _title(state: EditorState, field_id: str) -> str:
    definition = state.kind.field(field_id)
    return definition.title if definition else field_id


def add_field(state: EditorState, field_id: str) -> tuple[EditorState, str]:
    if state.kind.field(field_id) is None:
        return state, "That field is not offered for this list."
    if field_id in state.draft.fields:
        return state, f"{_title(state, field_id)} is already in the template."
    fields = (*state.draft.fields, field_id)
    new = _edited(state, replace(state.draft, fields=fields))
    return new, f"Added {_title(state, field_id)}, position {len(fields)} of {len(fields)}."


def remove_field(state: EditorState, index: int) -> tuple[EditorState, str]:
    fields = state.draft.fields
    if not 0 <= index < len(fields):
        return state, "Nothing is selected to remove."
    gone = _title(state, fields[index])
    rest = (*fields[:index], *fields[index + 1 :])
    return _edited(state, replace(state.draft, fields=rest)), f"Removed {gone}. {len(rest)} left."


def move(state: EditorState, index: int, delta: int) -> tuple[EditorState, int, str]:
    """Move a field; returns the state, the field's new index and the announcement."""
    fields = state.draft.fields
    if not 0 <= index < len(fields):
        return state, index, "Nothing is selected to move."
    name = _title(state, fields[index])
    moved, new_index = move_field(fields, index, delta)
    if new_index == index:
        edge = "first" if delta < 0 else "last"
        return state, index, f"{name} is already {edge}."
    new = _edited(state, replace(state.draft, fields=moved))
    return new, new_index, f"{name} moved to position {new_index + 1} of {len(fields)}."


def set_separator(state: EditorState, text: str) -> tuple[EditorState, str]:
    clipped = text[:MAX_SEPARATOR]
    return _edited(state, replace(state.draft, separator=clipped)), "Separator changed."


def set_labels(state: EditorState, on: bool) -> tuple[EditorState, str]:
    new = _edited(state, replace(state.draft, labels=on))
    return new, "Field labels on." if on else "Field labels off."


def set_omit_empty(state: EditorState, on: bool) -> tuple[EditorState, str]:
    new = _edited(state, replace(state.draft, omit_empty=on))
    return new, "Empty fields are left out." if on else "Empty fields use the fallback text."


def set_fallback(state: EditorState, text: str) -> tuple[EditorState, str]:
    return _edited(
        state, replace(state.draft, fallback=text[:MAX_FALLBACK])
    ), "Fallback text changed."


def unavailable_note(state: EditorState) -> str:
    """One sentence naming fields the list no longer offers, or empty."""
    gone = unavailable_fields(state.draft, state.kind)
    if not gone:
        return ""
    names = ", ".join(gone)
    noun = "field is" if len(gone) == 1 else "fields are"
    return f"The {noun} no longer offered for this list and will not be spoken: {names}."


def preview(state: EditorState) -> str:
    """The sample row as the draft speaks it, or what to do when it says nothing."""
    rendered = render_row(state.draft, state.kind, state.kind.sample)
    return rendered.text or "Nothing would be spoken. Add a field."


def save_draft(state: EditorState, name: str) -> tuple[EditorState, str]:
    """Save the draft under *name* and use it for this list."""
    try:
        library = lib.add_template(state.library, replace(state.draft, name=name))
    except ValueError as error:
        return state, str(error)
    clean = " ".join(name.split())
    library = lib.assign(library, state.list_type, lib.USER_PREFIX + clean)
    saved = lib.find_template(library, state.list_type, clean)
    new = replace(
        state,
        library=library,
        source=lib.USER_PREFIX + clean,
        draft=saved or state.draft,
        dirty=False,
    )
    return new, f"Saved {clean} and now using it for {state.kind.title}."


def rename_saved(state: EditorState, new_name: str) -> tuple[EditorState, str]:
    if not state.source.startswith(lib.USER_PREFIX):
        return state, "Only a saved template can be renamed."
    old = state.source.removeprefix(lib.USER_PREFIX)
    try:
        library = lib.rename_template(state.library, state.list_type, old, new_name)
    except ValueError as error:
        return state, str(error)
    clean = " ".join(new_name.split())
    new = replace(state, library=library, source=lib.USER_PREFIX + clean)
    new = replace(new, draft=replace(state.draft, name=clean))
    return new, f"Renamed to {clean}."


def delete_saved(state: EditorState) -> tuple[EditorState, str]:
    if not state.source.startswith(lib.USER_PREFIX):
        return state, "Only a saved template can be deleted."
    name = state.source.removeprefix(lib.USER_PREFIX)
    library = lib.delete_template(state.library, state.list_type, name)
    new = start(library, state.list_type)
    return new, f"Deleted {name}. {state.kind.title} use the usual wording."


def assign_current(state: EditorState, similar: bool = False) -> tuple[EditorState, str]:
    """Use the chosen source for this list (and, when *similar*, for lists that read alike)."""
    ref = state.source
    if state.dirty and not ref.startswith(lib.USER_PREFIX):
        return state, "Save the template first, then use it."
    if similar:
        library, skipped = lib.assign_family(state.library, state.list_type, ref)
        extra = f" {', '.join(skipped)} kept their own choice." if skipped else ""
        message = f"Now used for {state.kind.title} and similar lists.{extra}"
    else:
        library = lib.assign(state.library, state.list_type, ref)
        message = (
            f"{state.kind.title} use the usual wording."
            if ref == lib.DEFAULT_REF
            else f"Now used for {state.kind.title}."
        )
    return replace(state, library=library), message
