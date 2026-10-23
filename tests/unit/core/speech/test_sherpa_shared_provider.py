"""One sherpa-onnx provider for every local model (dict.md D-26) -- with fakes.

Nothing here loads sherpa-onnx or downloads a model: the provider's file
pipeline, its model lists and the old-folder adoption are all injectable.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from quill.core.error_codes import CodedError
from quill.core.settings import Settings
from quill.core.speech import sherpa_migration
from quill.core.speech.provider import (
    SpeechCancelledError,
    SpeechError,
    TranscriptionRequest,
)
from quill.core.speech.providers import sherpa_shared
from quill.core.speech.providers.sherpa_shared import (
    PROMPT_UNSUPPORTED,
    SherpaSharedProvider,
    can_translate,
)
from quill.core.speech.registry import SpeechProviderRegistry
from quill.core.speech.service import (
    DEFAULT_PROVIDER_ID,
    SHARED_PROVIDER_ID,
    default_registry,
    describe_models,
    preferred_dictation_provider_id,
)
from quill.core.windows_dictation import model_catalog, model_store
from quill.core.windows_dictation.file_transcribe import (
    FileJob,
    FileTranscribeError,
    FileTranscriber,
    FileTranscript,
    Paragraph,
    Segment,
    TranscriptionCancelled,
)
from quill.core.windows_dictation.model_catalog import DownloadableModel, DownloadFile, downloadable
from quill.core.windows_dictation.model_loader import (
    SherpaLoadError,
    SherpaRuntimeError,
    SherpaUnsupportedError,
)

# -- the ladder ----------------------------------------------------------------


class _Fake:
    def __init__(self, provider_id: str, installed: tuple[str, ...] = ()) -> None:
        self.id = provider_id
        self.display_name = provider_id
        self._installed = installed

    def list_installed_models(self):
        return [type("M", (), {"id": model_id})() for model_id in self._installed]

    def list_supported_models(self):
        return []


def _registry(*providers: _Fake) -> SpeechProviderRegistry:
    registry = SpeechProviderRegistry()
    for provider in providers:
        registry.register(provider)  # type: ignore[arg-type]
    return registry


def test_an_explicit_choice_wins_and_a_chapter_engine_falls_through() -> None:
    registry = _registry(
        _Fake("whispercpp", ("base",)), _Fake("sherpa", ("parakeet",)), _Fake("vosk", ("x",))
    )
    assert preferred_dictation_provider_id(registry, "whispercpp") == "whispercpp"
    assert preferred_dictation_provider_id(registry, "vosk") == SHARED_PROVIDER_ID


def test_an_installed_parakeet_promotes_the_shared_models() -> None:
    registry = _registry(_Fake("whispercpp", ("base",)), _Fake("sherpa", ("moonshine", "parakeet")))
    assert preferred_dictation_provider_id(registry) == SHARED_PROVIDER_ID


def test_whisper_cpp_with_a_model_stays_the_default_without_parakeet() -> None:
    registry = _registry(_Fake("whispercpp", ("base",)), _Fake("sherpa", ("moonshine",)))
    assert preferred_dictation_provider_id(registry) == DEFAULT_PROVIDER_ID


def test_whisper_cpp_without_a_model_gives_way_to_the_built_in_moonshine() -> None:
    """Removing whisper.cpp's models leaves offline dictation working (D-26)."""
    registry = _registry(_Fake("whispercpp"), _Fake("sherpa", ("moonshine",)))
    assert preferred_dictation_provider_id(registry) == SHARED_PROVIDER_ID
    assert preferred_dictation_provider_id(_registry(_Fake("whispercpp"))) == DEFAULT_PROVIDER_ID


def test_the_registry_has_no_duplicate_nemotron_or_parakeet_engine() -> None:
    ids = {provider.id for provider in default_registry().available()}
    assert not ids & {"nemotron", "parakeet"}


# -- the provider's models -----------------------------------------------------


