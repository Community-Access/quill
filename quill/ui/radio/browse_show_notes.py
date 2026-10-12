"""View Show Notes on a podcast episode row in Quill Radio.

Station Details shows an episode's notes as plain text, which is right for
reading down but turns every link into an address to retype (QUILLVille list,
2026-10-11). This opens the same notes in QUILL Cast's Show Notes window, built
on the shared Notes reader: links are links, Tab moves between them, Links in
These Notes lists them, and Save As keeps them in HTML and Markdown. One window,
raised again for the next episode asked about, never a second copy.

Split from ``browse_tree_menu`` under GATE-11, like ``browse_transcript``: that
module maps a row to its verbs, and this is one verb's whole story.
"""

from __future__ import annotations

from typing import Any


def view(dialog: Any, station: Any) -> None:
    """Open (or raise) the Show Notes window on *station*'s publisher notes."""
    from quill.ui.podcasts.peer_window import open_peer
    from quill.ui.podcasts.show_notes_dialog import ShowNotesWindow

    content: dict[str, Any] = {
        "episode_title": str(getattr(station, "name", "") or ""),
        "description_html": str(getattr(station, "notes_html", "") or ""),
    }
    existing = getattr(dialog, "_show_notes_window", None)
    if existing is not None and existing.frame:
        existing.load(**content)
    open_peer(
        dialog,
        "_show_notes_window",
        # The tree's own window is the parent; the dialog object only wraps it.
        lambda owner: ShowNotesWindow(owner._win, announce_cb=owner._announce, **content),
    )
