"""The dictation benchmark's scoring and its recordings folder, without any audio."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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
