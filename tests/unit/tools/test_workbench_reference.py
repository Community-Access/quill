"""The generated GitHub Workbench tables in docs/github/workbench-reference.md cannot drift."""

from __future__ import annotations

from quill.tools import build_workbench_reference as ref


def test_the_committed_reference_matches_the_tables() -> None:
    current = ref.OUTPUT_PATH.read_text(encoding="utf-8")
    assert ref.render(current) == current, (
        "Regenerate with: python -m quill.tools.build_workbench_reference --write"
    )


def test_every_preference_and_key_is_in_it() -> None:
    from quill.core.github.workbench_help import PREF_HELP
    from quill.core.github.workbench_window_menu import WORKBENCH_KEYS

    text = ref.OUTPUT_PATH.read_text(encoding="utf-8")
    for name in PREF_HELP:
        assert f"`{name}`" in text, name
    for key in WORKBENCH_KEYS.values():
        assert f"| {key} |" in text, key
