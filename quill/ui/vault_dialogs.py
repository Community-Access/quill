"""Accessible list dialogs for the Vault (wx shell over quill.core.vault).

``VaultListDialog`` is a single-column, keyboard-operable list used for the
Backlinks pane and the "Insert link to note" / note-chooser pickers. Each row
carries an opaque payload; activating a row (Enter, Space, or double-click) hands
that payload to ``on_activate``. ``__init__`` builds no wx, so ``labels`` and
``activate_index`` are unit-tested without a display, like the Story Studio
dialogs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


def _end_modal_then(wx: Any, dialog: Any, func: Callable[..., Any], *args: Any) -> None:
    """End the modal first, then dispatch the activation callback.

    Activation callbacks open files or mutate the UI; running them while the
    dialog is still modal (parent disabled) caused focus glitches and
    re-entrancy risk (#788 review). CallAfter defers until the modal has
    unwound; stub wx objects in unit tests fall back to a direct call.
    """
    if dialog is not None:
        dialog.EndModal(wx.ID_OK)
    call_after = getattr(wx, "CallAfter", None)
    if callable(call_after):
        call_after(func, *args)
    else:
        func(*args)


class VaultListDialog:
    """A labelled, activatable list of ``(label, payload)`` rows."""

    def __init__(
        self,
        wx: Any,
        *,
        heading: str,
        items: Sequence[tuple[str, Any]],
        on_activate: Callable[[Any], None] | None = None,
    ) -> None:
        self._wx = wx
        self._heading = heading
        self._items = list(items)
        self._on_activate = on_activate
        self._listbox: Any = None
        self._dialog: Any = None
        self._activated = False

    @property
    def labels(self) -> list[str]:
        return [label for label, _payload in self._items]

    def activate_index(self, index: int) -> bool:
        """Fire ``on_activate`` with the row's payload. Returns False if out of range."""
        if not 0 <= index < len(self._items):
            return False
        if self._on_activate is not None:
            self._on_activate(self._items[index][1])
        return True

    # --- wx construction (no display in unit tests) -----------------------

    def populate(self, dialog: Any) -> Any:
        """Build the heading + list box; return the outer sizer."""
        from quill.ui.dialog_contract import apply_listbox_activation

        wx = self._wx
        self._dialog = dialog
        outer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(dialog, label=self._heading)
        outer.Add(label, 0, wx.ALL, 8)
        listbox = wx.ListBox(dialog, choices=self.labels, style=wx.LB_SINGLE)
        listbox.SetName(self._heading)
        if self._items:
            listbox.SetSelection(0)
        self._listbox = listbox
        apply_listbox_activation(listbox, self._on_listbox_activate)
        outer.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizer(outer)
        return outer

    def _on_listbox_activate(self, _event: Any) -> None:
        index = self._listbox.GetSelection() if self._listbox is not None else -1
        if 0 <= index < len(self._items):
            self._activated = True
            _end_modal_then(self._wx, self._dialog, self.activate_index, index)

    def activate_selected(self) -> bool:
        """Activate the currently selected row (the OK/Open button path).

        No-op when list activation already dispatched (Enter/double-click ends
        the modal with ID_OK too, and must not open the row twice).
        """
        if self._activated:
            return False
        index = self._listbox.GetSelection() if self._listbox is not None else -1
        if not 0 <= index < len(self._items):
            return False
        self._activated = True
        return self.activate_index(index)


class VaultFilterDialog:
    """A filter field over a live-updating list — the quick switcher / vault search.

    ``provider(query) -> [(label, payload)]`` is re-run as the user types; ``count_verb``
    fills the spoken running-count announcement ("7 matches"). The non-wx seam (``update``,
    ``labels``, ``activate_index``) is unit-tested without a display; ``populate`` builds
    the accessible field-plus-list widget. Optional ``option_labels`` add labelled
    checkboxes (e.g. Regex / Whole word) whose state is passed to ``provider`` as the
    second positional arg (a dict), so the same dialog serves the plain quick switcher and
    the search surface.
    """

    def __init__(
        self,
        wx: Any,
        *,
        heading: str,
        prompt: str,
        provider: Callable[..., Sequence[tuple[str, Any]]],
        on_activate: Callable[[Any], None] | None = None,
        announce: Callable[[str], None] | None = None,
        count_verb: str = "matches",
        option_labels: Sequence[str] = (),
    ) -> None:
        self._wx = wx
        self._heading = heading
        self._prompt = prompt
        self._provider = provider
        self._on_activate = on_activate
        self._announce = announce or (lambda _m: None)
        self._count_verb = count_verb
        self._option_labels = list(option_labels)
        self._items: list[tuple[str, Any]] = list(self._call_provider("", {}))
        self._field: Any = None
        self._listbox: Any = None
        self._dialog: Any = None
        self._checkboxes: list[Any] = []
        self._activated = False

    def _call_provider(self, query: str, options: dict[str, bool]) -> Sequence[tuple[str, Any]]:
        return self._provider(query, options) if self._option_labels else self._provider(query)

    @property
    def labels(self) -> list[str]:
        return [label for label, _payload in self._items]

    def update(self, query: str, options: dict[str, bool] | None = None) -> int:
        """Re-run the provider; store the rows; return the count (for the announcement)."""
        self._items = list(self._call_provider(query, options or {}))
        return len(self._items)

    def activate_index(self, index: int) -> bool:
        if not 0 <= index < len(self._items):
            return False
        if self._on_activate is not None:
            self._on_activate(self._items[index][1])
        return True

    # --- wx construction --------------------------------------------------

    def _options(self) -> dict[str, bool]:
        return {
            label: bool(cb.GetValue())
            for label, cb in zip(self._option_labels, self._checkboxes, strict=False)
        }

    def _refresh(self) -> None:
        query = self._field.GetValue() if self._field is not None else ""
        count = self.update(query, self._options())
        if self._listbox is not None:
            self._listbox.Set(self.labels)
            if self._items:
                self._listbox.SetSelection(0)
        self._announce(f"{count} {self._count_verb}")

    def populate(self, dialog: Any) -> Any:
        from quill.ui.dialog_contract import apply_listbox_activation

        wx = self._wx
        self._dialog = dialog
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(wx.StaticText(dialog, label=self._prompt), 0, wx.ALL, 8)

        field = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        field.SetName(self._prompt)
        self._field = field
        outer.Add(field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        for label in self._option_labels:
            checkbox = wx.CheckBox(dialog, label=label)
            self._checkboxes.append(checkbox)
            checkbox.Bind(wx.EVT_CHECKBOX, lambda _e: self._refresh())
            outer.Add(checkbox, 0, wx.LEFT | wx.RIGHT, 8)

        listbox = wx.ListBox(dialog, choices=self.labels, style=wx.LB_SINGLE)
        listbox.SetName(self._heading)
        if self._items:
            listbox.SetSelection(0)
        self._listbox = listbox
        apply_listbox_activation(listbox, self._on_listbox_activate)
        outer.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

        field.Bind(wx.EVT_TEXT, lambda _e: self._refresh())
        field.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._activate_selected())
        field.Bind(wx.EVT_KEY_DOWN, self._on_field_key)
        dialog.SetSizer(outer)
        return outer

    def _on_field_key(self, event: Any) -> None:
        # Down-arrow from the filter field moves focus into the results for arrowing.
        if event.GetKeyCode() == self._wx.WXK_DOWN and self._listbox is not None:
            self._listbox.SetFocus()
        else:
            event.Skip()

    def _activate_selected(self) -> None:
        index = self._listbox.GetSelection() if self._listbox is not None else -1
        if index < 0 and self._items:
            index = 0  # Enter in the field opens the top match
        if 0 <= index < len(self._items):
            self._activated = True
            _end_modal_then(self._wx, self._dialog, self.activate_index, index)

    def activate_selected(self) -> bool:
        """Activate the selected row from the OK/Open button; no-op if the
        list already dispatched (Enter/double-click also ends with ID_OK)."""
        if self._activated:
            return False
        index = self._listbox.GetSelection() if self._listbox is not None else -1
        if index < 0 and self._items:
            index = 0
        if not 0 <= index < len(self._items):
            return False
        self._activated = True
        return self.activate_index(index)

    def _on_listbox_activate(self, _event: Any) -> None:
        self._activate_selected()


class VaultExplorerDialog:
    """A keyboard tree of the vault's notes (Vault Explorer).

    Populates a ``wx.TreeCtrl`` from the wx-free :class:`ExplorerNode` tree
    (``quill.core.vault.explorer.build_note_tree``); activating a note leaf (Enter / double
    click) hands its rel path to ``on_activate`` and closes. Folders expand/collapse as
    usual. Each note's rel path rides on the tree item via ``SetItemData`` so no wx item id
    is used as a dict key.
    """

    def __init__(self, wx: Any, *, tree: Any, on_activate: Callable[[str], None]) -> None:
        self._wx = wx
        self._tree = tree
        self._on_activate = on_activate
        self._ctrl: Any = None
        self._dialog: Any = None

    def populate(self, dialog: Any) -> Any:
        wx = self._wx
        self._dialog = dialog
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(wx.StaticText(dialog, label="Notes"), 0, wx.ALL, 8)
        ctrl = wx.TreeCtrl(dialog, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_SINGLE)
        ctrl.SetName("Vault notes")
        root_id = ctrl.AddRoot("Vault")
        self._add_children(ctrl, root_id, self._tree)
        ctrl.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activated)
        self._ctrl = ctrl
        outer.Add(ctrl, 1, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizer(outer)
        return outer

    def _add_children(self, ctrl: Any, parent_id: Any, node: Any) -> None:
        for child in node.children:
            item = ctrl.AppendItem(parent_id, child.label)
            ctrl.SetItemData(item, child.path)  # str for a note, None for a folder
            if child.path is None:
                self._add_children(ctrl, item, child)

    def _on_activated(self, event: Any) -> None:
        path = self._ctrl.GetItemData(event.GetItem()) if self._ctrl is not None else None
        if path is None:
            event.Skip()  # a folder: let the tree expand/collapse
            return
        _end_modal_then(self._wx, self._dialog, self._on_activate, path)


# ── Modal shells ─────────────────────────────────────────────────────────────
# Shared dialog plumbing for the MainFrame vault mixin, kept here so the mixin
# stays within its GATE-11 size budget. ``frame`` is the MainFrame.


def show_vault_list_modal(frame: Any, heading: str, items: Any, on_activate: Any = None) -> None:
    """Show a VaultListDialog modally; OK ("Open") activates the selection."""
    from quill.ui.dialog_contract import apply_modal_ids

    wx = frame._wx
    activate = on_activate or (lambda payload: frame._open_vault_note(payload[0], payload[1]))
    view = VaultListDialog(wx, heading=heading, items=items, on_activate=activate)
    dialog = wx.Dialog(frame.frame, title=heading, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    outer = view.populate(dialog)
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label="&Open", cancel_id=wx.ID_CANCEL
    )
    try:
        # The button is labelled "Open", so OK must actually open the selected
        # row, exactly like Enter on the list (#788 review).
        if frame._show_modal_dialog(dialog, heading) == wx.ID_OK:
            view.activate_selected()
    finally:
        dialog.Destroy()


def show_vault_filter_modal(
    frame: Any,
    heading: str,
    *,
    prompt: str,
    provider: Any,
    on_activate: Any,
    count_verb: str,
    option_labels: Sequence[str] = (),
) -> None:
    """Show a VaultFilterDialog modally; OK ("Open") activates the selection."""
    from quill.ui.dialog_contract import apply_modal_ids

    wx = frame._wx
    view = VaultFilterDialog(
        wx,
        heading=heading,
        prompt=prompt,
        provider=provider,
        on_activate=on_activate,
        announce=frame._announce,
        count_verb=count_verb,
        option_labels=option_labels,
    )
    dialog = wx.Dialog(frame.frame, title=heading, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    outer = view.populate(dialog)
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    apply_modal_ids(
        dialog, affirmative_id=wx.ID_OK, affirmative_label="&Open", cancel_id=wx.ID_CANCEL
    )
    try:
        if frame._show_modal_dialog(dialog, heading) == wx.ID_OK:
            view.activate_selected()
    finally:
        dialog.Destroy()
