"""Choose Columns... -- decide what a row says, and in what order. Shared.

A report list is read out one column at a time, so the column set *is* the
sentence. This dialog is therefore not a display preference dressed up as one:
it is where somebody decides what they will hear on every row of a list they
arrow through hundreds of times a day.

**Two lists, not checkboxes.** ``quill.ui.media.quick_actions_dialog`` records
why QUILL rearranges by position rather than by checkbox: a checkbox inside a
list is a state a screen reader has to be asked for, while a list position is a
place you land on and the announcement after a move tells you where you are now.
Visibility is a second dimension, so it gets a second list rather than a
checkbox column -- Hide moves a column out of the spoken row and into "Hidden",
Show puts it back where its order says it belongs. Its place in the order is
kept while it is hidden, so showing a column again does not send it to the end.

**The preview is the announcement, not a picture of it.** The line under the
lists reads exactly what one row will say, comma-separated, because that is how
a screen reader runs a report row's cells together. Somebody deciding whether to
hide Country can hear the answer before pressing OK.

**Nothing in here knows what a station or an episode is.** The catalogue, the
labels and the store all arrive as arguments, so Cast and Radio share one dialog
rather than two that drift.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.media.list_columns import ColumnDef, ColumnLayouts
from quill.ui.dialog_contract import apply_modal_ids


class ListColumnsDialog:
    """Returns the edited :class:`ColumnLayouts`, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        layouts: ColumnLayouts,
        surface_labels: Sequence[tuple[str, str]],
        announce_cb: Callable[[str], None] | None = None,
        title: str = "Choose Columns",
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._labels = list(surface_labels)
        self._title = title
        # Edit a copy: Cancel has to mean cancel, and the caller is holding the
        # live record its lists are already built from.
        self._layouts = layouts.copy()
        self._result: ColumnLayouts | None = None
        self._surface = self._labels[0][0] if self._labels else ""

        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((620, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "A row is read out one column at a time, so this is what each "
                "row will say. Put the column you listen for first, and hide "
                "anything you would rather not hear on every row."
            ),
        )
        intro.Wrap(580)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        surface_row = wx.BoxSizer(wx.HORIZONTAL)
        surface_row.Add(
            wx.StaticText(self.dialog, label="Columns &for:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._surface_choice = wx.Choice(
            self.dialog, choices=[label for _sid, label in self._labels]
        )
        self._surface_choice.SetName("Which list's columns to change")
        self._surface_choice.SetSelection(0)
        surface_row.Add(self._surface_choice, 1, wx.EXPAND)
        root.Add(surface_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        body = wx.BoxSizer(wx.HORIZONTAL)

        shown_col = wx.BoxSizer(wx.VERTICAL)
        shown_col.Add(
            wx.StaticText(self.dialog, label="&Shown, in the order they are read:"),
            0,
            wx.BOTTOM,
            4,
        )
        self._shown_list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        self._shown_list.SetName(
            "Columns this list shows, in reading order; Alt+Up and Alt+Down rearrange them"
        )
        shown_col.Add(self._shown_list, 1, wx.EXPAND)
        shown_col.Add(
            wx.StaticText(self.dialog, label="&Hidden (not read out at all):"),
            0,
            wx.TOP | wx.BOTTOM,
            4,
        )
        self._hidden_list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        self._hidden_list.SetName("Columns this list does not show")
        shown_col.Add(self._hidden_list, 1, wx.EXPAND)
        body.Add(shown_col, 1, wx.EXPAND | wx.RIGHT, 10)

        button_col = wx.BoxSizer(wx.VERTICAL)
        self._up_btn = wx.Button(self.dialog, label="Move &Up")
        self._up_btn.SetName("Move the selected column earlier in the row")
        self._down_btn = wx.Button(self.dialog, label="Move &Down")
        self._down_btn.SetName("Move the selected column later in the row")
        self._hide_btn = wx.Button(self.dialog, label="H&ide")
        self._hide_btn.SetName("Stop reading the selected column on every row")
        self._show_btn = wx.Button(self.dialog, label="Sho&w")
        self._show_btn.SetName("Read the selected hidden column again, in its own place")
        reset_btn = wx.Button(self.dialog, label="&Reset This List")
        reset_btn.SetName("Put this list's columns back the way they shipped")
        for widget in (self._up_btn, self._down_btn, self._hide_btn, self._show_btn, reset_btn):
            button_col.Add(widget, 0, wx.EXPAND | wx.BOTTOM, 6)
        body.Add(button_col, 0)
        root.Add(body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._description = wx.StaticText(self.dialog, label="")
        self._description.SetName("What the selected column holds")
        root.Add(self._description, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        preview_label = wx.StaticText(self.dialog, label="&A row will read:")
        root.Add(preview_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._preview = wx.TextCtrl(
            self.dialog, value="", style=wx.TE_READONLY | wx.TE_MULTILINE, size=(-1, 48)
        )
        self._preview.SetName("What one row of this list will say, with the columns as set above")
        root.Add(self._preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
        ok_btn.SetHelpText(
            "Keep the column changes for every list edited here. They are "
            "saved and apply to those lists from now on."
        )
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText(
            "Close without keeping anything. Every list's columns stay as "
            "they were before this dialog opened."
        )
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._surface_choice.Bind(wx.EVT_CHOICE, self._on_surface_choice)
        self._shown_list.Bind(wx.EVT_LISTBOX, lambda _e: self._describe_shown())
        self._shown_list.Bind(wx.EVT_KEY_DOWN, self._on_shown_key)
        self._hidden_list.Bind(wx.EVT_LISTBOX, lambda _e: self._describe_hidden())
        self._up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        self._hide_btn.Bind(wx.EVT_BUTTON, lambda _e: self._hide())
        self._show_btn.Bind(wx.EVT_BUTTON, lambda _e: self._show())
        reset_btn.Bind(wx.EVT_BUTTON, lambda _e: self._reset())
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        self._refill()

    def show(self) -> ColumnLayouts | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="OK",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, self._title, announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    # -- the two lists ---------------------------------------------------

    def _shown(self) -> list[ColumnDef]:
        return self._layouts.columns(self._surface)

    def _hidden(self) -> list[ColumnDef]:
        return [
            column for column, visible in self._layouts.all_columns(self._surface) if not visible
        ]

    def _refill(self, *, select_shown: int = 0, select_hidden: int = -1) -> None:
        shown = self._shown()
        hidden = self._hidden()
        self._shown_list.Set([column.label for column in shown])
        self._hidden_list.Set([column.label for column in hidden])
        if shown:
            self._shown_list.SetSelection(max(0, min(select_shown, len(shown) - 1)))
        if hidden and select_hidden >= 0:
            self._hidden_list.SetSelection(max(0, min(select_hidden, len(hidden) - 1)))
        elif hidden:
            self._hidden_list.SetSelection(0)
        self._hide_btn.Enable(bool(shown))
        self._show_btn.Enable(bool(hidden))
        self._refresh_preview()
        self._describe_shown()

    def _refresh_preview(self) -> None:
        preview = self._layouts.preview(self._surface)
        self._preview.SetValue(preview or "(this list would read nothing)")

    def _describe_shown(self) -> None:
        index = self._shown_list.GetSelection()
        shown = self._shown()
        if not (0 <= index < len(shown)):
            self._description.SetLabel("")
            return
        column = shown[index]
        position = f"Read {_ordinal(index + 1)} of {len(shown)}"
        if column.pinned:
            position += " -- this column names the row and cannot be hidden"
        self._description.SetLabel(f"{column.description} {position}.")

    def _describe_hidden(self) -> None:
        index = self._hidden_list.GetSelection()
        hidden = self._hidden()
        if not (0 <= index < len(hidden)):
            return
        column = hidden[index]
        self._description.SetLabel(f"{column.description} Not read out on any row.")

    def _on_surface_choice(self, _event: object) -> None:
        index = max(0, self._surface_choice.GetSelection())
        self._surface = self._labels[index][0]
        self._refill()
        self._announce(f"{self._labels[index][1]}: {len(self._shown())} columns shown")

    def _on_shown_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if event.AltDown() and code == wx.WXK_UP:
            self._move(-1)
            return
        if event.AltDown() and code == wx.WXK_DOWN:
            self._move(1)
            return
        event.Skip()

    def _move(self, delta: int) -> None:
        """Swap two adjacent *shown* columns, in the full order.

        The swap happens in the full order rather than in the visible list, so a
        hidden column sitting between them keeps its place and comes back where
        it belongs rather than jumping when it is shown again.
        """
        index = self._shown_list.GetSelection()
        shown = self._shown()
        target = index + delta
        if not (0 <= index < len(shown)) or not (0 <= target < len(shown)):
            self._announce("Already at the end of the list.")
            return
        order = self._layouts.order(self._surface)
        first = order.index(shown[index].id)
        second = order.index(shown[target].id)
        order[first], order[second] = order[second], order[first]
        self._layouts.set_order(self._surface, order)
        self._refill(select_shown=target)
        self._announce(f"{shown[index].label} is now read {_ordinal(target + 1)}")

    def _hide(self) -> None:
        index = self._shown_list.GetSelection()
        shown = self._shown()
        if not (0 <= index < len(shown)):
            return
        column = shown[index]
        if column.pinned:
            # Refused rather than disabled: a disabled button on a row somebody
            # deliberately chose says only "no", and the reason is the useful
            # half of the answer.
            self._announce(f"{column.label} cannot be hidden -- a row has to say what it is.")
            return
        self._layouts.set_visible(self._surface, column.id, False)
        self._refill(select_shown=index)
        self._announce(
            f"{column.label} hidden. A row now reads: {self._layouts.preview(self._surface)}"
        )

    def _show(self) -> None:
        index = self._hidden_list.GetSelection()
        hidden = self._hidden()
        if not (0 <= index < len(hidden)):
            return
        column = hidden[index]
        self._layouts.set_visible(self._surface, column.id, True)
        shown = self._shown()
        position = next((i for i, entry in enumerate(shown) if entry.id == column.id), 0)
        self._refill(select_shown=position)
        self._announce(
            f"{column.label} is shown again, read {_ordinal(position + 1)}. "
            f"A row now reads: {self._layouts.preview(self._surface)}"
        )

    def _reset(self) -> None:
        self._layouts.reset(self._surface)
        self._refill()
        label = dict(self._labels).get(self._surface, "This list")
        self._announce(f"{label} columns reset to the way they shipped")

    def _on_ok(self, _event: object) -> None:
        # Repair once more on the way out: nothing here can produce an invalid
        # layout, but the record is about to be written to disk and read back by
        # a future build, and that is the file that has to be trustworthy.
        for surface, _label in self._labels:
            self._layouts.set_order(surface, self._layouts.order(surface))
        self._result = self._layouts
        self.dialog.EndModal(self._wx.ID_OK)


def _ordinal(number: int) -> str:
    """ "1st", "2nd", "3rd"... -- said rather than shown, so it reads aloud."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"
