"""Tests for the footprint_live parent orchestration (parse + render)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "footprint_live", _ROOT / "scripts" / "footprint_live.py"
)
assert _spec and _spec.loader
footprint_live = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(footprint_live)


def test_parse_child_output_valid_json() -> None:
    out = '{"engine_id": "x", "display_name": "X", "available": true, "cold_start_s": 1.2}'
    t = footprint_live.parse_child_output(out, "x")
    assert t.available is True and t.cold_start_s == 1.2


def test_parse_child_output_ignores_noise_before_json() -> None:
    out = 'some warning line\n{"engine_id": "y", "display_name": "Y", "available": false}'
    t = footprint_live.parse_child_output(out, "y")
    assert t.engine_id == "y" and t.available is False


def test_parse_child_output_no_json() -> None:
    t = footprint_live.parse_child_output("just noise, no json", "z")
    assert t.available is False and "no JSON" in t.note


def test_parse_child_output_bad_json() -> None:
    t = footprint_live.parse_child_output("{not valid json", "z")
    assert t.available is False and "not valid JSON" in t.note


def test_render_markdown_empty() -> None:
    assert "No speech engines" in footprint_live.render_markdown([])


def test_render_markdown_table() -> None:
    from quill.core.footprint.live_probe import EngineTiming

    md = footprint_live.render_markdown([
        EngineTiming(engine_id="e", display_name="Eng", available=True, note="")
    ])
    assert "| Eng |" in md and "Cold start" in md
