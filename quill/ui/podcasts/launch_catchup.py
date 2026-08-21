"""What Quill Radio did while Cast was closed, folded in at launch.

Two handoff files, read in one place. ``radio-listens.json`` carries what Radio
*heard* -- positions and finished episodes -- and ``radio-actions.json`` carries
what the listener *asked for* from a Radio browse row: play next, add to the
queue, send to the Inbox, mark played.

**Quiet on purpose.** A launch summary would talk over the screen reader
announcing the window, and the result is visible in the lists a moment later
anyway. The counts are returned for a caller that wants them -- nothing in the
app currently does, and that is the right default.

**Two files rather than one field**, for the forward-compatibility reason
``core/podcasts/radio_actions`` sets out at length: an older Cast reading a new
Radio's ``action`` field on the *listens* record would match it, do nothing, and
then delete it, losing the instruction silently. A file it never opens leaves
the backlog intact.

Extracted from ``main_frame_podcasts`` under GATE-11.
"""

from __future__ import annotations

from typing import Any


def catch_up_with_radio(library: Any) -> tuple[int, int]:
    """Merge both Radio handoffs into *library* and save if anything changed.

    Returns ``(positions_updated, instructions_applied)``. Never raises: a
    handoff that cannot be read must not stop the app opening.

    Saves with a plain ``save_library`` rather than the frame's own helper,
    which reaches the download queue -- that does not exist yet this early in
    initialisation.
    """
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.radio_actions import merge_radio_actions
        from quill.core.podcasts.radio_listens import merge_radio_listens
        from quill.core.podcasts.subscriptions import save_library

        data_dir = app_data_dir()
        updated, _finished = merge_radio_listens(data_dir, library)
        applied, _said = merge_radio_actions(data_dir, library)
        if updated or applied:
            save_library(data_dir, library)
        return (updated, applied)
    except Exception:  # noqa: BLE001 - a handoff must never block launch
        return (0, 0)
