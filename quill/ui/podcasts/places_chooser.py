"""View > Places...: the chooser for the Places list (qc.md 4.3).

A reorderable list with Up, Down, Show, Hide, Rename and Reset buttons -- the
house pattern for a wx list (no checkboxes in a list control, because a
checkbox in a list is a control two readers describe two ways). Hidden
places are still listed, marked "(hidden)", so hiding is a shorter list and
never a lost feature; a place whose feature is off in Customize Features is
not here at all, which is the difference between the two.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import places as places_model

__all__ = ["PlacesChooser", "open_places_chooser"]

TITLE = "Places"


class PlacesChooser:
    """The dialog; ``show()`` returns the layout to save, or None."""

    def __init__(
        self,
        parent: Any,
        *,
        layout: places_model.PlacesLayout,
        label_for: Any,
        enabled: Any,
        announce: Any,
    ) -> None:
        import wx

        from quill.ui.accessible_names import set_accessible_name
        from quill.ui.dialog_contract import apply_modal_ids

        self._wx = wx
        self._layout = layout
        self._label_for = label_for
        self._enabled = enabled
        self._announce = announce or (lambda _m: None)
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label="&Places, in your order:"), 0, wx.LEFT | wx.TOP, 8
        )
        self._list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        set_accessible_name(self._list, "Places, in your order")
        self._list.SetHelpText(
            "Every place, in the order the main window lists them. Up and Down "
            "move the selected place; Hide takes it out of the main window's list "
            "and Show puts it back; Rename gives it your own name; Reset restores "
            "the shipped order and names. Nothing here changes what is in a place."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons: dict[str, Any] = {}
        for key, label, help_text in (
            ("up", "&Up", "Moves the selected place one row up."),
            ("down", "&Down", "Moves the selected place one row down."),
            ("show", "&Show", "Puts the selected place back in the main window's list."),
            (
                "hide",
                "&Hide",
                "Takes the selected place out of the main window's list. It is still "
                "reachable by its key and by Go To.",
            ),
            (
                "rename",
                "&Rename...",
                "Gives the selected place your own name; the shipped name is one Reset away.",
            ),
            (
                "reset",
                "Rese&t to Default",
                "Restores the shipped order, shows every place, and clears your names.",
            ),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, k=key: self._on(k))
            buttons.Add(button, 0, wx.RIGHT, 6)
            self._buttons[key] = button
        root.Add(buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        closing = wx.BoxSizer(wx.HORIZONTAL)
        closing.AddStretchSpacer(1)
        ok = wx.Button(self.dialog, wx.ID_OK, label="Save")
        ok.SetHelpText("Keeps this order and these names in the main window.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Closes this window without saving; nothing you changed here is kept.")
        closing.Add(ok, 0, wx.RIGHT, 6)
        closing.Add(cancel, 0)
        root.Add(closing, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        self.dialog.SetSize((520, 420))
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_OK, affirmative_label="Save", cancel_id=wx.ID_CANCEL
        )
        self._names: dict[str, str] = {}
        self._fill(keep=0)

    def _rows(self) -> list[places_model.Place]:
        return places_model.visible(self._layout, enabled=self._enabled, include_hidden=True)

    def _fill(self, *, keep: int) -> None:
        rows = self._rows()
        labels = []
        for entry in rows:
            name = self._names.get(entry.id) or self._label_for(entry.id)
            labels.append(f"{name} (hidden)" if entry.id in self._layout.hidden else name)
        self._list.Set(labels)
        if rows:
            self._list.SetSelection(max(0, min(keep, len(rows) - 1)))
        self._list.SetFocus()

    def _selected(self) -> places_model.Place | None:
        rows = self._rows()
        index = self._list.GetSelection()
        return rows[index] if 0 <= index < len(rows) else None

    def _on(self, key: str) -> None:
        entry = self._selected()
        index = self._list.GetSelection()
        if key == "reset":
            self._layout = places_model.reset()
            self._names = {place.id: "" for place in places_model.PLACES}
            self._fill(keep=0)
            self._announce("Shipped order and names restored.")
            return
        if entry is None:
            return
        name = self._names.get(entry.id) or self._label_for(entry.id)
        if key in ("up", "down"):
            delta = -1 if key == "up" else 1
            order = list(self._layout.order)
            # Move within the full order (hidden rows included), since the
            # chooser lists them all.
            visible_ids = [place.id for place in self._rows()]
            position = visible_ids.index(entry.id)
            target = position + delta
            if not (0 <= target < len(visible_ids)):
                self._announce("It is already at the end.")
                return
            other = visible_ids[target]
            a, b = order.index(entry.id), order.index(other)
            order[a], order[b] = order[b], order[a]
            self._layout = places_model.PlacesLayout(tuple(order), self._layout.hidden)
            self._fill(keep=target)
            self._announce(f"{name} moved to {target + 1} of {len(visible_ids)}.")
            return
        if key == "hide":
            self._layout = places_model.hide(self._layout, entry.id)
            self._fill(keep=index)
            self._announce(f"{name} hidden.")
            return
        if key == "show":
            self._layout = places_model.show(self._layout, entry.id)
            self._fill(keep=index)
            self._announce(f"{name} shown.")
            return
        if key == "rename":
            from quill.ui.podcasts.folder_prompt import name_prompt

            new_name = name_prompt(self.dialog, "Rename Place", name, announce=self._announce)
            if new_name is None:
                return
            self._names[entry.id] = "" if new_name == entry.label else new_name
            self._fill(keep=index)
            self._announce(f"Renamed to {new_name}.")

    def show(self) -> tuple[places_model.PlacesLayout, dict[str, str]] | None:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            if answer != self._wx.ID_OK:
                return None
            return self._layout, dict(self._names)
        finally:
            self.dialog.Destroy()


def open_places_chooser(host: Any) -> None:
    library = host._podcast_library
    chooser = PlacesChooser(
        host.frame,
        layout=host._places_layout(),
        label_for=lambda place_id: places_model.label(library, place_id),
        enabled=host._cast_area_enabled,
        announce=host._announce,
    )
    result = chooser.show()
    if result is None:
        return
    layout, names = result
    for place_id, name in names.items():
        if name:
            library.settings.view_names[place_id] = name
        elif place_id in names and name == "":
            library.settings.view_names.pop(place_id, None)
    host._save_places_layout(layout)
    host._rebuild_places(keep=host._current_place)
    shown = [place.id for place in host._visible_places()]
    if host._current_place not in shown and shown:
        host.show_place(shown[0], focus=False)
    host._announce(f"Places saved: {len(shown)} shown.")
