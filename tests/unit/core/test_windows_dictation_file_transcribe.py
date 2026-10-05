"""Transcribe a Recording's wx-free half: decoding, phrases, paragraphs, text.

Every heavy piece is a fake -- the decoder, the voice detector, the engines --
so these run anywhere, with no model, no sound file and no network. The real
recordings were checked end to end on 2026-10-05 (the design note, section 12).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import audio_file, file_models, file_transcribe
from quill.core.windows_dictation.audio_file import RATE, AudioFileError, AudioSource, Resampler
from quill.core.windows_dictation.file_models import FileModel
from quill.core.windows_dictation.file_transcribe import (
    FileJob,
    FileTranscriber,
    FileTranscript,
    Paragraph,
    Segment,
    TranscriptionCancelled,
    done_sentence,
    plain,
    timestamp,
)

# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


def _numpy() -> Any:
    """numpy, or a skip: it comes with the dictation extra, which CI does not
    install, and the tests that need no samples should still run there."""
    return pytest.importorskip("numpy")


def _source(seconds: float, path: Path = Path("talk.mp3")) -> AudioSource:
    """A recording of *seconds* of quiet, a second at a time."""
    np = _numpy()

    def blocks() -> Any:
        whole = int(seconds * RATE)
        for start in range(0, whole, RATE):
            yield np.zeros(min(RATE, whole - start), dtype=np.float32)

    return AudioSource(path, seconds, "fake", blocks)


class _Phrases:
    """A voice detector that 'finds' fixed phrases once enough sound has passed.

    *phrases* is ``(start_seconds, length_seconds, words)``; the words ride on
    the samples' first value so the fake engine can say them back.
    """

    def __init__(self, phrases: list[tuple[float, float, str]]) -> None:
        self._phrases = list(phrases)
        self.heard = 0
        self.words: dict[int, str] = {}

    def _due(self, final: bool) -> list[Segment]:
        np = _numpy()
        out = []
        while self._phrases:
            start, length, words = self._phrases[0]
            if not final and (start + length) * RATE > self.heard:
                break
            self._phrases.pop(0)
            marker = len(self.words) + 1
            self.words[marker] = words
            samples = np.full(int(length * RATE), marker, dtype=np.float32)
            out.append(Segment(int(start * RATE), samples))
        return out

    def accept(self, samples: Any) -> list[Segment]:
        self.heard += len(samples)
        return self._due(False)

    def finish(self) -> list[Segment]:
        return self._due(True)


def _run(
    phrases: list[tuple[float, float, str]],
    *,
    seconds: float = 60.0,
    progress: Any = None,
    cancelled: Any = lambda: False,
    model: str = "moonshine",
    **job: Any,
) -> tuple[FileTranscript, list[Any]]:
    np = _numpy()  # skip here, not inside the transcriber's own loop
    detector = _Phrases(phrases)
    sent: list[Any] = []

    def engine(_job: FileJob) -> tuple[Any, str]:
        def recognise(samples: Any) -> str:
            sent.append(samples)
            markers = [int(value) for value in dict.fromkeys(np.asarray(samples)) if value]
            return " ".join(detector.words[marker] for marker in markers)

        return recognise, ""

    transcriber = FileTranscriber(
        FileJob(Path("talk.mp3"), model, **job),
        opener=lambda path: _source(seconds, path),
        segmenter=lambda: detector,
        engine=engine,
    )
    return transcriber.run(progress, cancelled), sent


# --------------------------------------------------------------------------- #
# The pipeline
# --------------------------------------------------------------------------- #


def test_phrases_become_tidy_sentences_in_one_paragraph() -> None:
    transcript, _sent = _run([
        (1.0, 2.0, "Can you send me the report by Friday?"),
        (3.5, 2.0, "the meeting moved to Thursday."),
    ])
    assert transcript.text() == (
        "Can you send me the report by Friday? The meeting moved to Thursday."
    )
    assert transcript.words == 13


def test_a_long_pause_starts_a_paragraph_with_its_time() -> None:
    transcript, _sent = _run(
        [(1.0, 2.0, "First thought."), (83.0, 2.0, "Second thought.")], seconds=90
    )
    assert transcript.text() == "First thought.\n\nSecond thought."
    assert transcript.text(timestamps=True) == (
        "[00:00:01] First thought.\n\n[00:01:23] Second thought."
    )


def test_two_minutes_of_unbroken_talk_is_broken_at_the_next_pause() -> None:
    phrases = [
        (float(start), 9.5, f"Part {index}.") for index, start in enumerate(range(0, 140, 10))
    ]
    transcript, _sent = _run(phrases, seconds=150)
    assert len(transcript.paragraphs) == 2


def test_a_breath_full_stop_is_taken_back_when_the_sentence_carries_on() -> None:
    transcript, _sent = _run([(1.0, 2.0, "I went to the store."), (3.2, 1.0, "And bought milk.")])
    assert transcript.text() == "I went to the store and bought milk."


def test_spoken_commands_are_words_unless_asked() -> None:
    phrases = [(1.0, 2.0, "Read this new paragraph aloud."), (3.5, 1.0, "Scratch that.")]
    plain_text, _sent = _run(phrases)
    assert "new paragraph" in plain_text.text()
    assert "Scratch that." in plain_text.text()


def test_obeyed_commands_write_marks_and_scratch_that() -> None:
    phrases = [
        (1.0, 2.0, "Dear Ann comma"),
        (3.5, 1.0, "this is wrong."),
        (5.0, 1.0, "scratch that"),
        (6.5, 1.0, "see you soon period"),
    ]
    transcript, _sent = _run(phrases, obey_commands=True)
    text = transcript.text()
    assert text.startswith("Dear Ann,")
    assert "wrong" not in text
    assert text.endswith("see you soon.")


def test_fillers_go_only_when_dictation_removes_them() -> None:
    phrases = [(1.0, 2.0, "Um, so the plan is ready.")]
    kept, _ = _run(phrases)
    gone, _ = _run(phrases, remove_fillers=True)
    assert "Um" in kept.text()
    assert "Um" not in gone.text() and "plan is ready" in gone.text()


def test_progress_is_a_rising_fraction_reported_at_most_once_a_percent() -> None:
    seen: list[float | None] = []
    _run([(1.0, 1.0, "Hello.")], seconds=300, progress=lambda fraction, _s: seen.append(fraction))
    fractions = [value for value in seen if value is not None]
    assert fractions == sorted(fractions)
    assert len(seen) <= 100
    assert fractions[-1] < 1.0


def test_cancel_stops_part_way() -> None:
    calls = {"n": 0}

    def cancelled() -> bool:
        calls["n"] += 1
        return calls["n"] > 3

    with pytest.raises(TranscriptionCancelled):
        _run([(1.0, 1.0, "Hello."), (50.0, 1.0, "Never reached.")], cancelled=cancelled)


def test_openai_gets_a_minute_or_so_at_a_time_never_across_a_paragraph() -> None:
    phrases = [(float(start), 9.0, f"Part {start}.") for start in range(0, 100, 10)]
    phrases.append((105.0, 5.0, "After the pause."))
    transcript, sent = _run(phrases, seconds=120, model="openai:gpt-transcribe")
    assert len(sent) == 3  # 0-60 s, 60-100 s, then the new paragraph
    assert all(len(piece) <= 61 * RATE for piece in sent)
    assert transcript.text().endswith("\n\nAfter the pause.")


def test_the_real_engine_is_asked_for_when_none_is_given(monkeypatch) -> None:
    asked: list[str] = []

    def local_engine(engine_id: str, language: str) -> tuple[Any, str]:
        asked.append(f"{engine_id}/{language}")
        return (lambda _samples: "Hello."), "notice"

    monkeypatch.setattr(file_transcribe, "local_engine", local_engine)
    transcriber = FileTranscriber(
        FileJob(Path("a.wav"), "parakeet", language="es"),
        opener=lambda path: _source(5, path),
        segmenter=lambda: _Phrases([(1.0, 1.0, "x")]),
    )
    transcript = transcriber.run()
    assert asked == ["parakeet/es"]
    assert transcript.notice == "notice"


def test_silero_segmenter_feeds_whole_windows_and_flushes() -> None:
    np = _numpy()

    class Vad:
        def __init__(self) -> None:
            self.windows: list[int] = []
            self.flushed = False
            self.queue: list[Any] = []

        def accept_waveform(self, samples: Any) -> None:
            self.windows.append(len(samples))
            if len(self.windows) == 3:
                self.queue.append(type("S", (), {"start": 512, "samples": [0.1] * 512})())

        def empty(self) -> bool:
            return not self.queue

        @property
        def front(self) -> Any:
            return self.queue[0]

        def pop(self) -> None:
            self.queue.pop(0)

        def flush(self) -> None:
            self.flushed = True

    vad = Vad()
    segmenter = file_transcribe._SileroSegmenter(vad)
    found = segmenter.accept(np.zeros(1600, dtype=np.float32))
    assert set(vad.windows) == {512} and len(vad.windows) == 3
    assert found[0].start == 512 and found[0].end == 1024
    segmenter.finish()
    assert vad.flushed and vad.windows[-1] == 512


def test_sentences_and_timestamps() -> None:
    transcript = FileTranscript((Paragraph(0, "One two three."),), 720.0, 185.0)
    assert done_sentence("meeting.mp3", transcript) == (
        "Transcribed meeting.mp3: 12 minutes, 3 words, in 3 minutes."
    )
    assert "no speech" in done_sentence("quiet.mp3", FileTranscript((), 30.0, 2.0))
    assert timestamp(3723.9) == "[01:02:03]"
    assert plain(file_transcribe.FileTranscribeError("A sentence.")) == "A sentence."


# --------------------------------------------------------------------------- #
# Reading files
# --------------------------------------------------------------------------- #


def test_resampling_in_pieces_matches_resampling_whole() -> None:
    np = _numpy()
    tone = np.sin(np.arange(44_100 * 2) / 44_100 * 2 * np.pi * 300).astype(np.float32)
    whole = Resampler(44_100).process(tone)
    pieces = Resampler(44_100)
    joined = np.concatenate([pieces.process(tone[i : i + 777]) for i in range(0, tone.size, 777)])
    assert abs(whole.size - 32_000) <= 2
    assert np.allclose(whole[: joined.size], joined[: whole.size], atol=1e-5)
    assert 0.9 < float(np.max(np.abs(whole[500:1500]))) < 1.1  # speech band kept


def test_16_khz_passes_straight_through() -> None:
    np = _numpy()
    samples = np.arange(10, dtype=np.float32)
    assert np.array_equal(Resampler(16_000).process(samples), samples)


def test_open_audio_tries_each_decoder_and_says_why_when_none_can(tmp_path) -> None:
    recording = tmp_path / "talk.m4a"
    recording.write_bytes(b"x")
    tried: list[str] = []

    def refuse(name: str) -> Any:
        def opener(path: Path) -> AudioSource:
            tried.append(name)
            raise RuntimeError(name)

        return opener

    with pytest.raises(AudioFileError) as raised:
        audio_file.open_audio(recording, openers=(refuse("one"), refuse("two")))
    assert tried == ["one", "two"]
    assert "MP3, M4A, AAC, WAV, Ogg, Opus, FLAC and WMA" in plain(raised.value)
    with pytest.raises(AudioFileError) as missing:
        audio_file.open_audio(tmp_path / "gone.mp3")
    assert "was not found" in plain(missing.value)


def test_m4a_goes_to_media_foundation_first_and_mp3_to_libsndfile(monkeypatch, tmp_path) -> None:
    order: list[str] = []

    def opener(name: str) -> Any:
        def open_it(path: Path) -> AudioSource:
            order.append(name)
            raise RuntimeError

        return open_it

    monkeypatch.setattr(audio_file, "_soundfile_source", opener("soundfile"))
    monkeypatch.setattr(audio_file, "_media_foundation_source", opener("mf"))
    monkeypatch.setattr(audio_file, "_ffmpeg_source", opener("ffmpeg"))
    for name in ("a.m4a", "b.mp3"):
        (tmp_path / name).write_bytes(b"x")
        with pytest.raises(AudioFileError):
            audio_file.open_audio(tmp_path / name)
    assert order == ["mf", "soundfile", "ffmpeg", "soundfile", "mf", "ffmpeg"]


def test_the_picker_offers_every_format() -> None:
    wildcard = audio_file.file_filter()
    for extension in ("*.mp3", "*.m4a", "*.aac", "*.wav", "*.ogg", "*.opus", "*.flac", "*.wma"):
        assert extension in wildcard


# --------------------------------------------------------------------------- #
# Which models, and how long
# --------------------------------------------------------------------------- #


@pytest.fixture
def downloaded(monkeypatch):
    from quill.core.windows_dictation import model_store, openai_models
    from quill.core.windows_dictation.model_catalog import downloadable

    have: list[str] = []
    problem = {"text": "OpenAI dictation needs your own OpenAI key."}
    monkeypatch.setattr(
        model_store, "installed_models", lambda: [downloadable(name) for name in have]
    )
    monkeypatch.setattr(openai_models, "cloud_problem", lambda **_k: problem["text"])
    return have, problem


def test_only_the_built_in_two_until_something_is_downloaded(downloaded) -> None:
    rows = file_models.file_models("en")
    assert [row.id for row in rows] == ["whisper", "moonshine"]
    assert file_models.default_model(rows).id == "whisper"


def test_downloaded_models_join_and_the_most_accurate_is_suggested(downloaded) -> None:
    have, _problem = downloaded
    have.extend(["whisper_small", "moonshine_base", "parakeet"])
    rows = file_models.file_models("en")
    assert [row.id for row in rows] == [
        "parakeet",
        "whisper_small",
        "moonshine_base",
        "whisper",
        "moonshine",
    ]
    assert file_models.default_model(rows).id == "parakeet"
    assert rows[0].label.endswith("(downloaded)")


def test_spanish_lists_only_models_that_know_spanish(downloaded) -> None:
    have, _problem = downloaded
    have.extend(["parakeet_unified", "nemotron"])
    assert [row.id for row in file_models.file_models("es")] == ["nemotron", "whisper"]


def test_openai_appears_only_with_a_key_and_never_its_live_model(downloaded) -> None:
    _have, problem = downloaded
    live = ["gpt-live-transcribe", "gpt-transcribe"]
    assert all(not row.cloud for row in file_models.file_models("en", live))
    problem["text"] = ""
    rows = file_models.file_models("en", live)
    cloud = [row for row in rows if row.cloud]
    assert [row.openai_model for row in cloud] == ["gpt-transcribe"]
    assert rows[-1].cloud  # after every local model
    assert not file_models.default_model(rows).cloud  # never suggested


def test_the_estimate_uses_the_measured_speeds() -> None:
    tiny = FileModel("moonshine", "Moonshine tiny (built in, fastest)", "", ("en",), 1.0)
    big = FileModel("parakeet", "NVIDIA Parakeet TDT 0.6B v3 (downloaded)", "", ("en",), 6.3)
    hour = 3600.0
    assert file_models.estimate_seconds(tiny, hour, weak=True) < file_models.estimate_seconds(
        big, hour, weak=True
    )
    assert file_models.estimate_seconds(big, hour, weak=False) < file_models.estimate_seconds(
        big, hour, weak=True
    )
    sentence = file_models.estimate_sentence(big, hour, weak=True)
    assert sentence.startswith("The recording is 1 hour long. With NVIDIA Parakeet TDT 0.6B v3,")
    assert "should take about" in sentence
    cloud = FileModel("openai:gpt-transcribe", "OpenAI gpt-transcribe", "", ("en",), None)
    assert file_models.estimate_seconds(cloud, hour, weak=True) is None
    assert "internet connection" in file_models.estimate_sentence(cloud, hour, weak=True)
    assert "no estimate" in file_models.estimate_sentence(tiny, 0, weak=True)


def test_spoken_lengths() -> None:
    assert file_models.spoken_length(1) == "1 second"
    assert file_models.spoken_length(45) == "45 seconds"
    assert file_models.spoken_length(60) == "1 minute"
    assert file_models.spoken_length(3900) == "1 hour 5 minutes"
    assert file_models.spoken_length(7200) == "2 hours"


def test_a_currency_sign_glued_to_the_word_before_gets_its_space() -> None:
    transcript, _sent = _run([(1.0, 2.0, "We spend about$12,000 a year, in US$.")])
    assert "about $12,000" in transcript.text()
    assert "US$" in transcript.text()
