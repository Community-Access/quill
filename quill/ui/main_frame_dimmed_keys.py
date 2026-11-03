"""QUILL's dimmed markup rows keep a key that says why, instead of a dead one.

The same fix as QUILL Lite's (:mod:`quill.ui.dimmed_row_keys`, reported
2026-11-02 as "commands produce no feedback at all in a blank document"). QUILL
dims the Markdown rows outside Markdown, the heading and table rows outside
Markdown and HTML, and Insert HTML Tag outside HTML -- and a new document is
plain, so every one of those keys was dead there: Windows does not fire the
accelerator of a disabled menu row, and nothing said why.

QUILL's handlers are not all refusals. Insert HTML Tag, reached in a plain
document, would open its picker and write HTML into a file that has none, which
is why the row is dimmed in the first place. So the key does not run the
command: it says, in one sentence, what the command needs. The sentence goes
through ``_announce_result``, QUILL's announcement service (spoken and
brailled), forced because the user asked for something and is owed the answer.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from quill.ui.dimmed_row_keys import DimmedRowKeys

__all__ = ["DimmedMarkupKeysMixin"]

#: What each kind of dimmed row needs, in the order the refresh passes them.
_NEEDS = ("a Markdown document", "a Markdown or HTML document", "an HTML document")


class DimmedMarkupKeysMixin:
    """The accelerator table, with dimmed markup rows routed to a sentence."""

    def _dimmed_markup_keeper(self) -> DimmedRowKeys | None:
        frame = getattr(self, "frame", None)
        if frame is None or not hasattr(frame, "SetAcceleratorTable"):
            return None  # a test double without a real window
        keeper = getattr(self, "_dimmed_row_keys", None)
        if keeper is None:
            import wx

            keeper = DimmedRowKeys(wx, frame, self._dimmed_row_refusal)
            self._dimmed_row_keys = keeper
        return keeper

    def _dimmed_row_refusal(self, menu_id: Any) -> Any:
        def say(_event: Any) -> None:
            sentences = getattr(self, "_dimmed_row_sentences", {})
            self._announce_result(  # type: ignore[attr-defined]
                sentences.get(menu_id, "That command does not work in this document.")
            )

        return say

    def _set_accelerator_base(self, entries: list[Any]) -> None:
        """Install *entries* as the frame's table, dimmed rows' keys rerouted."""
        keeper = self._dimmed_markup_keeper()
        if keeper is None:
            import wx

            self.frame.SetAcceleratorTable(wx.AcceleratorTable(entries))  # type: ignore[attr-defined]
            return
        keeper.set_base(entries)
        # The ids, not the rows: a rebuilt menu bar has new row objects, and the
        # last refresh's would be gone.
        self._route_dimmed_markup_keys(*getattr(self, "_dimmed_markup_groups", ()))

    def _route_dimmed_markup_keys(self, *groups: Iterable[Any]) -> None:
        """Called by the contextual refresh with its three groups of row ids."""
        self._dimmed_markup_groups = tuple(tuple(ids) for ids in groups)
        keeper = self._dimmed_markup_keeper()
        if keeper is None:
            return
        get_menu_bar = getattr(self.frame, "GetMenuBar", None)  # type: ignore[attr-defined]
        menu_bar = get_menu_bar() if callable(get_menu_bar) and self._dimmed_markup_groups else None
        rows: dict[int, Any] = {}
        sentences: dict[int, str] = {}
        for ids, needs in zip(self._dimmed_markup_groups, _NEEDS, strict=False):
            for item_id in ids:
                item = menu_bar.FindItemById(item_id) if menu_bar is not None else None
                if item is None or item.IsEnabled():
                    continue
                rows[int(item_id)] = item
                name = str(item.GetItemLabelText()).rstrip(". ")
                sentences[int(item_id)] = f"{name} needs {needs}."
        self._dimmed_row_sentences = sentences
        keeper.apply(rows)
