"""GATE-SETDOC: a new setting cannot ship undocumented and unclassified.

EdSharp's ``checkOptionsDocumented``: an undocumented setting is one nobody
can find. Statuses and the ratchet live in
``quill.tools.settings_doc_audit``; what is pinned here:

* nothing is ``missing`` -- a new ``Settings`` field must be documented in
  the corpus or deliberately classified ``internal``;
* the committed snapshot matches the live tree (fields added or removed,
  docs gained or lost);
* ``grandfathered`` only ever shrinks -- the 2026-08-27 backlog is a
  ratchet, not a dumping ground.
"""

from __future__ import annotations

from quill.tools import settings_doc_audit


def test_snapshot_matches_and_nothing_is_missing() -> None:
    committed = settings_doc_audit.load_snapshot()
    live = settings_doc_audit.build_snapshot(committed)
    assert live == committed, (
        "Settings fields or documentation changed. Run "
        "'python -m quill.tools.settings_doc_audit --write', then document "
        "each new field (or classify it internal) -- a setting nobody can "
        "read about is a setting nobody can find."
    )
    missing = sorted(name for name, status in committed.items() if status == "missing")
    assert missing == [], "Undocumented, unclassified settings: " + ", ".join(missing)
    assert set(committed.values()) <= settings_doc_audit.STATUSES


def test_grandfathered_only_shrinks() -> None:
    """A field can leave the backlog (documented or internal), never join it."""
    committed = settings_doc_audit.load_snapshot()
    live = settings_doc_audit.build_snapshot(committed)
    newly_grandfathered = {
        name
        for name, status in live.items()
        if status == "grandfathered" and committed.get(name) != "grandfathered"
    }
    assert newly_grandfathered == set(), (
        "grandfathered is a pre-gate backlog and may only shrink; document "
        "these or classify them internal: " + ", ".join(sorted(newly_grandfathered))
    )


def test_documented_detection_is_alive() -> None:
    """The corpus scan must actually find things (a broken scan passes everything)."""
    assert settings_doc_audit.is_documented("theme") or settings_doc_audit.is_documented(
        "indent_size"
    )
    assert not settings_doc_audit.is_documented("no_such_setting_xyzzy_42")
