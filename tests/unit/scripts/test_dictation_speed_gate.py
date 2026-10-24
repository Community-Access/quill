"""The dictation benchmark gate (scripts/dictation_speed_gate.py): the committed
real recordings, the advice's budget across many computers, and -- with the
models present -- each recommendable model's speed and errors on real speech."""

from __future__ import annotations

import importlib
import os
import sys
import wave
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _gate():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("dictation_speed_gate")


@pytest.mark.parametrize("language", ["en", "es"])
def test_the_committed_recordings_are_real_people_with_their_text(language: str) -> None:
    folder = _gate().CORPUS / language
    lines = (folder / "transcripts.txt").read_text(encoding="utf-8").splitlines()
    names = [line.split("\t", 1)[0] for line in lines]
    credits = (folder / "ATTRIBUTION.txt").read_text(encoding="utf-8")
    assert len(names) >= 4
    assert sorted(names) == sorted(p.name for p in folder.glob("*.wav"))
    for name in names:
        with wave.open(str(folder / name)) as audio:  # what dictbench reads
            assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) == (
                16_000,
                1,
                2,
            )
        assert f"{name}: read by " in credits and "for LibriVox project" in credits
    assert (folder.parent / "SOURCE.md").is_file()


def test_every_recommendation_keeps_inside_its_budget() -> None:
    assert _gate().budget_problems() == []


def test_every_recommendable_model_has_measured_figures() -> None:
    from quill.core.windows_dictation.model_types import MEASURED

    found = _gate().recommendable()
    assert {"moonshine", "parakeet", "parakeet_unified"} <= set(found)
    for model_id, languages in found.items():
        assert MEASURED[model_id].word_errors is not None
        if "es" in languages:
            assert MEASURED[model_id].word_errors_es is not None, model_id


def test_a_catalogue_cost_that_breaks_the_budget_is_caught(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _gate()
    real = gate.costs

    def inflated(language: str) -> dict[str, float]:
        return {model: cost * 10 for model, cost in real(language).items()}

    monkeypatch.setattr(gate, "costs", inflated)
    assert any("over its" in problem for problem in gate.budget_problems())


def test_a_model_that_got_slower_or_worse_fails_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _gate()

    def measured(model_id: str, language: str):
        if model_id == "moonshine":
            return gate.Measurement(model_id, language, 0.05, 6.0)
        if model_id == "parakeet_unified":  # three times its cost, and far worse
            return gate.Measurement(model_id, language, 0.05 * 3.8 * 3, 40.0)
        cost = gate.costs(language)[model_id]
        return gate.Measurement(model_id, language, 0.05 * cost, 5.0)

    monkeypatch.setattr(gate, "_measure", measured)
    problems = gate.run_problems()
    assert any(p.startswith("parakeet_unified (en) ran at") for p in problems)
    assert any(p.startswith("parakeet_unified (en) got 40.0%") for p in problems)
    assert not any(p.startswith("parakeet (") for p in problems)


@pytest.mark.skipif(
    os.environ.get("QUILL_DICTATION_BENCH") != "1",
    reason="needs sherpa-onnx and the models: the weekly dictation-benchmark workflow",
)
def test_the_recommendable_models_keep_their_numbers_on_real_speech() -> None:
    report: list[str] = []
    problems = _gate().run_problems(report)
    print("\n".join(report))
    assert problems == []


def test_report_only_warns_about_the_models_but_fails_on_the_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The weekly run is report-only (2026-10-24): a model's figures become
    warnings and a job summary, while the advice's own budget still fails."""
    gate = _gate()
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(
        gate,
        "run_problems",
        lambda report: (report.append("parakeet (en): 6.3 x tiny"), ["slow"])[1],
    )
    monkeypatch.setattr(gate, "budget_problems", lambda: [])
    assert gate.main(["--run", "--report-only"]) == 0
    assert "::warning::slow" in capsys.readouterr().out
    assert "Reported, not failed" in summary.read_text(encoding="utf-8")
    assert gate.main(["--run"]) == 1  # without the flag, the same figures fail
    monkeypatch.setattr(gate, "budget_problems", lambda: ["over its budget"])
    assert gate.main(["--run", "--report-only"]) == 1
