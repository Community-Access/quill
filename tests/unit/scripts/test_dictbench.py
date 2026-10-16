"""The dictation benchmark's scoring and its recordings folder, without any audio."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[3]


def _bench():
    spec = importlib.util.spec_from_file_location("dictbench", _REPO / "scripts" / "dictbench.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["dictbench"] = module  # its dataclasses look themselves up
    spec.loader.exec_module(module)
    return module


def test_transcripts_are_read_by_tab_or_space(tmp_path: Path) -> None:
    (tmp_path / "transcripts.txt").write_text(
        "# comments are skipped\n01.wav\t¿Dónde está la biblioteca?\n02.wav Hola, amigos.\n",
        encoding="utf-8",
    )
    assert _bench().read_transcripts(tmp_path) == {
        "01.wav": "¿Dónde está la biblioteca?",
        "02.wav": "Hola, amigos.",
    }


def test_a_bad_line_is_refused_by_number(tmp_path: Path) -> None:
    (tmp_path / "transcripts.txt").write_text("01.wav\tHola\nnot a line\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="line 2"):
        _bench().read_transcripts(tmp_path)


def test_word_errors_ignore_capitals_and_punctuation_and_count_accents_separately() -> None:
    result = _bench().score("01.wav", "¿Dónde está la biblioteca?", "donde esta la biblioteca")
    assert (result.words, result.errors, result.errors_ignoring_accents) == (4, 2, 0)
    assert result.marks_expected == {"?": 1, chr(0xBF): 1}
    assert result.marks_written == {}


def test_the_summary_reports_rates_punctuation_and_speed() -> None:
    bench = _bench()
    first = bench.score("01.wav", "¿Qué tal?", "¿Qué tal?")
    second = bench.score("02.wav", "Hola, amigos.", "hola amigo")
    first.audio_seconds, first.compute_seconds = 2.0, 0.2
    second.audio_seconds, second.compute_seconds = 2.0, 0.6
    overall = bench.summary([first, second])
    assert overall["word_error_rate"] == 0.25
    assert overall["speed_per_thread"] == 0.2
    assert overall["punctuation_found"][chr(0xBF)] == "1/1"
    assert overall["punctuation_found"][","] == "0/1"


def test_a_spoken_command_is_scored_as_recognised_or_not() -> None:
    bench = _bench()
    hit = bench.score("11.wav", "!new paragraph", "New paragraph.")
    miss = bench.score("12.wav", "!scratch that", "Scratch hat.")
    assert hit.command and hit.errors == 0 and hit.reference == "new paragraph"
    assert bench.summary([hit, miss])["commands_recognised"] == "1/2"


def test_list_models_names_every_optional_model(capsys) -> None:
    from quill.core.windows_dictation.model_catalog import CATALOGUE

    assert _bench().main(["--list-models"]) == 0
    out = capsys.readouterr().out
    for model in CATALOGUE:
        assert model.id in out


def test_an_unknown_model_is_refused_by_name() -> None:
    with pytest.raises(SystemExit, match="dragon"):
        _bench().main(["--model", "dragon"])


def test_a_model_that_is_not_downloaded_says_how_to_get_it(tmp_path, monkeypatch) -> None:
    pytest.importorskip("sherpa_onnx")
    from quill.core.windows_dictation import model_store

    monkeypatch.setenv(model_store.DOWNLOADS_VARIABLE, str(tmp_path))
    with pytest.raises(SystemExit, match="--fetch"):
        _bench().load_engine("whisper_small", "en", 1)


# -- the benchmark set (dict.md section 8): datasets, groups, parsing, JSON -------- #


def _folder(tmp_path: Path) -> Path:
    import wave

    folder = tmp_path / "set"
    folder.mkdir()
    lines = {
        "a.wav": "Hello, world.",
        "b.wav": "How are you?",
        "c.wav": "!new paragraph",
        "d.wav": "!scratch that",
    }
    for name in lines:
        with wave.open(str(folder / name), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16_000)
            audio.writeframes(b"\x00\x00" * 1600)
    (folder / "transcripts.txt").write_text(
        "".join(f"{name}\t{text}\n" for name, text in lines.items()), encoding="utf-8"
    )
    (folder / "speakers.tsv").write_text(
        "file\tspeaker\taccent\tgender\tlanguage\tgroup\theldout_moonshine\n"
        "a.wav\tann\tscottish\t\ten\tclean\tyes\n"
        "b.wav\tbob\tindian\t\ten\tclean\tno\n"
        "c.wav\tann\tscottish\t\ten\tnoise 10 dB\tyes\n"
        "d.wav\tbob\tindian\t\ten\tnoise 10 dB\tno\n",
        encoding="utf-8",
    )
    return folder


_HEARD = ("Hello world.", "How are you?", "New paragraph.", "scratch hat")


def _faked(monkeypatch: pytest.MonkeyPatch) -> Any:
    bench = _bench()
    order = iter(_HEARD)
    monkeypatch.setattr(bench, "load_engine", lambda *_a: object())
    monkeypatch.setattr(bench, "recognise", lambda _r, _s: next(order))
    return bench


def test_a_run_reports_groups_parsing_and_punctuation_as_json(tmp_path, monkeypatch) -> None:
    pytest.importorskip("numpy")
    bench = _faked(monkeypatch)
    folder = _folder(tmp_path)
    out = tmp_path / "results.json"
    assert bench.main([str(folder), "--parse", "--group-by", "accent", "--json", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert summary["commands_parsed"] == 1 and summary["commands_typed"] == 1
    assert summary["punctuation"]["marks"]["comma"]["missed"] == 1
    assert summary["normalizer"] and summary["date"]
    assert set(payload["groups"]["results"]) == {"indian", "scottish"}
    assert "never accuracy" in payload["limits"]
    assert "may_be_in_training_data" not in summary  # a plain folder: not known


def test_a_dataset_run_carries_the_contamination_flag(tmp_path, monkeypatch) -> None:
    pytest.importorskip("numpy")
    bench = _faked(monkeypatch)
    monkeypatch.setenv("QUILL_BENCH_AUDIO", str(tmp_path / "cache"))
    folder = _folder(tmp_path)
    prepared = tmp_path / "cache" / "librispeech-test-clean" / "prepared"
    prepared.parent.mkdir(parents=True)
    folder.rename(prepared)
    out = tmp_path / "results.json"
    code = bench.main([
        "--dataset",
        "librispeech-test-clean",
        "--group-by",
        "heldout",
        "--json",
        str(out),
    ])
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["dataset"] == "librispeech-test-clean"
    assert payload["summary"]["may_be_in_training_data"] is True
    assert set(payload["groups"]["results"]) == {"yes", "no"}


def test_a_dataset_that_is_not_prepared_says_how(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BENCH_AUDIO", str(tmp_path / "cache"))
    with pytest.raises(SystemExit, match="fetch_bench_audio.py fleurs-en"):
        _bench().main(["--dataset", "fleurs-en"])


def test_the_aligner_is_never_scored_on_the_set_it_aligned(tmp_path) -> None:
    folder = _folder(tmp_path)
    (folder / "aligner.txt").write_text("whisper\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="aligned this set"):
        _bench().main([str(folder), "--engine", "whisper"])
