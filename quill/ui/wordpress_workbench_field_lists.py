"""Lists and groups on the Workbench's Properties, edited in their own windows (WP-R-033).

A mixin of :class:`~quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.
A custom field that holds a list of groups (a schedule's rows) or a group (a
venue's address) shows on Properties as its JSON, so nothing is hidden and
anything can be pasted. Beside it, **Edit List...** or **Edit Group...** opens
the same list and group windows the editor's Custom Fields uses
(:class:`quill.ui.wordpress_custom_field_lists.StructuredEditor`): a list with
Add, Edit, Remove, Move Up and Move Down, a group as a form of labelled fields.

What the windows keep goes back into the box, so the sheet's OK or Apply sends
it, checked against the schema first and verified after, like any other field.
Keys the schema does not name are kept. Only a list or group whose every value
has a control gets the button (:func:`~quill.core.wordpress.field_plugins_more.structured_fields`);
a deeper one keeps its JSON box, and one QUILL cannot check stays read only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from quill.core.wordpress import custom_field_shapes as shapes
from quill.core.wordpress.field_plugins_more import box_text, box_value, structured_fields
from quill.core.workbench.properties import SheetSpec

__all__ = ["WorkbenchFieldLists"]


class WorkbenchFieldLists:
    """Edit List... and Edit Group... beside a structured field on Properties."""

    parent: Any
    say: Callable[[str], None]
    show_modal: Callable[[Any, str], int]

    def structured_buttons(
        self, sheet: SheetSpec, lookup: Mapping[str, Any]
    ) -> dict[str, list[Any]]:
        """The buttons for each list or group field of *sheet*, by field key."""
        from quill.ui.workbench_sheet_editor import FieldButton

        buttons: dict[str, list[Any]] = {}
        for key, schema in structured_fields(sheet, lookup).items():
            label = sheet.field(key).label
            is_list = shapes.shape_of(schema) == "list"
            buttons[key] = [
                FieldButton(
                    "Edit List..." if is_list else "Edit Group...",
                    (
                        f"Edit {label} one item at a time: add, change, remove and reorder."
                        if is_list
                        else f"Edit {label} as a form, one labelled box for each part."
                    )
                    + " OK or Apply sends it.",
                    lambda set_value, now, k=label, s=schema: self.edit_structured_box(
                        k, s, set_value, now
                    ),
                )
            ]
        return buttons

    def edit_structured_box(
        self,
        label: str,
        schema: dict[str, Any],
        set_value: Callable[[str], None],
        now: str,
    ) -> None:
        """Open *label*'s list or group window on what the box holds, and put the result back."""
        from quill.ui.wordpress_custom_field_lists import StructuredEditor

        value = box_value(now, schema)
        if value is None:
            word = "list" if shapes.shape_of(schema) == "list" else "object"
            self.say(
                f"{label} does not hold a valid JSON {word}, so it cannot be opened as a "
                "form. Correct the text, or press Cancel to leave it."
            )
            return
        editor = StructuredEditor(self.parent, self.show_modal, self.say)
        purpose = f"{label}, a custom field on this item."
        changed = editor.edit(schema, value, label, purpose)
        if changed is None:
            return
        set_value(box_text(changed))
        self.say(f"{label} changed. OK or Apply sends it to the site.")
