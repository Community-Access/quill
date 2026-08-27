"""What the details pane says about the highlighted row.

Extracted from ``browse_tree_dialog`` under GATE-11 (extract, never
rebaseline) when the browse window lost its duplicate transport button and
gained Go to Player. It earns its own module for the usual reason: this is a
question about the *row* -- what is this, where do its answers come from, what
would Enter do -- and not a question about the tree widget.

Five kinds of row, and each is told something different, because a listener
arrowing this tree gets no other chance to learn what they have landed on:

* a **station or episode** shows its own details, show notes included
* a **row that resolves when played** says so before you commit to the wait
* a **folder** says where its answers come from -- your catalog, or the
  internet each time (catalog UX 6.5) -- rather than nothing at all
* an **action row** explains what Enter would do, before Enter
* **nothing selected** clears the pane rather than leaving the last row's text
  standing as though it were current
"""

from __future__ import annotations

from typing import Any


def describe_selection(dialog: Any, data: dict | None) -> None:
    """Fill the details pane, and light the Favorites button when it applies."""

    station = data.get("station") if data else None
    if station is not None:
        dialog._details.ChangeValue(station.details_text)
        dialog._favorite_btn.Enable(True)
        dialog._update_favorite_label(station)
    elif dialog._is_playable(data) and data is not None:
        note = data.get("note") or "resolves when you play it"
        dialog._details.ChangeValue(f"{data['label']}\n{note.capitalize()}.")
        # The stream resolves lazily, but Add to Favorites resolves it on
        # demand (#1210), so the button is live. Label it Add -- we cannot
        # know the saved state before resolving.
        dialog._favorite_btn.Enable(True)
        dialog._favorite_btn.SetLabel("Add to &Favorites")
    elif dialog._is_folder_data(data) and data is not None:
        # A branch explains where its answers come from (catalog UX, 6.5):
        # "Answers from your catalog, updated 2 hours ago." or "Asks the
        # internet each time; nothing is stored." Detail-panel only --
        # never a per-row suffix.
        from quill.core.radio.browse_nodes import split_id
        from quill.core.radio.catalog import read as catalog_read

        kind, _args = split_id(str(data.get("node_id", "")))
        sentence = catalog_read.provenance_sentence(getattr(dialog, "_catalog", None), kind)
        label_text = str(data.get("label", ""))
        dialog._details.ChangeValue(label_text + chr(10) + sentence)
        dialog._favorite_btn.Enable(False)
    elif data is not None and data.get("is_action"):
        # An action row explains itself while merely highlighted, so nobody
        # has to press Enter to learn what Enter would do.
        note = str(data.get("note") or "")
        detail = f"{data['label']}\n{note.capitalize()}. " if note else f"{data['label']}\n"
        dialog._details.ChangeValue(f"{detail}Press Enter to use it.")
        dialog._favorite_btn.Enable(False)
    else:
        dialog._details.ChangeValue("")
        dialog._favorite_btn.Enable(False)
