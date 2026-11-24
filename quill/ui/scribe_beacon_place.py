"""Save a Beacon Place, a Next Step in QUILL's Conversions on This Computer (PRD 8.1.7, 8.7).

For a Word or accessible HTML result, "Save a Beacon Place (Word)..." asks
where the place should point -- "Save a Beacon Place", a standard choice
list of "The start of the document" and then each heading, words first
(:func:`quill.core.scribe.headings.heading_rows`) -- and writes the place
straight to Quill Beacon's store
(:func:`quill.apps.beacon.scribe_places.save_place`). The place remembers the
Scribe document, so Beacon can download it again when the file is gone.

It is offered only where Beacon is: a build that shows Beacon, or a computer
where Beacon is installed. QUILL alone says what happened, once: "Saved a
Beacon place: Notes, at Methods." A running Beacon picks the place up on its
next refresh without a word.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

TITLE = "Save a Beacon Place"


def beacon_available() -> bool:
    """Beacon can be reached: released in this build, or installed here."""
    from quill.core.app_launcher import is_app_released

    if is_app_released("beacon"):
        return True
    try:
        from quill.core.paths import app_data_dir
        from quill.core.runtime_apps import installed_apps

        return any(app.ref_id == "beacon" for app in installed_apps(app_data_dir()))
    except Exception:  # noqa: BLE001 - no answer is "not here"
        return False


def choose_heading(parent: Any, path: Path, modal: Callable[[Any, str], int]) -> list[str] | None:
    """Where the place points: ``[]`` for the start, a heading path, or ``None``."""
    import wx

    from quill.core.scribe.headings import document_headings, heading_path, heading_rows
    from quill.ui.dialog_contract import apply_modal_ids

    headings = document_headings(path)
    rows = heading_rows(headings)
    if len(rows) == 1:
        return []  # no headings: the start is the only place there is
    dialog = wx.SingleChoiceDialog(parent, "Save the place at:", TITLE, rows)
    try:
        dialog.SetName("scribe_beacon_place_dialog")  # F1 finds its topic by this name
        dialog.SetSelection(0)
        for child in dialog.GetChildren():
            if isinstance(child, wx.ListBox):
                child.SetName("Save the place at")
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        if modal(dialog, TITLE) != wx.ID_OK:
            return None
        index = dialog.GetSelection()
    finally:
        dialog.Destroy()
    return heading_path(headings, index - 1) if index > 0 else []


def save_beacon_place(
    job: Any,
    format_id: str,
    path: Path,
    *,
    parent: Any,
    say: Callable[[str], None],
    modal: Callable[[Any, str], int],
) -> None:
    """The Next Step: choose where, write the place, say it once."""
    if not job.document_id:
        say(f"{job.display_name} has no Scribe document to remember yet.")
        return
    where = choose_heading(parent, path, modal)
    if where is None:
        return
    from quill.apps.beacon.scribe_places import open_store, save_place

    title = job.title or Path(job.file_name).stem or path.stem
    try:
        store = open_store()
        try:
            save_place(
                store,
                document_id=job.document_id,
                title=title,
                path=path,
                format_id=format_id,
                heading_path=where,
            )
        finally:
            store.close()
    except Exception:  # noqa: BLE001 - said, never raised into Next Steps
        say(
            "Quill Beacon could not save the place: its library is busy or cannot be "
            "written. Close Quill Beacon's open windows and try again."
        )
        return
    at = where[-1] if where else "the start"
    say(f"Saved a Beacon place: {title}, at {at}.")


__all__ = ["TITLE", "beacon_available", "choose_heading", "save_beacon_place"]
