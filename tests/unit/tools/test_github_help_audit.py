"""GATE-GITHUB-HELP: F1 help on every GitHub window, control, node, row and option.

GitHub PRD section 7 and D10. The inventory is at zero ``missing`` and stays
there: a new control in the Workbench or any ``quill/ui/github_*`` window
fails until it has inline help, and a new node, action, menu row or option
fails until the catalogue (:mod:`quill.core.github.workbench_help`) has words
for it.
"""

from __future__ import annotations

from quill.core.github import workbench_help
from quill.tools import github_help_audit
from quill.tools.help_audit import MISSING, build_snapshot


def test_every_github_window_title_has_a_purpose() -> None:
    _sites, violations = github_help_audit.scan()
    assert violations == [], "\n".join(f"{v.key}:{v.line}: {v.title!r}" for v in violations)


def test_the_committed_inventory_matches_and_nothing_is_missing() -> None:
    sites, _violations = github_help_audit.scan()
    committed = github_help_audit.load_snapshot()
    live = build_snapshot(sites, committed)
    assert live == committed, "run: python -m quill.tools.github_help_audit --write"
    assert [key for key, status in live.items() if status == MISSING] == []


def test_the_catalogue_has_no_gaps() -> None:
    assert github_help_audit.catalogue_gaps() == []


def test_the_gate_is_rostered_in_the_platform_report() -> None:
    from quill.tools import platform_report

    commands = [" ".join(gate.argv) for gate in platform_report.GATES]
    assert any("quill.tools.github_help_audit" in command for command in commands)


def test_every_glossary_word_and_task_is_plain_and_ends_a_sentence() -> None:
    for term, text in workbench_help.GLOSSARY.items():
        assert text.endswith("."), term
        assert "tick" not in text.lower(), term  # check, never tick
    for _id, title, steps, _target in workbench_help.TASKS:
        assert title and steps.endswith("."), title


def test_search_help_finds_places_commands_words_and_tasks() -> None:
    hits = workbench_help.search_help(
        "failed",
        {"github.workbench.rerun_failed": ("Re-run Failed Jobs", "Ctrl+Shift+F5")},
        {"repository:runs": "Runs"},
    )
    kinds = {hit.kind for hit in hits}
    assert {"command", "node", "task"} <= kinds
    command = next(hit for hit in hits if hit.kind == "command")
    assert command.spoken() == "Command: Re-run Failed Jobs, Ctrl+Shift+F5"
