"""Dictation's reviewed persistence sites.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 -- extract, never
rebaseline -- when the family's shared dictation settings (dict.md D-13,
2026-10-16) needed three more entries. The seam is real: every site here is a
file dictation keeps for itself or for the family's dictating programs.
"""

from __future__ import annotations

DICTATION_ENTRIES: dict[str, str] = {
    # Each document's context (2026-10-05, schema-stamped, additive), the
    # one-shot hand-off to Quill Inkwell (read once, deleted), D-2's open review.
    "core/windows_dictation/contexts.py::save": "content",
    "core/windows_dictation/anywhere.py::write_handoff": "cache",
    "core/windows_dictation/review_session.py::save_rescue": "content",
    # D-5 (2026-10-16): words not written, sealed, deleted on delivery; and the
    # opt-in text history, sealed, schema-stamped (rescue.py).
    "core/windows_dictation/rescue.py::keep": "content",
    "core/windows_dictation/rescue.py::_write_history": "content",
    # D-13 (2026-10-16): the family's shared dictation settings, schema-stamped
    # and keeping the fields a newer build wrote; the one-time copy of a
    # program's own settings before it first shares; and the word list's move
    # record (old file -> time and size), which only decides whether to merge.
    "core/windows_dictation/family_store.py::publish_fields": "versioned",
    "core/windows_dictation/family_store.py::_back_up_once": "content",
    "core/windows_dictation/family_words.py::bring_over": "marker",
    # 2026-10-22: which removed models' one-time notice is due or said; an
    # unreadable file reads as none, which costs at most one missed sentence.
    "core/windows_dictation/removed_models.py::_write": "marker",
}

__all__ = ["DICTATION_ENTRIES"]
