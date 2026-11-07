"""The family-wide choice files' reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 -- extract, never
rebaseline -- when Slider Keys (2026-10-26) joined App Sounds as one small file
of choices every Quill app reads. The seam is real: both are one file for the
whole family in the shared data folder, rather than a field per app.
"""

from __future__ import annotations

FAMILY_ENTRIES: dict[str, str] = {
    # Where each app's own sounds play (app_sounds.json), and which way the
    # arrow keys move a slider in every app (slider_keys.json).
    "core/app_sounds_store.py::save": "marker",
    "core/slider_key_layout.py::save": "marker",
    # Saved find-and-replace jobs, in each editor's own data folder: lists the
    # user made, whose shape only ever grows (both editors, 2026-11-07).
    "core/replace_jobs.py::save_replace_jobs": "content",
}
