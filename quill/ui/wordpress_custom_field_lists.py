"""Custom fields that are lists or groups, edited one at a time (WP-R-033).

A mixin of :class:`~quill.ui.wordpress_api_writing_commands.WordPressApiWritingCommands`.
After the plain fields of Custom Fields, a site's lists (speakers, a
schedule's rows, picture ids) and groups (a venue's address) open in a list
window of their own:

- **Lists and Groups** names each one with what it holds; Enter edits it.
- **A group** is one form of labelled fields. Keys its schema does not name
  are kept as they were.
- **A list** is a list window with Add, Edit, Remove, Move Up and Move Down,
  and Keep Changes. Every item of a list of groups is a form; every other
  item is one text box, or a choice when the site lists the values.

Nothing goes to the site from here: a changed list is kept with the working
copy, like every other custom field, and sent with the next Save Draft to
Site or Publish. All of the logic is in
:mod:`quill.core.wordpress.custom_field_shapes`; this file only asks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import custom_field_shapes as shapes
from quill.core.wordpress import custom_fields as cf
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.core.wordpress import local as lc
    from quill.core.wordpress import sites as st


def _name(sf: shapes.StructuredField) -> str:
    return sf.label.replace("&", "").rstrip(":")


class WordPressCustomFieldLists:
    # Provided by WordPressCommands.
    host: Any
    local: Any

    def edit_lists_and_groups(
        self, form: cf.CustomFields, copy: lc.WorkingCopy, profile: st.SiteProfile
    ) -> None:
        """The Lists and Groups window, when the site registers any."""
        if not form.structured:
            return

        def rows() -> list[str]:
            return [shapes.describe(sf) for sf in form.structured]

        def edit(index: int | None) -> object:
            if index is None:
                return None
            self._edit_structured(form, form.structured[index], copy, profile)
            return dlg.Rows(rows(), index)

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Lists and Groups",
            purpose=(
                f"The custom fields on {profile.name} that hold a list or a group of values, "
                "such as speakers or an address. Enter edits the selected one. Changes go to "
                "the site with your next Save Draft to Site or Publish."
            ),
            list_label="&Fields:",
            list_help="Each row names a list or group and says what it holds now.",
            rows=rows(),
            on_enter=edit,
            actions=[dlg.Action("&Edit...", "Edit the selected list or group.", edit)],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #

    def _edit_structured(
        self,
        form: cf.CustomFields,
        sf: shapes.StructuredField,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
    ) -> None:
        if sf.shape == "group":
            value = self._ask_group(sf.schema, sf.value, _name(sf), sf.help)
            if value is not None:
                self._keep_structured(form, sf, value, copy, profile)
            return
        self._edit_list(form, sf, copy, profile)

    def _edit_list(
        self,
        form: cf.CustomFields,
        sf: shapes.StructuredField,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
    ) -> None:
        items_schema: dict[str, Any] = dict(sf.schema.get("items") or {})
        working: list[Any] = list(sf.value) if isinstance(sf.value, (list, tuple)) else []
        name = _name(sf)

        def rows() -> list[str]:
            return [shapes.item_sentence(items_schema, item) for item in working]

        def add(index: int | None) -> object:
            value = self._ask_item(items_schema, shapes.blank(items_schema), f"Add to {name}")
            if value is None:
                return None
            working[:], where = shapes.add_item(working, value, index)
            return dlg.Rows(rows(), where)

        def edit(index: int | None) -> object:
            if index is None:
                return None
            value = self._ask_item(items_schema, working[index], f"Edit in {name}")
            if value is None:
                return None
            working[index] = value
            return dlg.Rows(rows(), index)

        def remove(index: int | None) -> object:
            if index is None:
                return None
            working[:], where = shapes.remove_item(working, index)
            self.host.announce("Removed. Keep Changes keeps the list without it.")
            return dlg.Rows(rows(), where)

        def mover(step: int) -> Any:
            def move(index: int | None) -> object:
                if index is None:
                    return None
                moved, where = shapes.move_item(working, index, step)
                if where == index:
                    self.host.announce("Already at the top." if step < 0 else "Already last.")
                    return None
                working[:] = moved
                return dlg.Rows(rows(), where)

            return move

        def keep(_index: int | None) -> object:
            self._keep_structured(form, sf, list(working), copy, profile)
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=name,
            purpose=(
                f"{sf.help} Add, change, remove and reorder the items, then Keep Changes. "
                "Close leaves the list as it was."
            ),
            list_label="&Items:",
            list_help="The list's items in order. Enter edits the selected one.",
            rows=rows(),
            on_enter=edit,
            actions=[
                dlg.Action("&Add...", "Add an item after the selected one.", add, needs_row=False),
                dlg.Action("&Edit...", "Change the selected item.", edit),
                dlg.Action("Re&move", "Take the selected item out of the list.", remove),
                dlg.Action("Move &Up", "Move the selected item one place earlier.", mover(-1)),
                dlg.Action("Move &Down", "Move the selected item one place later.", mover(1)),
                dlg.Action(
                    "&Keep Changes",
                    "Keep the list as it is now with your copy, and close.",
                    keep,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()

    def _ask_group(self, schema: dict[str, Any], value: Any, title: str, purpose: str) -> Any:
        fields = shapes.group_fields(schema, value)
        if not fields:
            self.host.announce(f"{title} has nothing QUILL can edit.")
            return None
        answers = bdlg.ask_fields(
            self.host.parent, self.host.show_modal, title=title, purpose=purpose, fields=fields
        )
        if answers is None:
            return None
        try:
            return shapes.apply_group(schema, value, answers, title)
        except cf.FieldValueError as exc:
            self.host.announce(f"{exc.field_label} needs a number. Nothing was changed.")
            return None

    def _ask_item(self, schema: dict[str, Any], current: Any, title: str) -> Any:
        """One item: a form for a group, a choice for listed values, else a text box."""
        if shapes.shape_of(schema) == "group":
            return self._ask_group(schema, current, title, "One item of the list.")
        enum = schema.get("enum")
        kind = shapes.json_type(schema)
        if kind == "boolean" or (isinstance(enum, list) and enum):
            values: list[Any] = list(enum) if isinstance(enum, list) and enum else [True, False]
            labels = [shapes.item_sentence(schema, v) for v in values]
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=title,
                prompt="&Value:",
                rows=labels,
                initial=values.index(current) if current in values else 0,
                help_text="Choose the item's value from the ones the site allows.",
            )
            return None if picked is None else values[picked]
        text = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title=title,
            prompt="&Value:",
            value="" if current is None else str(current),
            help_text=(
                "The item's value. It must be a number."
                if kind in ("integer", "number")
                else "The item's value, as it should read on the site."
            ),
        )
        if text is None:
            return None
        try:
            return shapes.coerce(schema, text, title)
        except cf.FieldValueError:
            self.host.announce("That needs a number. Nothing was added or changed.")
            return None

    def _keep_structured(
        self,
        form: cf.CustomFields,
        sf: shapes.StructuredField,
        value: Any,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
    ) -> None:
        try:
            changed, typed = cf.structured_change(form, sf.key, value)
        except cf.FieldValueError as exc:
            self.host.announce(f"{exc.field_label} needs a number. Nothing was kept.")
            return
        meta = dict(copy.properties.get("meta") or {})
        if changed:
            meta[sf.key] = typed
        else:
            meta.pop(sf.key, None)
        copy.properties["meta"] = meta
        self.local.save(copy)
        sf.value = typed
        name = _name(sf)
        if changed:
            self.host.announce(
                f"{name} kept with your copy. It goes to {profile.name} when you next send."
            )
        else:
            self.host.announce(f"{name} is the same as on {profile.name}.")
