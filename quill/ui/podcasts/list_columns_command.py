"""Subscriptions > Choose Columns... in QUILL Cast.

The counterpart of ``ui/radio/list_columns_command``, on Cast's catalogue. Both
apps open the same dialog on the same machinery; only the catalogue, the store
and the windows to rebuild differ.
"""

from __future__ import annotations

from typing import Any

__all__ = ["open_list_columns"]


def open_list_columns(host: Any) -> None:
    """The column window, on Cast's own catalogue."""
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.list_columns import SURFACE_LABELS, save_podcast_column_layouts
    from quill.ui.media.list_columns_dialog import ListColumnsDialog
    from quill.ui.media.list_columns_view import invalidate, layouts_for

    announce = getattr(host, "_announce", None)
    dialog = ListColumnsDialog(
        getattr(host, "frame", None) or host,
        layouts=layouts_for("cast"),
        surface_labels=SURFACE_LABELS,
        announce_cb=announce if callable(announce) else None,
        title="Choose Columns",
    )
    edited = dialog.show()
    if edited is None:
        return
    try:
        save_podcast_column_layouts(app_data_dir(), edited)
    except Exception:  # noqa: BLE001 - a layout that could not be saved still applies now
        pass
    invalidate("cast")
    _rebuild_open_lists(host)
    if callable(announce):
        announce("Columns saved.")


def _rebuild_open_lists(host: Any) -> None:
    """Rebuild the Manager's episode list if it is open.

    Cast holds a live reference to its Manager (``_podcast_manager_dialog``)
    precisely so it can be refreshed in place, so a layout saved while it is
    open takes effect there rather than next time. Best-effort and duck-typed:
    a window that is not open, or a build without the hook, is simply not asked,
    because nothing here is worth losing a layout somebody just chose.
    """
    window = getattr(host, "_podcast_manager_dialog", None)
    rebuild = getattr(window, "reapply_columns", None)
    if callable(rebuild):
        try:
            rebuild()
        except Exception:  # noqa: BLE001 - a stale window is not worth a traceback
            pass
