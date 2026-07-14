"""Dialog inventory registry gate (A11Y-4 / DLG-3).

These tests are the "magical" enforcement zfix.md asks for: the committed
dialog registry snapshot must exactly match the dialog surfaces found in source,
and every surface must carry a sanctioned classification. A new, moved, or
removed dialog fails the gate until the author deliberately regenerates the
snapshot with ``python -m quill.tools.dialog_inventory --write`` and the
resulting classification is reviewed in the diff.
"""

from __future__ import annotations

from quill.tools.dialog_inventory import (
    SURFACES,
    load_snapshot,
    platform_map,
    scan_dialog_surfaces,
    surface_map,
)

_REGEN = "Run 'python -m quill.tools.dialog_inventory --write' and review the diff."


def test_registry_snapshot_matches_source() -> None:
    """The committed registry must equal the live source scan exactly."""
    live = surface_map(scan_dialog_surfaces())
    snapshot = load_snapshot()

    new_dialogs = sorted(set(live) - set(snapshot))
    removed_dialogs = sorted(set(snapshot) - set(live))
    reclassified = sorted(key for key in set(live) & set(snapshot) if live[key] != snapshot[key])

    assert not new_dialogs, (
        "Unregistered dialog surface(s) found in source. Every dialog must be "
        f"registered and classified. {_REGEN}\nNew: {new_dialogs}"
    )
    assert not removed_dialogs, (
        f"Dialog surface(s) removed from source but still in the registry. {_REGEN}"
        f"\nRemoved: {removed_dialogs}"
    )
    assert not reclassified, (
        f"Dialog surface classification changed in source. {_REGEN}\nReclassified: {reclassified}"
    )


def test_every_surface_has_a_sanctioned_classification() -> None:
    """No bespoke surface drift: every entry is native, web, or hardened_custom."""
    snapshot = load_snapshot()
    unsanctioned = sorted(
        f"{key} -> {value}" for key, value in snapshot.items() if value not in SURFACES
    )
    assert not unsanctioned, (
        f"Dialog surfaces must be one of native/web/hardened_custom. Unsanctioned: {unsanctioned}"
    )


def test_registry_is_not_empty() -> None:
    """Guard against a scanner regression silently emptying the registry."""
    assert len(load_snapshot()) >= 100


def test_scan_is_deterministic() -> None:
    """Two scans return identical, sorted output (stable keys, no flakiness)."""
    first = [surface.key for surface in scan_dialog_surfaces()]
    second = [surface.key for surface in scan_dialog_surfaces()]
    assert first == second == sorted(first)


def test_every_surface_has_a_sanctioned_platform_tag() -> None:
    """The platform tag is a lower bound: only ``""`` or ``"darwin"`` ever appear.

    A Mac-only surface (one inside a ``sys.platform == "darwin"`` branch) is
    tagged ``"darwin"`` so a reviewer knows it cannot be exercised on the Windows
    dev box; every other surface is ``""``. No other tag is sanctioned, and a
    scanner regression that emitted anything else would fail here.
    """
    platforms = platform_map(scan_dialog_surfaces())
    unsanctioned = sorted(
        f"{key} -> {tag!r}" for key, tag in platforms.items() if tag not in ("", "darwin")
    )
    assert not unsanctioned, "Platform tags must be '' or 'darwin'. Unsanctioned: " + ", ".join(
        unsanctioned
    )
