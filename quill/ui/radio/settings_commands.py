"""The radio's three remembered-choice surfaces, driven from the app shell.

Extracted from ``main_frame_radio`` under GATE-11 (extract, never rebaseline),
and a real seam: each of these opens a small settings dialog, persists what came
back, and confirms it in one spoken sentence. The host passes itself in,
exactly like ``browse_refresh`` and ``download_runner``.
"""

from __future__ import annotations

from typing import Any


def search_sources(host: Any) -> None:
    """Choose which directories Find Stations searches (remembered)."""
    from quill.core.radio import search_sources as model
    from quill.ui.radio.search_sources_dialog import SearchSourcesDialog

    dialog = SearchSourcesDialog(
        host.frame,
        enabled=host._radio_history.search_sources_enabled,
        show_modal_dialog=host._show_modal_dialog,
        announce=host._announce,
    )
    host._radio_history.search_sources_enabled = dialog.show()
    host._save_radio_history()
    host._announce(model.describe_selection(host._radio_history.search_sources_enabled))


def browse_sources_visibility(host: Any) -> None:
    """Choose which branches Browse Stations shows (remembered).

    The counterpart of Search Sources, under the same rule: a branch that is
    off is not in the tree at all, and is never contacted.
    """
    from quill.core.radio import browse_visibility
    from quill.ui.radio.browse_sources_dialog import BrowseSourcesDialog

    dialog = BrowseSourcesDialog(
        host.frame,
        enabled=host._radio_history.browse_sources_enabled,
        show_modal_dialog=host._show_modal_dialog,
        announce=host._announce,
    )
    host._radio_history.browse_sources_enabled = dialog.show()
    host._save_radio_history()
    host._announce(browse_visibility.describe_selection(host._radio_history.browse_sources_enabled))


def download_preferences(host: Any) -> None:
    """Where downloads land and how they are filed (remembered)."""
    from quill.core.paths import app_data_dir
    from quill.core.radio import download_prefs
    from quill.ui.radio.download_prefs_dialog import DownloadPrefsDialog

    dialog = DownloadPrefsDialog(
        host.frame,
        prefs=download_prefs.load(app_data_dir()),
        show_modal_dialog=host._show_modal_dialog,
        announce=host._announce,
    )
    chosen = dialog.show()
    if chosen is None:
        return
    try:
        download_prefs.save(app_data_dir(), chosen)
    except OSError:
        host._announce("Those preferences could not be saved.")
        return
    # The runner caches prefs on its host (this object); refresh the cache so
    # the very next download files under the rules just chosen.
    host._download_prefs = chosen
    host._announce(chosen.describe())
