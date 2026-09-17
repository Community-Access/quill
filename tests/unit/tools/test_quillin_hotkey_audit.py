"""GATE-QHK: a Quillin may not claim a chord the core keymap already owns.

Two things claiming one chord means **one of them silently never fires**, and
which one depends on binding order -- not a thing anybody can reason about from
the outside. The user presses the key, gets the wrong verb or none, and neither
the menu nor the Keyboard Shortcuts sheet mentions the extension's claim.

The first run found all three bundled hotkeys colliding (bad.md 7.4).
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.tools.quillin_hotkey_audit import audit


def _quillin(root: Path, name: str, hotkeys: list[dict[str, str]]) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps({"id": f"test.{name}", "contributes": {"hotkeys": hotkeys}}),
        encoding="utf-8",
    )
    return directory


def test_the_bundled_quillins_claim_nothing_the_core_owns() -> None:
    """The gate over the shipped set, which is the one that matters."""
    bundled = Path(__file__).resolve().parents[3] / "quill" / "quillins_bundled"
    directories = [child for child in bundled.iterdir() if child.is_dir()]

    assert audit(directories) == []


def test_a_chord_the_core_binds_is_reported(tmp_path: Path) -> None:
    directory = _quillin(tmp_path, "greedy", [{"command": "ext.x.bold", "binding": "Ctrl+B"}])

    found = audit([directory])

    assert len(found) == 1
    assert found[0].binding == "Ctrl+B"
    assert "moves, not the core" in str(found[0])


def test_modifier_order_does_not_hide_a_collision(tmp_path: Path) -> None:
    """Ctrl+Shift+B and Shift+Ctrl+B are one key, and a gate that compared the
    strings would be one somebody routes around by accident."""
    directory = _quillin(
        tmp_path, "reordered", [{"command": "ext.x.mark", "binding": "Shift+Ctrl+B"}]
    )

    found = audit([directory])

    assert len(found) == 1
    assert found[0].core_command == "navigate.set_numbered_bookmark"


def test_a_chord_nobody_owns_is_allowed(tmp_path: Path) -> None:
    """The gate is about collisions, not about forbidding extension keys."""
    directory = _quillin(
        tmp_path, "polite", [{"command": "ext.x.thing", "binding": "Ctrl+Shift+Grave, Z"}]
    )

    assert audit([directory]) == []


def test_a_quillin_with_no_hotkeys_is_fine(tmp_path: Path) -> None:
    assert audit([_quillin(tmp_path, "quiet", [])]) == []


def test_a_broken_manifest_is_left_to_the_lint_gate(tmp_path: Path) -> None:
    """Reporting it here too would mean two gates failing for one fault, and the
    one with the better message is quillin_lint."""
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "manifest.json").write_text("{not json", encoding="utf-8")

    assert audit([directory]) == []
