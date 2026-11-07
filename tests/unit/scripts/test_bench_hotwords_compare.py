"""D-28 comparisons use raw counts and paired results, never an adoption flag."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def bench():
    scripts = str(Path(__file__).resolve().parents[3] / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    return importlib.import_module("bench_hotwords_compare")


def _runs(bench, before=10, after=15):
    names = [(f"name{i}",) for i in range(20)]
    without = {
        f"{i}.wav": bench.Row(f"name{i}", f"name{i}" if i < before else "missed", 1.0)
        for i in range(20)
    }
    with_hotwords = {
        f"{i}.wav": bench.Row(f"name{i}", f"name{i}" if i < after else "missed", 1.0)
        for i in range(20)
    }
    b1 = {"speech.wav": bench.Row("a real sentence", "a real sentence", 2.0)}
    return names, without, with_hotwords, b1, dict(b1)


def test_exactly_50_percent_and_unchanged_wer_meet_only_the_measurement(bench):
    result = bench.compare(*_runs(bench), real_heldout=True)
    assert result["status"] == "measurement_pass"
    assert result["adopted"] is False
    assert result["names"]["relative_increase"] == 0.5
    assert result["b1"]["wer_no_worse"] is True
    assert result["insufficient_evidence"] == []


def test_just_under_50_percent_is_not_rounded_into_a_pass(bench):
    result = bench.compare(*_runs(bench, after=14), real_heldout=True)
    assert result["status"] == "measurement_fail"


def test_one_more_word_error_fails_even_when_rounded_wer_would_match(bench):
    names, before, after, _, _ = _runs(bench)
    reference = " ".join(["word"] * 2500)
    baseline = {"speech.wav": bench.Row(reference, reference, 2.0)}
    candidate = {"speech.wav": bench.Row(reference, reference + " extra", 2.0)}
    result = bench.compare(names, before, after, baseline, candidate, real_heldout=True)
    assert result["status"] == "measurement_fail"
    assert result["b1"]["errors_with"] == 1


@pytest.mark.parametrize("real_heldout", [True, False])
def test_zero_hit_baseline_is_inconclusive_not_a_divide_by_zero_or_pass(bench, real_heldout):
    result = bench.compare(*_runs(bench, before=0, after=20), real_heldout=real_heldout)
    assert result["status"] == "insufficient_evidence"
    assert result["names"]["relative_increase"] is None


def test_synthetic_speech_cannot_pass(bench):
    assert bench.compare(*_runs(bench), real_heldout=False)["status"] == "insufficient_evidence"


def test_fewer_than_twenty_distinct_names_cannot_pass(bench):
    names, *runs = _runs(bench)
    result = bench.compare(names[:19], *runs, real_heldout=True)
    assert result["status"] == "insufficient_evidence"


def test_a_substring_is_not_a_name_match(bench):
    names = [("ann",)]
    rows = {"one.wav": bench.Row("Ann spoke", "Joanne spoke", 1.0)}
    assert bench._name_hits(rows, names) == 0


def test_a_name_in_another_clips_hallucination_is_not_a_hit(bench):
    rows = {
        "ann.wav": bench.Row("Ann spoke", "wrong", 1.0),
        "bob.wav": bench.Row("Bob spoke", "Ann spoke", 1.0),
    }
    assert bench._name_hits(rows, [("ann",), ("bob",)]) == 0


@pytest.mark.parametrize("problem", ["files", "reference", "duration", "failure", "missing_name"])
def test_unpaired_or_incomplete_evidence_is_an_error(bench, problem):
    names, before, after, b1_before, b1_after = _runs(bench)
    if problem == "files":
        after.pop("0.wav")
    elif problem == "reference":
        after["0.wav"] = bench.Row("changed", "name0", 1.0)
    elif problem == "duration":
        after["0.wav"] = bench.Row("name0", "name0", 2.0)
    elif problem == "failure":
        after["0.wav"] = bench.Row("name0", "name0", 1.0, "engine failed")
    else:
        names.append(("not-in-reference",))
    with pytest.raises(ValueError):
        bench.compare(names, before, after, b1_before, b1_after, real_heldout=True)


def _report(path, rows):
    path.write_text(json.dumps({"files": rows}), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "change",
    [
        {"audio_seconds": -1},
        {"audio_seconds": True},
        {"audio_seconds": float("nan")},
        {"audio_seconds": 10**400},
        {"reference": ""},
        {"heard": None},
    ],
)
def test_invalid_report_rows_fail_explicitly(bench, tmp_path, change):
    row = {"name": "a.wav", "reference": "hello", "heard": "hello", "audio_seconds": 1}
    path = _report(tmp_path / "run.json", [row | change])
    with pytest.raises(ValueError):
        bench.load_report(path)


def _cli_inputs(bench, tmp_path):
    names, *runs = _runs(bench)
    vocabulary = tmp_path / "names.txt"
    vocabulary.write_text("\n".join(name[0] for name in names), encoding="utf-8")
    argv = ["--names", str(vocabulary)]
    for option, rows in zip(
        ("names-without", "names-with", "b1-without", "b1-with"), runs, strict=True
    ):
        path = _report(
            tmp_path / f"{option}.json",
            [
                {
                    "name": name,
                    "reference": row.reference,
                    "heard": row.heard,
                    "audio_seconds": row.audio_seconds,
                    "failed": row.failed,
                    # The comparison must not trust a cached or rounded score.
                    "errors": 999,
                }
                for name, row in rows.items()
            ],
        )
        argv.extend([f"--{option}", str(path)])
    return argv


@pytest.mark.parametrize("real_heldout", [True, False])
def test_cli_writes_aggregate_evidence_and_hashes_without_transcripts(
    bench, tmp_path, real_heldout, capsys
):
    argv = _cli_inputs(bench, tmp_path)
    output = tmp_path / "result.json"
    argv.extend(["--out", str(output)])
    if real_heldout:
        argv.append("--real-heldout")
    assert bench.main(argv) == (0 if real_heldout else 1)
    text = output.read_text(encoding="utf-8")
    result = json.loads(text)
    assert result["adopted"] is False
    assert result["b1"]["errors_without"] == 0
    assert len(result["input_sha256"]) == 5
    assert all(len(value) == 64 for value in result["input_sha256"].values())
    assert "name0" not in text and "a real sentence" not in text
    assert "name0" not in capsys.readouterr().out


def test_cli_cannot_overwrite_an_input(bench, tmp_path):
    argv = _cli_inputs(bench, tmp_path)
    original = (tmp_path / "names.txt").read_bytes()
    with pytest.raises(SystemExit) as error:
        bench.main([*argv, "--out", str(tmp_path / "names.txt"), "--real-heldout"])
    assert error.value.code == 2
    assert (tmp_path / "names.txt").read_bytes() == original


def test_bad_input_does_not_create_a_success_shaped_report(bench, tmp_path, capsys):
    argv = _cli_inputs(bench, tmp_path)
    (tmp_path / "names-with.json").write_text('{"files": []}', encoding="utf-8")
    output = tmp_path / "result.json"
    with pytest.raises(SystemExit) as error:
        bench.main([*argv, "--out", str(output)])
    assert error.value.code == 2
    assert not output.exists()
    assert "must not be empty" in capsys.readouterr().err


def test_invalid_input_explicitly_reports_that_previous_output_is_stale(bench, tmp_path, capsys):
    argv = _cli_inputs(bench, tmp_path)
    output = tmp_path / "result.json"
    assert bench.main([*argv, "--out", str(output), "--real-heldout"]) == 0
    previous = output.read_bytes()
    (tmp_path / "names-with.json").write_text('{"files": []}', encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        bench.main([*argv, "--out", str(output), "--real-heldout"])
    assert error.value.code == 2
    assert output.read_bytes() == previous
    assert "previous report is unchanged" in capsys.readouterr().err


def test_empty_name_tokens_are_rejected_even_for_direct_comparison(bench):
    _, *runs = _runs(bench)
    with pytest.raises(ValueError, match="nonempty"):
        bench.compare([()], *runs, real_heldout=True)
