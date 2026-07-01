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
        if self.activate_index(index) and self._dialog is not None:
            self._dialog.EndModal(self._wx.ID_OK)
