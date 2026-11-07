"""A snippet's blanks, asked in the family's one fill-in form.

A QUILL snippet that says ``${input:topic}`` or ``${choice:NVDA|JAWS|Narrator}``
has blanks to fill before it goes in. QUILL used to ask them one dialog at a
time. They are asked now in :class:`quill.ui.fill_in_dialog.FillInDialog`, the
form abbreviation fields already use in QUILL, QUILL Lite and Quill Inkwell:
one labelled box or list per blank, in the order the snippet uses them, Tab
between them and Enter to insert. One form, so a blank behaves the same
whichever feature it is in, and no second form to drift from the first.

This module only translates a snippet's blanks into the form's questions and
the form's answers back into the snippet's tokens.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.expansion.fields import FieldSpec
from quill.core.snippets import Placeholder

__all__ = ["ask_snippet_values", "field_spec"]


def field_spec(placeholder: Placeholder) -> FieldSpec:
    """The form's question for one blank.

    A choice's label is its options, "NVDA, JAWS or Narrator": a snippet's
    choice has no name of its own, and two choices with different options must
    stay two questions.
    """
    if placeholder.kind == "choice":
        options = tuple(placeholder.options)
        if len(options) > 1:
            label = ", ".join(options[:-1]) + " or " + options[-1]
        else:
            label = options[0] if options else "Choice"
        return FieldSpec(label=label, default=options[0] if options else "", choices=options)
    name = placeholder.name.strip() or "Value"
    return FieldSpec(label=name[:1].upper() + name[1:])


def ask_snippet_values(
    parent: Any,
    title: str,
    placeholders: list[Placeholder],
    show_modal: Callable[[Any, str], int],
) -> dict[str, str] | None:
    """Ask every blank at once. ``{token: answer}``, or ``None`` when cancelled."""
    if not placeholders:
        return {}
    import wx

    from quill.ui.fill_in_dialog import FillInDialog

    specs = [field_spec(p) for p in placeholders]
    dialog = FillInDialog(parent, specs, title=title)
    try:
        if show_modal(dialog.dialog, title) != wx.ID_OK:
            return None
        answers = dialog.values
    finally:
        dialog.close()
    return {p.token: answers.get(spec.key, "") for p, spec in zip(placeholders, specs, strict=True)}
