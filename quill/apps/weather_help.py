"""Quill Weather's Help menu: its documents, its tutorials, and its About box.

Extracted from ``quill/apps/weather.py`` under GATE-11 (extract, never
rebaseline) when Help > Tutorials arrived. All three are the same kind of
thing -- a door on the Help menu to something written down -- so they live
together and the app shell keeps three one-line methods.
"""

from __future__ import annotations

from typing import Any

#: Which document each Help-menu item opens, by its file stem.
DOC_TITLES: dict[str, str] = {
    "userguide": "Quill Weather User Guide",
    "release-notes-2.2": "Quill Weather Release Notes",
    "tutorials": "Quill Weather Tutorials",
}

ABOUT_BODY = (
    "The accessible weather watcher from Quill.\n\n"
    "Keeps an eye on official National Weather Service alerts for your "
    "location and speaks new warnings as they are issued -- even while "
    "minimized to the system tray.\n\nSupport: support@community-access.org"
)


def open_doc(host: Any, stem: str) -> None:
    """Open a bundled doc (``docs\\`` beside the exe, or a dev checkout)."""
    host.open_app_document(
        host._doc_candidates("quill-weather", stem),
        title=DOC_TITLES.get(stem, stem),
        cache_name="app-docs",
    )


def open_tutorials(host: Any, slug: str = "") -> None:
    """Open the Tutorials window, optionally straight into one lesson."""
    from quill.ui.weather.tutorials import open_tutorials as show

    show(host, slug=slug)


def show_about(host: Any, wx: Any, title: str, version: str) -> None:
    """The About box, in the app shell's own message-box gate."""
    host._show_message_box(
        f"{title} {version}\n{ABOUT_BODY}",
        f"About {title}",
        wx.OK | wx.ICON_INFORMATION,
    )
