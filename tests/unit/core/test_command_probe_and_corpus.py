"""The registry's per-command probe, and the Command Key corpus format.

docs/design/command-key.md 5.1 (the runtime half of the catalogue) and 14.1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.command_catalogue.corpus import CorpusError, load_corpus, parse_row
from quill.core.commands import CommandRegistry


def _registry() -> CommandRegistry:
    registry = CommandRegistry()
    registry.register("format.bold", "Bold", lambda: None)
    registry.register("file.save", "Save", lambda: None)
    return registry


# -- set_command_probe ---------------------------------------------------------


def test_a_command_probe_gives_its_reason() -> None:
    registry = _registry()
    registry.set_command_probe("format.bold", lambda: "Bold needs a rich document.")
    assert registry.unavailable_reason("format.bold") == "Bold needs a rich document."
    assert registry.unavailable_reason("file.save") == ""


def test_the_registry_wide_probe_is_asked_first() -> None:
    registry = _registry()
    registry.set_availability_probe(
        lambda command_id: "Safe Mode is on." if command_id == "format.bold" else ""
    )
    registry.set_command_probe("format.bold", lambda: "Bold needs a rich document.")
    assert registry.unavailable_reason("format.bold") == "Safe Mode is on."


def test_the_command_probe_answers_when_the_wide_one_has_nothing() -> None:
    registry = _registry()
    registry.set_availability_probe(lambda _command_id: "")
    registry.set_command_probe("format.bold", lambda: "Bold needs a rich document.")
    assert registry.unavailable_reason("format.bold") == "Bold needs a rich document."


def test_a_probe_that_fails_means_no_reason_known() -> None:
    registry = _registry()

    def broken() -> str:
        raise RuntimeError("probe bug")

    registry.set_command_probe("format.bold", broken)
    assert registry.unavailable_reason("format.bold") == ""


def test_clearing_a_probe_and_unknown_commands() -> None:
    registry = _registry()
    registry.set_command_probe("format.bold", lambda: "No.")
    registry.set_command_probe("format.bold", None)
    registry.set_command_probe("never.registered", None)
    assert registry.unavailable_reason("format.bold") == ""
    registry.set_command_probe("never.registered", lambda: "No.")
    assert registry.unavailable_reason("never.registered") == ""


def test_the_probe_does_not_stop_run() -> None:
    """The probe explains; the run gate blocks. The Command Key asks both."""
    ran: list[str] = []
    registry = CommandRegistry()
    registry.register("format.bold", "Bold", lambda: ran.append("bold"))
    registry.set_command_probe("format.bold", lambda: "No.")
    registry.run("format.bold")
    assert ran == ["bold"]


# -- the corpus format ---------------------------------------------------------


def _row(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "text": "turn it down",
        "app": "radio",
        "expect": {"id": "radio.volume_down"},
    }
    row.update(changes)
    return row


def test_a_plain_row_parses_with_defaults() -> None:
    parsed = parse_row(_row(), line=3)
    assert parsed.expect_id == "radio.volume_down"
    assert parsed.mode == "typed" and parsed.set == "train" and parsed.tier_max == 2
    assert parsed.enabled is None and not parsed.is_refusal and parsed.line == 3


def test_a_refusal_row_with_context() -> None:
    parsed = parse_row(
        _row(
            expect={"refuse": "disabled", "pointer": "radio"},
            enabled=["radio.play_pause"],
            recent=["radio.volume_up"],
            mode="misheard",
            set="held_out",
        )
    )
    assert parsed.is_refusal and parsed.expect_refuse == "disabled" and parsed.pointer == "radio"
    assert parsed.enabled == ("radio.play_pause",) and parsed.recent == ("radio.volume_up",)


def test_enabled_default_means_whatever_the_app_enables() -> None:
    assert parse_row(_row(enabled="default")).enabled is None


@pytest.mark.parametrize(
    "bad",
    [
        {"app": "radio", "expect": {"id": "x"}},
        {"text": "x", "expect": {"id": "x"}},
        _row(mode="shouted"),
        _row(set="tuning"),
        _row(tier_max=7),
        _row(expect={"id": "a", "refuse": "never"}),
        _row(expect={}),
        _row(expect={"refuse": "because"}),
        _row(expect={"id": "a", "args": []}),
        _row(enabled=[1, 2]),
        _row(expect="radio.volume_down"),
    ],
)
def test_malformed_rows_are_refused_with_a_code(bad: dict[str, object]) -> None:
    with pytest.raises(CorpusError) as caught:
        parse_row(bad, line=9)
    assert "QUILL-CORE-COMMANDCORPUS-BAD-ROW" in str(caught.value)


def test_loading_a_file_skips_blanks_and_comments(tmp_path: Path) -> None:
    path = tmp_path / "radio.jsonl"
    path.write_text("// a comment\n\n" + json.dumps(_row()) + "\n", encoding="utf-8")
    rows = load_corpus(path)
    assert len(rows) == 1 and rows[0].line == 3


@pytest.mark.parametrize("line", ["not json", "[1, 2]"])
def test_a_bad_line_names_the_file_and_line(tmp_path: Path, line: str) -> None:
    path = tmp_path / "quill.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(CorpusError, match="quill.jsonl line 1"):
        load_corpus(path)
