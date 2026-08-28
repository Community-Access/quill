"""The Help menu's documents, and the guided tutorials. Thin wiring.

Extracted from ``quill/apps/radio.py`` under GATE-11 (extract, never
rebaseline) when Help > Tutorials... arrived. Both halves are "a door on the
Help menu to something written down": one opens a rendered document in the
browser, the other opens the tutorial window. Keeping them together means the
app shell keeps two one-line methods rather than two bodies.
"""

from __future__ import annotations

from typing import Any

#: Which document each Help-menu item opens, by its file stem.
DOC_TITLES: dict[str, str] = {
    "userguide": "Quill Radio User Guide",
    "release-notes-3.0": "Quill Radio Release Notes (3.0)",
    "release-notes-3.1": "Quill Radio Release Notes",
    "release-notes-3.0-in-depth": "Quill Radio Release Notes: The Long Version",
    "prd": "Quill Radio Product Requirements",
    "tutorials": "Quill Radio Tutorials",
}


def open_doc(host: Any, stem: str) -> None:
    """Open the rendered document *stem* in the listener's browser."""
    host.open_app_document(
        host._doc_candidates("quill-radio", stem),
        title=DOC_TITLES.get(stem, stem),
        cache_name="app-docs",
    )


def open_tutorials(host: Any, slug: str = "") -> None:
    """Open the Tutorials window, optionally straight into one lesson."""
    from quill.ui.radio.tutorials_dialog import open_tutorials as show

    show(host, slug=slug)


def install_help_items(host: Any, help_menu: Any, wx: Any) -> list[Any]:
    """Append What Is This?, Tutorials and the four documents. Returns the ids.

    The keys are a family, and the family is ordered by how often somebody
    reaches for the door. **F1** is context help for the control you are on --
    QUILL's editor convention, which is why the guide gave that key up. **Ctrl+F1**
    is the guide. **Shift+F1** and **Ctrl+Shift+F1** are the release notes and
    the companion that carries the reasoning; the narrative points at the
    companion by name, so a document nobody can open from the Help menu is a
    document that does not really ship.

    **Ctrl+Alt+F1 is Tutorials** as of 2026-08-27, and the **PRD moved out one
    notch to Alt+Shift+F1** -- the same reasoning that put the PRD on Ctrl+Alt+F1
    in the first place, applied again now there is something newer that is
    reached for far more often. Ctrl+Alt+Shift+F1 was not available: it is a
    QuillVille launcher (``SIBLING_APP_ACCELERATORS``).

    The returned ids are the caller's to keep alive: ``wx.NewIdRef`` ids are
    recycled once nothing references them, and a recycled id is a menu item
    that stops firing.
    """
    ids = {
        name: wx.NewIdRef()
        for name in ("what_is_this", "tutorials", "guide", "notes", "notes_depth", "prd")
    }
    help_menu.Append(ids["what_is_this"], "&What Is This?\tF1")
    help_menu.Append(ids["tutorials"], host._menu_label("&Tutorials...", "radio.tutorials"))
    help_menu.Append(ids["guide"], "&User Guide\tCtrl+F1")
    help_menu.Append(ids["notes"], "&Release Notes\tShift+F1")
    help_menu.Append(ids["notes_depth"], "Release Notes: The &Long Version\tCtrl+Shift+F1")
    help_menu.Append(ids["prd"], "&Product Requirements...\tAlt+Shift+F1")

    frame = host.frame
    frame.Bind(wx.EVT_MENU, lambda _e: host._radio_show_context_help(), id=ids["what_is_this"])
    frame.Bind(wx.EVT_MENU, lambda _e: host.open_radio_tutorials(), id=ids["tutorials"])
    # "Release Notes" opens the notes for the build you are running, which is
    # this one -- 3.1's, written as the work lands. The Long Version stays 3.0's
    # companion piece: it carries the reasoning behind the release before this
    # one, and is a document in its own right rather than a longer edition of
    # whatever shipped most recently.
    for name, stem in (
        ("guide", "userguide"),
        ("notes", "release-notes-3.1"),
        ("notes_depth", "release-notes-3.0-in-depth"),
        ("prd", "prd"),
    ):
        frame.Bind(wx.EVT_MENU, lambda _e, s=stem: open_doc(host, s), id=ids[name])
    return list(ids.values())
