"""B-8's machine run: the proposals it makes from measurements, never edits."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _run() -> Any:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("bench_machine_run")


def test_ram_tiers_are_the_smallest_machine_that_fits() -> None:
    tier = _run().ram_tier
    assert tier(210) == "4 GB"
    assert tier(844) == "8 GB"
    assert tier(2_100) == "16 GB"
    assert tier(None) == "not measured"


def test_cost_factors_are_proposed_against_moonshine_on_the_same_set() -> None:
    rows = [
        {"engine": "moonshine", "set": "en", "speed_per_thread": 0.05, "peak_memory_mb": 210},
        {"engine": "moonshine", "set": "es", "speed_per_thread": 0.10, "peak_memory_mb": 220},
        {"engine": "parakeet", "set": "en", "speed_per_thread": 0.34, "peak_memory_mb": 805},
        {"engine": "parakeet", "set": "es", "speed_per_thread": 0.70, "peak_memory_mb": 900},
    ]
    proposed = _run().proposals(rows)
    assert proposed["moonshine"]["cost_factor"] == 1.0
    assert proposed["parakeet"]["cost_factor"] == 7.0
    assert proposed["parakeet"]["ram_tier"] == "8 GB"


def test_the_table_has_a_row_per_model_and_set() -> None:
    rows = [
        {
            "engine": "moonshine",
            "set": "en",
            "mode": "files",
            "word_error_rate": 0.034,
            "punctuation": {"marks": {"period": {"f1": 0.9}, "comma": {"f1": 0.5}}},
            "speed_per_thread": 0.05,
            "peak_memory_mb": 210,
            "startup_seconds": 2.2,
        }
    ]
    assert "| moonshine | en | files | 3.4% | 0.9 | 0.5 | 0.05 |" in _run().table(rows)
