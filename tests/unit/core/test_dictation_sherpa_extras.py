"""The shared layer's catalogue fields and its extras (dict.md D-26 to D-29).

Keyword spotting, hotwords, punctuation and speaker labels are built but not
switched on until measured; everything here runs on fakes and downloads nothing.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.windows_dictation import hotwords, kws_keywords, model_loader, post_passes
from quill.core.windows_dictation.model_catalog import CATALOGUE, downloadable
from quill.core.windows_dictation.model_types import (
    HOTWORD_MODELS,
    TASKS,
    estimated_peak_mb,
    ram_tier_budget_mb,
    ram_tier_for,
)
from quill.core.windows_dictation.parser import RecognizedPhrase, words_from_text

# -- D-26: the catalogue's new fields -------------------------------------------


def test_every_model_has_a_ram_tier_tasks_a_source_and_a_licence() -> None:
    for model in CATALOGUE:
        assert model.ram_tier in {4, 8, 16}, model.id
        assert model.tasks <= set(TASKS) and "transcribe" in model.tasks, model.id
        assert model.source_url.startswith(f"https://huggingface.co/{model.repo}/tree/"), model.id
        assert model.licence, model.id
    assert downloadable("nemotron").streaming
    assert not any(model.streaming for model in CATALOGUE if model.id != "nemotron")


def test_memory_tiers_follow_the_measurements() -> None:
    assert downloadable("moonshine_base").ram_tier == 4  # 365 MB measured
    assert downloadable("parakeet").ram_tier == 8  # 805 MB measured
    assert downloadable("whisper_medium").ram_tier == 16  # 2.1 GB measured
    assert ram_tier_for(600) == 4 and ram_tier_for(601) == 8 and ram_tier_for(9999) == 16
    assert ram_tier_budget_mb(3.8) == 600 and ram_tier_budget_mb(7.9) == 1000
    assert ram_tier_budget_mb(31.0) == 2500
    assert estimated_peak_mb(100_000_000) == 300  # small models: weights plus working memory


def test_only_multilingual_whisper_translates_and_nothing_has_hotwords_yet() -> None:
    translators = {model.id for model in CATALOGUE if "translate" in model.tasks}
    assert translators
    assert all(
        downloadable(i).kind == "whisper" and "es" in downloadable(i).languages for i in translators
    )
    assert not HOTWORD_MODELS
    assert not any("hotwords" in model.tasks for model in CATALOGUE)


class _Sherpa:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        outer = self

        class Offline:
            @staticmethod
            def from_whisper(**kwargs):
                outer.calls.append(("whisper", kwargs))
                return "whisper"

            @staticmethod
            def from_transducer(**kwargs):
                outer.calls.append(("transducer", kwargs))
                return "transducer"

        class Online:
            @staticmethod
            def from_transducer(**kwargs):
                outer.calls.append(("online", kwargs))
                return "online"

        self.OfflineRecognizer = Offline
        self.OnlineRecognizer = Online


def test_build_passes_the_task_to_whisper_and_refuses_it_elsewhere(tmp_path) -> None:
    sherpa = _Sherpa()
    model_loader.build(downloadable("whisper_small"), tmp_path, sherpa, task="translate")
    assert sherpa.calls[-1][1]["task"] == "translate"
    with pytest.raises(model_loader.SherpaUnsupportedError, match="cannot translate"):
        model_loader.build(downloadable("parakeet"), tmp_path, sherpa, task="translate")


def test_build_passes_decoder_options_to_transducers(tmp_path) -> None:
    sherpa = _Sherpa()
    options = {"decoding_method": "modified_beam_search", "hotwords_file": "h.txt"}
    model_loader.build(downloadable("parakeet"), tmp_path, sherpa, decoder_options=options)
    assert sherpa.calls[-1][1]["hotwords_file"] == "h.txt"
    model_loader.online(downloadable("nemotron"), tmp_path, sherpa)
    assert sherpa.calls[-1][1]["decoding_method"] == "greedy_search"  # unchanged by default


# -- D-27: keyword spotting -------------------------------------------------------


def test_keywords_are_the_command_word_hey_and_the_wake_and_stop_phrases() -> None:
    phrases = kws_keywords.keyword_phrases("QUILL", "hey quill, start", "stop dictating")
    assert phrases == ["QUILL", "HEY QUILL", "HEY QUILL START", "STOP DICTATING"]
    assert kws_keywords.keyword_phrases("Quill Pen") == ["QUILL PEN"]  # no "hey" for two words


def test_keyword_lines_carry_boost_threshold_and_the_phrase() -> None:
    lines = kws_keywords.keyword_lines(
        ["QUILL"], lambda texts: [["▁QUI", "LL"] for _ in texts], boost=2.0, threshold=0.3
    )
    assert lines == ["▁QUI LL :2 #0.3 @QUILL"]


class _Spotter:
    def __init__(self, hits: list[str]) -> None:
        self._hits = hits
        self.resets = 0

    def create_stream(self):
        return SimpleNamespace(accept_waveform=lambda rate, samples: None, ready=[True])

    def is_ready(self, stream):
        return stream.ready.pop() if stream.ready else False

    def decode_stream(self, stream):
        stream.ready.append(False)

    def get_result(self, stream):
        return self._hits.pop(0) if self._hits else ""

    def reset_stream(self, stream):
        self.resets += 1


def test_the_gate_reports_a_hit_once_per_phrase() -> None:
    spotter = _Spotter(["QUILL"])
    gate = kws_keywords.KeywordGate(spotter)
    gate.accept([0.0] * 512)
    assert gate.take() is True and spotter.resets == 1
    assert gate.take() is False


def test_the_gate_is_off_until_adopted(tmp_path) -> None:
    prefs = SimpleNamespace(command_prefix="QUILL", wake_phrase="", stop_phrase="")
    assert kws_keywords.KWS_ADOPTED is False
    assert kws_keywords.keyword_gate_for(prefs, folder=tmp_path) is None
    built = kws_keywords.keyword_gate_for(
        prefs,
        sherpa_onnx=SimpleNamespace(
            text2token=lambda texts, **_k: [[t] for t in texts],
            KeywordSpotter=lambda **_k: _Spotter([]),
        ),
        folder=tmp_path,
        ready=lambda _folder: True,
    )
    assert isinstance(built, kws_keywords.KeywordGate)
    assert "@HEY QUILL" in (tmp_path / "keywords.txt").read_text(encoding="utf-8")
    no_word = SimpleNamespace(command_prefix="", wake_phrase="", stop_phrase="")
    assert kws_keywords.keyword_gate_for(no_word, ready=lambda _f: True) is None


def test_both_must_agree_before_a_phrase_is_a_command() -> None:
    from quill.core.windows_dictation.command_mode_mixin import CommandModeMixin

    class Host(CommandModeMixin):
        _command_once = False
        _command_sticky = False

    prefs = SimpleNamespace(command_prefix="QUILL")
    host = Host()

    def phrase(heard):
        text = "Quill scratch that"
        return RecognizedPhrase(words_from_text(text), text=text, keyword_heard=heard)

    assert host._command_split(phrase(None), prefs) is not None  # no spotter: text decides
    assert host._command_split(phrase(True), prefs) is not None
    assert host._command_split(phrase(False), prefs) is None  # spotter heard no keyword


def test_the_worker_marks_each_phrase_with_what_the_spotter_heard() -> None:
    from quill.core.windows_dictation.recognizer_worker import WorkerMixin

    posted: list[RecognizedPhrase] = []

    class Vad:
        def __init__(self):
            self.front = SimpleNamespace(start=0, samples=[0.0] * 16_000)
            self._left = 1

        def empty(self):
            return self._left == 0

        def pop(self):
            self._left = 0

    class History:
        def with_lead_in(self, segment):
            return segment.samples

    class Worker(WorkerMixin):
        _generation = 0
        _live = None
        _listener = SimpleNamespace(on_phrase=lambda p: posted.append(p))

        def __init__(self):
            self._running = SimpleNamespace(is_set=lambda: True)
            self._post = lambda fn, *args: fn(*args)
            self.keyword_gate = SimpleNamespace(take=lambda: True)

        def _transcribe_healing(self, samples):
            return "Quill new paragraph"

    Worker()._drain_segments(Vad(), History())
    assert posted[0].keyword_heard is True


# -- D-28: hotwords ------------------------------------------------------------------


def test_hotwords_are_off_and_write_nothing_until_a_model_qualifies(tmp_path) -> None:
    parakeet = downloadable("parakeet")
    assert hotwords.HOTWORDS_ENABLED is False
    assert hotwords.decoder_options(parakeet, tmp_path, ["QuillVille"]) == {}
    assert hotwords.decoder_options(parakeet, tmp_path, ["QuillVille"], enabled=True) == {}
    assert not (tmp_path / "hotwords.txt").exists()


def test_a_qualified_model_gets_beam_search_and_its_hotwords_file(tmp_path) -> None:
    qualified = SimpleNamespace(tasks=frozenset({"transcribe", "hotwords"}))
    (tmp_path / "bpe.vocab").write_text("x", encoding="utf-8")
    options = hotwords.decoder_options(
        qualified, tmp_path, ["QuillVille", "quillville", " ", "Jeff Bishop"], enabled=True
    )
    assert options["decoding_method"] == "modified_beam_search"
    assert options["bpe_vocab"].endswith("bpe.vocab") and options["modeling_unit"] == "bpe"
    written = Path(options["hotwords_file"]).read_text(encoding="utf-8").split()
    assert written == ["QUILLVILLE", "JEFF", "BISHOP"]


def test_the_persons_spelling_comes_back_after_upper_case_hotwords() -> None:
    assert "QuillVille" in hotwords.restore_spelling("I live in quillville", ["QuillVille"])


# -- D-29: punctuation and speaker labels ----------------------------------------------


def test_punctuation_and_speakers_are_off_until_adopted(tmp_path) -> None:
    assert post_passes.PUNCTUATION_ADOPTED is False and post_passes.SPEAKERS_ADOPTED is False
    assert not post_passes.punctuation_ready(lambda folder, name: tmp_path)
    assert not post_passes.speakers_ready(lambda folder, name: tmp_path)


def test_punctuate_never_loses_words() -> None:
    good = SimpleNamespace(add_punctuation=lambda text: text.capitalize() + ".")
    assert post_passes.punctuate(good, "hello there") == "Hello there."

    def broken(_text):
        raise RuntimeError("model")

    assert post_passes.punctuate(SimpleNamespace(add_punctuation=broken), "hello") == "hello"
    assert post_passes.punctuate(good, "  ") == "  "


def test_the_sherpa_objects_are_built_with_cpu_and_threads(tmp_path) -> None:
    made: dict[str, dict] = {}

    def record(name):
        def build(*args, **kwargs):
            made[name] = kwargs
            return SimpleNamespace(**kwargs)

        return build

    names = (
        "OfflinePunctuationConfig OfflinePunctuationModelConfig OfflinePunctuation "
        "OfflineSpeakerDiarizationConfig OfflineSpeakerSegmentationModelConfig "
        "OfflineSpeakerSegmentationPyannoteModelConfig SpeakerEmbeddingExtractorConfig "
        "FastClusteringConfig OfflineSpeakerDiarization"
    ).split()
    sherpa = SimpleNamespace(**{name: record(name) for name in names})
    post_passes.build_punctuator(sherpa, tmp_path / "p.onnx")
    post_passes.build_diarizer(sherpa, tmp_path / "s.onnx", tmp_path / "e.onnx", speakers=2)
    assert made["OfflinePunctuationModelConfig"]["provider"] == "cpu"
    assert made["FastClusteringConfig"]["num_clusters"] == 2
    assert made["SpeakerEmbeddingExtractorConfig"]["num_threads"] == 2


def test_speakers_are_numbered_by_first_voice_and_matched_by_overlap() -> None:
    result = SimpleNamespace(
        sort_by_start_time=lambda: [
            SimpleNamespace(start=0.0, end=4.0, speaker=7),
            SimpleNamespace(start=4.0, end=9.0, speaker=3),
            SimpleNamespace(start=9.0, end=12.0, speaker=7),
        ]
    )
    turns = post_passes.speaker_turns(SimpleNamespace(process=lambda samples: result), [])
    labels = post_passes.label_spans([(0.0, 3.5), (3.8, 8.0), (9.5, 11.0), (20.0, 21.0)], turns)
    assert labels == ["Speaker 1", "Speaker 2", "Speaker 1", ""]
