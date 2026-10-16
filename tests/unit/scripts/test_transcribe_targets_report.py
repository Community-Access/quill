"""B-2's incomplete-report correctness, without a real window.

The tested-programs harness (``tests/integration/test_transcribe_targets.py``,
D-4) types into real programs and so never runs here. Its scoring does: the
harness's ``_dictate`` is driven against a fake field and a fake typing path
that drops keys, and the count of reports that agreed with what arrived --
and of the ones that did not -- is checked. Nothing is typed anywhere.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_HARNESS = (
    Path(__file__).resolve().parents[3] / "tests" / "integration" / "test_transcribe_targets.py"
)


def _harness() -> Any:
    spec = importlib.util.spec_from_file_location("transcribe_targets_harness", _HARNESS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["transcribe_targets_harness"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("reported", "exact", "verdict"),
    [
        (False, True, "agreed"),
        (True, False, "agreed"),
        (True, True, "false_alarm"),
        (False, False, "silent_miss"),
    ],
)
def test_each_report_is_classified(reported: bool, exact: bool, verdict: str) -> None:
    assert _harness().report_agreement(reported, exact) == verdict


def test_the_harness_counts_reports_against_what_arrived(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _harness()
    from quill.ui.windows_dictation_external import ExternalDocument

    field = {"text": ""}
    phrases = list(harness.PHRASES)

    def typing(text: str, *_hush: Any) -> bool:
        if text == phrases[1]:  # keys dropped, and QUILL is told (reports it)
            field["text"] += text[:5]
            return False
        if text == phrases[2]:  # keys dropped, and nobody notices: a silent miss
            field["text"] += text[:-3]
            return True
        if text == phrases[3]:  # it all arrived, but the report said otherwise
            field["text"] += text
            return False
        field["text"] += text
        return True

    monkeypatch.setattr(harness, "_SETTLE_S", 0.01)
    monkeypatch.setattr(harness, "_tick", lambda: 0)
    monkeypatch.setattr(harness, "_read_field", lambda _s: (field["text"], "TextPattern"))
    monkeypatch.setattr(
        harness,
        "_external_document",
        lambda _s: ExternalDocument(
            problem=lambda: "", where=lambda: ("fake", 1, "edit"), type_text=typing
        ),
    )
    row = harness._dictate(SimpleNamespace(guard=lambda: "", own_tick=0))
    assert row["phrases_sent"] == len(phrases)
    assert row["phrases_exact"] == len(phrases) - 2
    assert row["report_agreement"] == {
        "agreed": len(phrases) - 2,
        "false_alarm": 1,
        "silent_miss": 1,
    }
    assert any("reported it incomplete" in m["arrived"] for m in row["mismatches"])
