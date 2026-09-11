"""GATE-LITE-COVER holds: the command-coverage ratchet only ever tightens.

The gate itself is :mod:`quill.tools.lite_command_coverage`; this is the test
that runs it in CI, plus checks on the scanner underneath it, because a gate
whose detection is wrong is worse than no gate -- it reports coverage that is
not there and everybody stops looking.

The failure it was written for: ``cmd_start_extend_selection`` shipped with a
test that called it and asserted nothing about what happened next, while extend
mode had never once worked from the keyboard. "There is a test" and "the
behaviour is checked" are different claims, and only the first one is
mechanical. This gate makes the first one mandatory so a human is at least
looking at the second.
"""

from __future__ import annotations

import json

from quill.tools.lite_command_coverage import (
    SNAPSHOT_PATH,
    STATUSES,
    build_snapshot,
    called_handlers,
    command_handlers,
    load_snapshot,
    violations,
)


def test_the_snapshot_matches_the_tree() -> None:
    """The gate, as CI runs it.

    A new command, a deleted test, or a handler that has gained a test all land
    here. The last of those is a *good* change and still fails: regenerate with
    ``python -m quill.tools.lite_command_coverage --write`` and commit the diff.
    """
    assert violations() == []


def test_the_snapshot_covers_every_command_and_nothing_else() -> None:
    recorded = load_snapshot()
    assert set(recorded) == set(command_handlers())
    assert recorded, "an empty snapshot would make the gate vacuous"


def test_every_recorded_status_is_one_of_the_two() -> None:
    unknown = {
        handler: status for handler, status in load_snapshot().items() if status not in STATUSES
    }
    assert unknown == {}


def test_the_snapshot_on_disk_is_what_the_writer_would_write() -> None:
    """Formatting drift is a diff nobody reads. Pin it."""
    expected = json.dumps(build_snapshot(), indent=2, sort_keys=True) + "\n"
    assert SNAPSHOT_PATH.read_text(encoding="utf-8") == expected


def test_the_scanner_counts_a_call_and_not_a_mention(tmp_path) -> None:
    """The distinction the whole gate rests on.

    A test that lists handler names in a table -- exactly the shape of test that
    let F8 through -- must not read as coverage. Only an actual call does.
    """
    tests = tmp_path / "tests" / "unit" / "apps"
    tests.mkdir(parents=True)
    (tests / "test_sample.py").write_text(
        "\n".join([
            "NAMES = ['cmd_only_mentioned']",
            "def test_one(win):",
            "    win.cmd_really_called()",
            "    assert hasattr(win, 'cmd_only_attribute')",
            "    getattr(win, 'cmd_by_string')()",
            "",
        ]),
        encoding="utf-8",
    )
    found = called_handlers(tmp_path)
    assert "cmd_really_called" in found
    assert "cmd_only_mentioned" not in found
    assert "cmd_only_attribute" not in found
    # A getattr call is a string, not an attribute access, and the scanner is
    # honest about not seeing it. Recorded here so the limit is known rather
    # than discovered: a test that drives handlers by name reads as no coverage.
    assert "cmd_by_string" not in found


def test_a_file_that_does_not_parse_is_skipped_rather_than_fatal(tmp_path) -> None:
    tests = tmp_path / "tests" / "unit" / "apps"
    tests.mkdir(parents=True)
    (tests / "test_broken.py").write_text("def (", encoding="utf-8")
    (tests / "test_fine.py").write_text("def t(w):\n    w.cmd_ok()\n", encoding="utf-8")
    assert called_handlers(tmp_path) == {"cmd_ok"}


def test_a_new_command_fails_until_it_is_classified() -> None:
    recorded = dict(load_snapshot())
    removed = sorted(recorded)[0]
    del recorded[removed]
    problems = violations(recorded)
    assert any(removed in problem and "new command" in problem for problem in problems)


def test_losing_a_test_fails_the_build() -> None:
    """The half that makes it a ratchet rather than a checklist."""
    recorded = dict(load_snapshot())
    shape_only = next(h for h, status in recorded.items() if status == "shape_only")
    recorded[shape_only] = "covered"
    problems = violations(recorded)
    assert any(shape_only in problem and "no test calls it" in problem for problem in problems)


def test_gaining_a_test_asks_for_a_regenerate() -> None:
    recorded = dict(load_snapshot())
    covered = next(h for h, status in recorded.items() if status == "covered")
    recorded[covered] = "shape_only"
    problems = violations(recorded)
    assert any(covered in problem and "--write" in problem for problem in problems)


def test_a_stale_entry_is_reported() -> None:
    recorded = dict(load_snapshot())
    recorded["cmd_deleted_last_release"] = "covered"
    problems = violations(recorded)
    assert any("cmd_deleted_last_release" in problem for problem in problems)


def test_the_debt_is_visible_rather_than_averaged() -> None:
    """A count, asserted, so shrinking it is a deliberate act.

    Not a percentage: a ratio moves when the denominator moves, so adding
    commands could make the number look better while the untested list grew.
    """
    recorded = load_snapshot()
    shape_only = sorted(h for h, status in recorded.items() if status == "shape_only")
    assert len(shape_only) <= 68, (
        "the shape-only list may only shrink; if you removed a test, put it back, "
        f"and if you added commands, cover them. Currently: {shape_only}"
    )
