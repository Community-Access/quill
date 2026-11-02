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
    # Record a demonstration (2026-10-29). The check report beside a finished
    # recording is written for the user, like the screenshot report above.
    "core/demo_recording_verify.py::save_reports": "export",
    # The in-progress recording's session file, read back only to recover an
    # unfinished recording and removed when it is finished: a recovery marker.
    "core/demo_recording_session.py::save": "marker",
    # Do Not Disturb as it was before recording, so a crash can put it back;
    # deleted once restored.
    "platform/windows/focus_guard.py::start": "marker",
    # The recording window's last choices and the broadcast settings (never the
    # password, which is in Windows Credential Manager): real config with no
    # version stamp yet.
    "apps/studio_demo.py::record_demonstration": "needs-versioning",
    "apps/studio_streaming.py::_start_stream": "needs-versioning",
    # Studio's own Choose Your AI choice and picture consent (codex.md Phase 3):
    # names and ids only, never a key or a token; no version stamp yet.
    "core/audio_studio/ai_settings.py::save_ai_settings": "needs-versioning",
    # Describe a Folder (2026-11-01): one result file per picture under Studio's
    # data, holding the descriptions the person asked for. Self-describing and
    # additive (schema_version 1, a later schema read for what is known), and
    # never config: user-created content.
    "core/ai/picture_batch.py::save_result": "content",
}
