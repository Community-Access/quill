"""GATE-CATREF: docs/command-catalogue.md is generated and cannot drift."""

from __future__ import annotations

from quill.core.command_catalogue import rows_for_app
from quill.tools import build_command_catalogue_reference as ref


def test_the_reference_matches_the_catalogue() -> None:
    assert ref.main(["--check"]) == 0, (
        "run python -m quill.tools.build_command_catalogue_reference --write"
    )


def test_every_offered_command_and_example_is_on_the_page() -> None:
    text = ref.render()
    for app in ("quill", "lite", "radio"):
        for spec in rows_for_app(app):
            assert spec.title in text, spec.id
            for example in spec.examples if spec.offered else ():
                assert f'"{example}"' in text, (spec.id, example)


def test_a_confirm_command_says_it_asks() -> None:
    assert (
        "**Close Document (Ctrl+W).** Close this document. It asks before it does it."
        in ref.render()
    )


def test_keys_come_from_each_apps_own_table() -> None:
    text = ref.render()
    assert "**Volume Up (Ctrl+Up).**" in text
    assert "**Save (Ctrl+S).**" in text
