from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.core.commands import Command
from quill.core.palette import (
    PaletteUsage,
    load_palette_usage,
    rank_commands,
    record_palette_usage,
    save_palette_usage,
)


def _command(command_id: str, title: str) -> Command:
    return Command(
        id=command_id,
        title=title,
        keybinding=None,
        handler=lambda: None,
        feature_id="core.app",
    )


def test_rank_commands_prefers_prefix_matches() -> None:
    commands = [
        _command("file.open", "Open File"),
        _command("file.save", "Save File"),
        _command("edit.find", "Find"),
    ]

    ranked = rank_commands(commands, "op", {})

    assert [item.id for item in ranked] == ["file.open"]


def test_rank_commands_uses_frequency_and_recency_tiebreakers() -> None:
    commands = [
        _command("edit.find", "Find"),
        _command("edit.find_next", "Find Next"),
    ]
    usage = {
        "edit.find": PaletteUsage(count=10, last_used_epoch=10),
        "edit.find_next": PaletteUsage(count=10, last_used_epoch=20),
    }

    ranked = rank_commands(commands, "fi", usage)

    assert [item.id for item in ranked] == ["edit.find_next", "edit.find"]


def test_record_palette_usage_increments_count() -> None:
    usage = {"edit.find": PaletteUsage(count=2, last_used_epoch=100)}

    updated = record_palette_usage(
        usage,
        "edit.find",
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert updated["edit.find"].count == 3
    assert updated["edit.find"].last_used_epoch == int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())


def test_palette_usage_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "palette-usage.json"
    import quill.core.palette as palette_module

    monkeypatch.setattr(palette_module, "palette_usage_path", lambda: target)
    usage = {"file.open": PaletteUsage(count=5, last_used_epoch=123)}

    save_palette_usage(usage)
    loaded = load_palette_usage()

    assert loaded == usage


def test_rank_commands_multi_term_matches_in_any_order() -> None:
    commands = [
        _command("file.open_url", "Open From URL..."),
        _command("file.open", "Open File"),
        _command("edit.find", "Find"),
    ]

    assert [item.id for item in rank_commands(commands, "url open", {})] == ["file.open_url"]
    assert [item.id for item in rank_commands(commands, "open url", {})] == ["file.open_url"]


def test_rank_commands_matches_intent_aliases() -> None:
    commands = [
        _command("app.preferences", "Preferences..."),
        _command("file.open", "Open File"),
    ]

    ranked = rank_commands(commands, "settings", {})

    assert [item.id for item in ranked] == ["app.preferences"]


def test_rank_commands_matches_keybinding_text() -> None:
    commands = [
        Command(
            id="file.open",
            title="Open",
            keybinding="Ctrl+O",
            handler=lambda: None,
            feature_id="core.file",
        ),
        _command("edit.find", "Find"),
    ]

    ranked = rank_commands(commands, "ctrl+o", {})

    assert [item.id for item in ranked] == ["file.open"]


def test_rank_commands_id_prefix_limits_to_command_ids() -> None:
    commands = [
        _command("file.open", "Open File"),
        _command("edit.find", "Search"),
    ]

    ranked = rank_commands(commands, ":find", {})

    assert [item.id for item in ranked] == ["edit.find"]


def test_rank_commands_bound_prefix_limits_to_bound_commands() -> None:
    commands = [
        Command(
            id="file.open",
            title="Open",
            keybinding="Ctrl+O",
            handler=lambda: None,
            feature_id="core.file",
        ),
        Command(
            id="file.save",
            title="Save",
            keybinding=None,
            handler=lambda: None,
            feature_id="core.file",
        ),
    ]

    ranked = rank_commands(commands, "?", {})

    assert [item.id for item in ranked] == ["file.open"]


def test_rank_commands_recent_prefix_prioritizes_usage() -> None:
    commands = [
        _command("file.open", "Open"),
        _command("file.save", "Save"),
    ]
    usage = {
        "file.save": PaletteUsage(count=5, last_used_epoch=20),
        "file.open": PaletteUsage(count=2, last_used_epoch=10),
    }

    ranked = rank_commands(commands, "~", usage)

    assert [item.id for item in ranked] == ["file.save", "file.open"]
