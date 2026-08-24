"""GATE-REACH: can anybody get here? (list.md 12.3)

QUILL Cast's user guide described a welcome screen for two releases. The dialog
existed, was well written, and had passing tests. Nothing in the app ever called
it.

Every gate we had ran the other way round. ``check_help_coverage`` asks whether
a *feature* has documentation; the two ``*_help_audit`` gates ask whether a
*window in the source* has an authored purpose. All of them start at the code
and look for words. None started at a surface and asked whether a listener
could reach it.

The distinction that makes the audit work is that **tests are not callers**.
The dead dialog was mentioned constantly -- by its own test file, and by a
helper nothing called. Reachability means: start at the app entry points and
follow imports.
"""

from __future__ import annotations

from pathlib import Path

from quill.tools import surface_reachability_audit as audit

REPO = Path(__file__).resolve().parents[3]


def test_the_snapshot_is_current() -> None:
    """The gate in test form, so a dead surface fails the suite and not only
    the scorecard."""
    unreviewed = sorted(k for k, v in audit.build_snapshot().items() if v == audit.UNREACHABLE)

    assert not unreviewed, (
        "these define a window no app entry point can reach by imports: "
        f"{unreviewed}. Wire them up, or classify them 'dynamic'/'parked' via "
        "python -m quill.tools.surface_reachability_audit --write"
    )


def test_the_snapshot_on_disk_matches_the_tree() -> None:
    stored, computed = audit.load_snapshot(), audit.build_snapshot()

    assert stored == computed, (
        "surface_reachability.json has drifted. Regenerate with: "
        "python -m quill.tools.surface_reachability_audit --write"
    )


def test_tests_do_not_count_as_callers() -> None:
    """The whole premise. If ``tests/`` were on the walk, the dialog that
    shipped unreachable would have been reported reachable by its own test.
    """
    assert all("test" not in path.parts for path in audit.entry_modules())
    assert all(path.is_relative_to(REPO / "quill") for path in audit.entry_modules())


def test_an_app_entry_point_is_reachable_from_itself() -> None:
    """A sanity floor: an empty walk would call everything unreachable and an
    over-broad one would call everything reachable, and both would look calm.
    """
    reached = audit.reachable_modules()

    assert "quill.ui.main_frame" in reached
    assert len(reached) > 100


def test_the_two_verbosity_dialogs_it_found_are_wired_now() -> None:
    """The gate's first run named exactly these two, and this is what stops
    the fix from being quietly reverted."""
    snapshot = audit.build_snapshot()

    assert snapshot["quill.ui.verbosity_chord_editor"] == audit.REACHABLE
    assert snapshot["quill.ui.verbosity_qvp_install"] == audit.REACHABLE


def test_a_classification_has_to_be_one_of_the_reviewed_words() -> None:
    """'dynamic' and 'parked' are reviewed answers; a free-text one would be a
    way to silence the gate without saying anything."""
    for module, status in audit.load_snapshot().items():
        assert status in audit.STATUSES, f"{module}: {status!r} is not a reviewed status"


def test_the_gate_is_on_the_scorecard() -> None:
    """A gate nobody runs is the same shape of problem it exists to catch."""
    from quill.tools.platform_report import GATES

    assert any("surface_reachability_audit" in " ".join(gate.argv) for gate in GATES)
