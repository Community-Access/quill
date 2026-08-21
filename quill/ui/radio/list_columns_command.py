"""View > Choose Columns... in Quill Radio.

Two small jobs, neither of which belongs in a frame at its GATE-11 ceiling:
open the shared column dialog on Radio's catalogue, and make the result take
effect. The same shape as ``ui/radio/quick_actions_command``, for the same
reason -- the wiring is thin, and the frame is not where thin wiring should
accumulate.

**There is nothing open to rebuild.** Both of Radio's configurable lists are
modal windows opened from the same menu bar this item lives on, so the cache is
simply dropped and the next window built reads the new layout -- which is the
very next thing somebody does after pressing OK.
"""

from __future__ import annotations

from typing import Any

__all__ = ["open_list_columns"]


def open_list_columns(host: Any) -> None:
    """The column window, on Radio's own catalogue."""
    from quill.core.paths import app_data_dir
    from quill.core.radio.list_columns import SURFACE_LABELS, save_radio_column_layouts
    from quill.ui.media.list_columns_dialog import ListColumnsDialog
    from quill.ui.media.list_columns_view import invalidate, layouts_for

    announce = getattr(host, "_announce", None)
    dialog = ListColumnsDialog(
        getattr(host, "frame", None) or host,
        layouts=layouts_for("radio"),
        surface_labels=SURFACE_LABELS,
        announce_cb=announce if callable(announce) else None,
        title="Choose Columns",
    )
    edited = dialog.show()
    if edited is None:
        return
    try:
        save_radio_column_layouts(app_data_dir(), edited)
    except Exception:  # noqa: BLE001 - a layout that could not be saved still applies now
        pass
    invalidate("radio")
    if callable(announce):
        announce("Columns saved.")