@pytest.fixture
def store(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv(model_store.DOWNLOADS_VARIABLE, str(tmp_path / "store"))
    return tmp_path / "store"


def _provider(tmp_path: Path, downloads=(), **kwargs) -> SherpaSharedProvider:
    adopted: list[int] = kwargs.pop("adopted", [])
    return SherpaSharedProvider(
        sherpa_present=lambda: True,
        built_in_folder=lambda engine_id: tmp_path / engine_id,
        downloaded=lambda: [downloadable(model_id) for model_id in downloads],
        adopt=lambda: adopted.append(1) or [],
        **kwargs,
    )


def test_installed_models_are_the_built_ins_and_the_family_store_most_accurate_first(
    tmp_path, store
) -> None:
    adopted: list[int] = []
    provider = _provider(tmp_path, ("moonshine_base", "parakeet"), adopted=adopted)
    ids = [model.id for model in provider.list_installed_models()]
    assert ids == ["parakeet", "moonshine_base", "whisper", "moonshine"]
    assert all(model.provider_id == "sherpa" for model in provider.list_installed_models())
    assert adopted == [1]  # the old folder is looked at once per provider, not per call


def test_the_supported_list_is_the_one_catalogue_with_tiers_memory_and_capabilities(
    tmp_path,
) -> None:
    rows = {info.id: info for info in _provider(tmp_path).list_supported_models()}
    assert set(rows) == set(model_catalog.catalogue_ids())
    assert "silence-safe" in rows["parakeet"].capabilities
    assert "streaming" in rows["nemotron"].capabilities
    assert "translate" in rows["whisper_small"].capabilities
    assert "translate" not in rows["whisper_base_en"].capabilities
    assert "GB of memory or more" in rows["parakeet"].recommended_use
    labels = {row.id: row.label for row in describe_models(_provider(tmp_path), 16.0, False)}
    assert "never invents text from silence" in labels["parakeet"]
    # The catalogue's tier, not a size guess: 670 MB, yet Lightweight because
    # its real-speech cost is 3.2 times Moonshine tiny.
    assert ", Lightweight" in labels["parakeet"]


def test_built_in_models_cannot_be_downloaded_or_removed(tmp_path) -> None:
    provider = _provider(tmp_path)
    with pytest.raises(SpeechError, match="part of QUILL"):
        provider.download_model("moonshine")
    with pytest.raises(SpeechError, match="cannot be removed"):
        provider.remove_model("whisper")
    with pytest.raises(SpeechError, match="No download"):
        provider.download_model("no-such-model")


def test_a_download_goes_to_the_family_store(tmp_path, store, monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(model_store, "free_space_problem", lambda model: "")
    monkeypatch.setattr(
        model_store,
        "download",
        lambda model, progress=None: seen.append(model.id) or model_store.model_folder(model),
    )
    installed = _provider(tmp_path).download_model("moonshine_base")
    assert seen == ["moonshine_base"]
    assert installed.path == store / "moonshine-base-en"


# -- transcription -------------------------------------------------------------


def _transcript(*texts: str, notice: str = "") -> FileTranscript:
    paragraphs = tuple(Paragraph(float(index * 10), text) for index, text in enumerate(texts))
    return FileTranscript(paragraphs, 25.0, 3.0, notice)


def _request(tmp_path: Path, **kwargs) -> TranscriptionRequest:
    audio = tmp_path / "talk.wav"
    audio.write_bytes(b"RIFF")
    return TranscriptionRequest(source_path=audio, **kwargs)


def test_a_transcription_is_the_file_pipeline_with_paragraph_segments(tmp_path) -> None:
    jobs: list[FileJob] = []

    def run(job, progress, cancelled):
        jobs.append(job)
        progress(0.5, 12.0)
        return _transcript("First part.", "Second part.")

    said: list[float] = []
    result = _provider(tmp_path, run_file=run).transcribe_file(
        _request(tmp_path, model_id="parakeet", language="es", initial_prompt="QUILL, Jeff"),
        lambda fraction, _message: said.append(fraction),
    )
    assert jobs[0].model == "parakeet" and jobs[0].language == "es" and not jobs[0].translate
    assert result.full_text == "First part.\n\nSecond part."
    assert [(s.start_seconds, s.end_seconds) for s in result.segments] == [
        (0.0, 10.0),
        (10.0, 25.0),
    ]
    assert result.warnings == (PROMPT_UNSUPPORTED,)  # said, never silently dropped
    assert said == [0.5, 1.0]


def test_translation_goes_to_multilingual_whisper_and_others_refuse(tmp_path) -> None:
    jobs: list[FileJob] = []
    provider = _provider(tmp_path, run_file=lambda job, p, c: jobs.append(job) or _transcript("Hi"))
    result = provider.transcribe_file(
        _request(tmp_path, model_id="whisper_small", language="es", translate_to_english=True)
    )
    assert jobs[0].translate and jobs[0].task == "translate" and result.language == "en"
    with pytest.raises(SherpaUnsupportedError, match="cannot translate"):
        provider.transcribe_file(
            _request(tmp_path, model_id="parakeet", language="es", translate_to_english=True)
        )
    assert can_translate("whisper", "es") and not can_translate("whisper", "en")
    assert not can_translate("whisper_base_en", "es")


def test_speaker_labels_are_a_warning_until_a_speaker_model_is_adopted(tmp_path) -> None:
    provider = _provider(tmp_path, run_file=lambda job, p, c: _transcript("Hello."))
    result = provider.transcribe_file(_request(tmp_path, model_id="moonshine", diarize=True))
    assert any("Speaker labels" in warning for warning in result.warnings)
    assert result.segments[0].speaker == ""


def test_failures_and_cancelling_are_speech_errors(tmp_path) -> None:
    def fail(job, p, c):
        raise FileTranscribeError("talk.wav could not be read.")

    def stop(job, p, c):
        raise TranscriptionCancelled("Transcription stopped.")

    with pytest.raises(SpeechError, match="could not be read"):
        _provider(tmp_path, run_file=fail).transcribe_file(_request(tmp_path, model_id="moonshine"))
    with pytest.raises(SpeechCancelledError):
        _provider(tmp_path, run_file=stop).transcribe_file(_request(tmp_path, model_id="moonshine"))
    absent = SherpaSharedProvider(sherpa_present=lambda: False)
    with pytest.raises(SherpaRuntimeError):
        absent.transcribe_file(_request(tmp_path, model_id="moonshine"))


def test_locked_dictation_and_transcribe_a_recording_give_identical_text(tmp_path) -> None:
    """The acceptance criterion: same file, same model, same words -- because the
    provider runs Transcribe a Recording's own pipeline."""
    pytest.importorskip("numpy")  # the live-dictation extra, not in every CI leg
    rate = 16_000

    class _Source:
        path = tmp_path / "talk.wav"
        duration = 3.0

        def blocks(self):
            import numpy as np

            yield np.zeros(rate * 3, dtype=np.float32)

    class _Segmenter:
        def accept(self, samples):
            import numpy as np

            return [Segment(0, np.zeros(rate, np.float32)), Segment(rate * 2, np.zeros(rate))]

        def finish(self):
            return []

    heard = iter(["the first phrase", "and the second", "the first phrase", "and the second"])

    def pipeline(job: FileJob) -> FileTranscriber:
        return FileTranscriber(
            job,
            opener=lambda _path: _Source(),
            segmenter=_Segmenter,
            engine=lambda _job: (lambda _samples: next(heard), ""),
        )

    direct = pipeline(FileJob(tmp_path / "talk.wav", "parakeet")).run()
    provider = _provider(
        tmp_path, run_file=lambda job, progress, cancelled: pipeline(job).run(progress, cancelled)
    )
    locked = provider.transcribe_file(_request(tmp_path, model_id="parakeet"))
    assert locked.full_text == direct.text() != ""


# -- errors --------------------------------------------------------------------


def test_the_three_shared_layer_errors_are_coded() -> None:
    codes = {cls.code for cls in (SherpaLoadError, SherpaUnsupportedError, SherpaRuntimeError)}
    assert codes == {
        "QUILL-SPEECH-SHERPA-LOAD",
        "QUILL-SPEECH-SHERPA-UNSUPPORTED",
        "QUILL-SPEECH-SHERPA-RUNTIME",
    }
    assert all(issubclass(cls, (CodedError, SpeechError)) for cls in (SherpaLoadError,))


# -- migration of saved choices and the old model folder -----------------------


@pytest.mark.parametrize(
    ("saved", "expected"),
    [
        (
            {
                "speech_provider": "nemotron",
                "speech_default_model_id": "nemotron-streaming-en-0.6b",
            },
            ("sherpa", "nemotron"),
        ),
        (
            {"speech_provider": "parakeet", "speech_default_model_id": "parakeet-tdt-0.6b-v3"},
            ("sherpa", "parakeet"),
        ),
        (
            {"speech_provider": "whispercpp", "speech_default_model_id": "small"},
            ("whispercpp", "small"),
        ),
        ({"speech_provider": "vosk"}, ("", "")),
        ({"speech_provider": "SHERPA"}, ("sherpa", "")),
    ],
)
def test_saved_engine_choices_move_to_the_shared_provider(saved, expected) -> None:
    assert sherpa_migration.migrate_choice(saved) == expected
    loaded = Settings.from_dict(saved)
    assert (loaded.speech_provider, loaded.speech_default_model_id) == expected


def _tiny_parakeet(**overrides) -> DownloadableModel:
    bodies = {"encoder.int8.onnx": b"enc", "tokens.txt": b"a 1\n"}
    values = dict(
        id="parakeet",
        name="Parakeet (test)",
        good_for="t",
        description="d",
        group="g",
        kind="nemo_transducer",
        languages=("en",),
        works_best_on="w",
        accuracy="a",
        repo="o/r",
        commit="0" * 40,
        files=tuple(
            DownloadFile(
                name,
                "tokens" if name.endswith(".txt") else "encoder",
                len(body),
                hashlib.sha256(body).hexdigest(),
            )
            for name, body in bodies.items()
        ),
        licence="CC BY 4.0",
        licence_url="https://x",
        source="s",
        cost_factor=6.3,
        folder="parakeet-test",
    )
    values.update(overrides)
    return DownloadableModel(**values)


def _legacy(root: Path, nested: bool = False) -> Path:
    folder = root / "parakeet" / "parakeet-tdt-0.6b-v3"
    if nested:
        folder = folder / "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
    folder.mkdir(parents=True)
    (folder / "encoder.int8.onnx").write_bytes(b"enc")
    (folder / "tokens.txt").write_bytes(b"a 1\n")
    return folder


@pytest.mark.parametrize("nested", [False, True])
def test_an_old_parakeet_is_adopted_into_the_store_not_downloaded_again(
    tmp_path, store, monkeypatch, nested
) -> None:
    model = _tiny_parakeet()
    monkeypatch.setattr(model_catalog, "downloadable", lambda model_id: model)
    _legacy(tmp_path / "legacy", nested)
    assert sherpa_migration.adopt_legacy_models(tmp_path / "legacy") == ["parakeet"]
    assert model_store.installed(model)
    assert (store / "parakeet-test" / "tokens.txt").read_bytes() == b"a 1\n"
    assert sherpa_migration.adopt_legacy_models(tmp_path / "legacy") == []  # once


def test_a_partial_old_parakeet_is_left_alone(tmp_path, store, monkeypatch) -> None:
    model = _tiny_parakeet()
    monkeypatch.setattr(model_catalog, "downloadable", lambda model_id: model)
    old = _legacy(tmp_path / "legacy")
    (old / "tokens.txt").write_bytes(b"a different size\n")
    assert sherpa_migration.adopt_legacy_models(tmp_path / "legacy") == []
    assert not (store / "parakeet-test").exists()


def test_the_provider_module_never_imports_sherpa_onnx_at_import_time() -> None:
    source = Path(sherpa_shared.__file__).read_text(encoding="utf-8")
    assert "\nimport sherpa_onnx" not in source and "\nfrom sherpa_onnx" not in source
