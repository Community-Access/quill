"""The GitHub workbench's reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 when the GitHub
workbench (2026-11-07) brought five write sites. Every one writes through
``write_json_atomic``; none holds a token (tokens live in the credential store).
"""

from __future__ import annotations

GITHUB_ENTRIES: dict[str, str] = {
    # The account list: non-secret login and host per account, schema-stamped.
    "core/github/accounts.py::_persist": "versioned",
    # Local issue and review drafts, kept until they are submitted or discarded.
    "core/github/local_drafts.py::_write": "content",
    # Pending line comments, kept until they go out with the review (Wave 2).
    "core/github/line_comment_drafts.py::_write": "content",
    # The diff's line-mark style (words or symbols), shared by both editors.
    "core/github/review_preferences.py::save_line_marks": "marker",
    # The attention queue's snoozes and the remembered place in each view:
    # regenerable state, and losing it only costs a re-sort.
    "core/github/attention_queue.py::save": "cache",
    "core/github/navigation_state.py::save": "cache",
    # A one-time marker written while moving saved items to per-account files.
    "core/github/saved_items.py::load": "marker",
}
