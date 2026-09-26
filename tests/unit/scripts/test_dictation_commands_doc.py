"""The published dictation command reference matches the table dictation reads."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]


def _script():
    spec = importlib.util.spec_from_file_location(
        "build_dictation_commands", _REPO / "scripts" / "build_dictation_commands.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_both_published_copies_are_current() -> None:
    stale = _script().stale()
    assert stale == [], "run: python scripts/build_dictation_commands.py"
