"""Story element details form (accessible wx shell over quill.core.story.fields).

A labelled text field per structured field for an element (a character's goal,
a plot thread's status, tags), plus any unknown keys already in the file
(preserved). Editing here and editing the file's front matter are the same
bytes. All field logic lives in :mod:`quill.core.story.fields`; this is a wiring
layer. ``__init__`` builds no wx, so the seams (``rows``/``result_fields``) are
unit-tested without a display.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from quill.core.story.fields import FieldRow, build_rows, collect_fields
from quill.core.story.model import ElementKind


def _with_mnemonic(label: str, used: set[str]) -> str:
    """Insert ``&`` before the first letter not already used as a mnemonic."""
    for index, char in enumerate(label):
        if char.isalnum() and char.lower() not in used:
            used.add(char.lower())
            return label[:index] + "&" + label[index:]
    return label


class StoryElementFormDialog:
    """Edits an element's front-matter fields and reports them after OK.

    ``on_save(fields)`` is called with the merged fields dict when the user
    accepts. ``fields`` is the element's current front matter (from
    ``split_front_matter``); ``kind`` selects the default field set.
    """

    def __init__(
        self,
        wx: Any,
        *,
        kind: ElementKind,
        fields: Mapping[str, Any],
        on_save: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._wx = wx
        self._kind = kind
        self._fields = dict(fields)
        self._on_save = on_save
        self._rows: list[FieldRow] = build_rows(kind, self._fields)
        self._controls: dict[str, Any] = {}
        self._dialog: Any = None

    @property
    def rows(self) -> list[FieldRow]:
        return self._rows

    def result_fields(self, values: Mapping[str, str]) -> dict[str, Any]:
        """Merge control ``values`` (keyed by field key) into a fields dict."""
        return collect_fields(self._kind, self._fields, values)

    # --- wx construction (no display in unit tests) -----------------------

    def populate(self, dialog: Any) -> Any:
        """Build a labelled text field per row; return the outer sizer."""
        wx = self._wx
        self._dialog = dialog
        outer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)
        # Each label gets a unique Alt+letter mnemonic; the label immediately
        # precedes its TextCtrl, so the access key focuses the field (#784).
        used_mnemonics: set[str] = set()
        for row in self._rows:
            label = wx.StaticText(dialog, label=f"{_with_mnemonic(row.label, used_mnemonics)}:")
            control = wx.TextCtrl(dialog, value=row.value)
            control.SetName(row.label)
            self._controls[row.key] = control
            grid.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
        outer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        dialog.SetSizer(outer)
        return outer

    def commit(self) -> None:
        """Read the controls and hand the merged fields to ``on_save`` (OK path)."""
        values = {key: control.GetValue() for key, control in self._controls.items()}
        if self._on_save is not None:
            self._on_save(self.result_fields(values))
