"""QUILL Studio's reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 -- extract, never
rebaseline -- when QUILL Studio's screen capture (2026-10-26) brought eight new
write sites. The seam is real: every site here is a file Studio's capture keeps
beside the user's screenshots, or for its own capture choices.
"""

from __future__ import annotations

STUDIO_ENTRIES: dict[str, str] = {
    # Written beside the user's screenshots: the spoken note, a sequence's and a
    # scrolling capture's evidence, and the verification report.
    "core/screenshot_note.py::finish": "export",
    "core/screenshot_sequences.py::capture_sequence": "export",
    "platform/windows/screenshot_scroll.py::capture_scrolling": "export",
    "core/studio_capture.py::save_capture_report": "export",
    # The user's editing work on a screenshot (layered, self-describing).
    "core/screenshot_project.py::save": "content",
    # Saved capture setups and the capture AI preferences: real config without a
    # version stamp yet -- the backlog the versioned contract is for.
    "core/screenshot_workspaces.py::save_workspace": "needs-versioning",
    "core/screenshot_workspaces.py::remove_workspace": "needs-versioning",
    "core/studio_capture_ai.py::save_capture_ai_preferences": "needs-versioning",
}
