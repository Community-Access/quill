"""Accessible-name inventory gate (#1012 / GATE-A11Y-NAME).

The committed snapshot must exactly match the labelable-control sites found in
source, and every site's classification must be sanctioned. A new, moved, or
removed control fails the gate until the author deliberately regenerates the
snapshot with ``python -m quill.tools.accessible_name_audit --write`` and the
resulting classification is reviewed in the diff: a control in a modal dialog
keeps ``modal-hook`` (named at show time by ``ensure_accessible_names``); a
control on a non-modal surface must name itself (``named``) or carry an
explicit ``named-elsewhere`` / ``opt-out``.
"""

from __future__ import annotations

from quill.tools.accessible_name_audit import (
    NAMED,
    STATUSES,
    load_snapshot,
    scan_control_sites,
)

_REGEN = "Run 'python -m quill.tools.accessible_name_audit --write' and review the diff."


def test_inventory_snapshot_matches_source() -> None:
    """The committed inventory must equal the live source scan exactly."""
    live = {site.key: site.named_inline for site in scan_control_sites()}
    snapshot = load_snapshot()

    new_sites = sorted(set(live) - set(snapshot))
    removed_sites = sorted(set(snapshot) - set(live))

    assert not new_sites, (
        "Unregistered labelable control site(s) found in source. Every "
        "control VoiceOver reads by window name must be classified so macOS "
        f"users get a label (#1012). {_REGEN}\nNew: {new_sites}"
    )
    assert not removed_sites, (
        f"Control site(s) removed from source but still in the inventory. {_REGEN}"
        f"\nRemoved: {removed_sites}"
    )


def test_inline_naming_claims_are_verified() -> None:
    """A site the snapshot calls ``named`` must actually name itself inline.

    (The reverse — an inline-named site classified as something else — is a
    stale snapshot; ``--write`` always records inline-named sites as
    ``named``, so the exact-match test above catches it via the diff.)
    """
    live = {site.key: site.named_inline for site in scan_control_sites()}
    snapshot = load_snapshot()

    unverified = sorted(
        key for key, status in snapshot.items() if status == NAMED and not live.get(key, False)
    )
    stale = sorted(
        key for key, status in snapshot.items() if status != NAMED and live.get(key, False)
    )

    assert not unverified, (
        "Snapshot claims these sites name their control inline, but the scan "
        f"finds no naming. {_REGEN}\nUnverified: {unverified}"
    )
    assert not stale, (
        "These sites now name their control inline but the snapshot still "
        f"classifies them otherwise. {_REGEN}\nStale: {stale}"
    )


def test_every_site_has_a_sanctioned_classification() -> None:
    snapshot = load_snapshot()
    unsanctioned = sorted(
        f"{key} -> {value}" for key, value in snapshot.items() if value not in STATUSES
    )
    assert not unsanctioned, f"Unsanctioned classification(s): {unsanctioned}"
