"""QUILL's settings registry, as Find a setting sees it (qc.md X-01).

QUILL's Settings dialog builds each notebook page the first time it is shown,
so the native search -- which walks built controls -- could only find the
first page's settings; and the Preferences hub, which opens that dialog, could
only find the hub's own category names. Both now read the registry's
declarative specs (:mod:`quill.core.settings_registry`) through
:mod:`quill.core.settings_finder`:

* in **Settings**, a match on a page not built yet builds that page, turns to
  it, and focuses the setting -- the same thing that happens for a built one;
* in the **Preferences hub**, a match closes the hub, opens Settings at that
  page with focus on the setting, and says which page it is on (the reader
  says "Settings" and the control; the page is the one thing it does not).

Only specs whose feature is on are declared, the same filter the dialog uses
to decide what to draw, so search never offers a setting Settings will not
show.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.settings_finder import SettingEntry, moved_to, registry_entries
from quill.ui.preferences_search import declare_settings

__all__ = ["SettingsPages", "declare_hub_settings", "declare_settings_pages"]


class SettingsPages:
    """The Settings dialog's lazily built pages, addressable by setting key."""

    def __init__(
        self,
        notebook: Any,
        pages: Sequence[tuple[int, Any, Sequence[Any]]],
        build_page: Callable[[int], None],
        control_index: dict[str, tuple[int, Any]],
    ) -> None:
        self._notebook = notebook
        self._build_page = build_page
        self._control_index = control_index
        self.entries: list[SettingEntry] = []
        self._page_of: dict[str, int] = {}
        for page_index, group, specs in pages:
            for entry in registry_entries([group], specs):
                self.entries.append(entry)
                self._page_of[entry.key] = page_index

    def control_for(self, entry: SettingEntry) -> Any:
        found = self._control_index.get(entry.key)
        return found[1] if found is not None else None

    def go(self, entry: SettingEntry) -> Any:
        """Build and turn to *entry*'s page; return its control (None if none)."""
        page_index = self._page_of.get(entry.key)
        if page_index is None:
            return None
        self._build_page(page_index)
        self._notebook.SetSelection(page_index)
        return self.control_for(entry)

    def focus(self, key: str, announce: Callable[[str], None]) -> SettingEntry | None:
        """Turn to *key*'s page, focus its control, and say which page it is."""
        if not self._notebook:  # the dialog closed before this ran
            return None
        entry = next((e for e in self.entries if e.key == key), None)
        control = self.go(entry) if entry is not None else None
        if entry is None or control is None:
            return None
        control.SetFocus()
        announce(moved_to(entry))
        return entry


def declare_settings_pages(
    dialog: Any,
    notebook: Any,
    pages: Sequence[tuple[int, Any, Sequence[Any]]],
    build_page: Callable[[int], None],
    control_index: dict[str, tuple[int, Any]],
) -> SettingsPages:
    """Give the Settings dialog's search every page, built or not."""
    settings_pages = SettingsPages(notebook, pages, build_page, control_index)
    declare_settings(
        dialog,
        settings_pages.entries,
        settings_pages.go,
        control_for=settings_pages.control_for,
    )
    return settings_pages


def declare_hub_settings(
    dialog: Any, feature_enabled: Callable[[str], bool], open_at: Callable[[str], None]
) -> None:
    """Let the Preferences hub's search find settings inside Settings.

    *open_at* receives the chosen key; it closes the hub and opens Settings
    there. Returning ``None`` from the search's ``go`` tells it focus has left.
    """
    from quill.core import settings_registry as registry

    specs = [
        spec for spec in registry.specs() if not spec.feature_id or feature_enabled(spec.feature_id)
    ]
    entries = registry_entries(registry.groups(), specs, area="the {title} page of Settings")

    def go(entry: SettingEntry) -> None:
        open_at(entry.key)

    declare_settings(dialog, entries, go)
