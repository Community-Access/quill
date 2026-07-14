"""Unit tests for the speech project profile (batch-document-to-speech §4.10)."""

from __future__ import annotations

from pathlib import Path

from quill.core.speech.project_profile import (
    ChapterProfile,
    DictionaryRef,
    OutputProfile,
    PronunciationProfile,
    SpeechProjectProfile,
    SynthesizerProfile,
    TranslationProfile,
    TranslationTarget,
    load_profile,
    profile_path,
    save_profile,
    to_batch_options,
    to_chapter_options,
)


def _full_profile() -> SpeechProjectProfile:
    return SpeechProjectProfile(
        synthesizer=SynthesizerProfile(
            engine="piper",
            voice="en_US-amy",
            rate=210,
            extra={"piper_model": "C:/m/amy.onnx", "piper_executable": "C:/p/piper.exe"},
        ),
        output=OutputProfile(format="mp3", skip_existing=True),
        chapters=ChapterProfile(
            mode="single",
            sound_enabled=True,
            sound_volume=80,
            article_gap_ms=1500,
            combine_headings=True,
            round_robin_voices=("en_US-amy", "en_US-ryan"),
        ),
        normalization={"dash_mode": "words"},
        pronunciation=PronunciationProfile(
            enabled=True,
            dictionaries=[
                DictionaryRef(id="news", scope="project", path=".quill/pronunciation/news.json"),
                DictionaryRef(id="tech", scope="global"),
            ],
        ),
        translation=TranslationProfile(
            provider="ai_assistant",
            targets=[
                TranslationTarget(language="es", engine="espeak", voice="es"),
                TranslationTarget(language="fr", engine="openai", voice="nova"),
            ],
        ),
    )


def test_translation_targets_round_trip() -> None:
    p = _full_profile()
    restored = SpeechProjectProfile.from_dict(p.to_dict())
    assert [t.language for t in restored.translation.targets] == ["es", "fr"]
    assert restored.translation.targets[1].engine == "openai"
    # An unknown provider falls back to ai_assistant.
    bad = SpeechProjectProfile.from_dict({"version": 1, "translation": {"provider": "bogus"}})
    assert bad.translation.provider == "ai_assistant"


def test_round_trips_through_dict() -> None:
    p = _full_profile()
    assert SpeechProjectProfile.from_dict(p.to_dict()) == p


def test_save_and_load(tmp_path: Path) -> None:
    p = _full_profile()
    path = save_profile(p, tmp_path)
    assert path == profile_path(tmp_path)
    assert path.is_file()
    assert path.parent.name == ".quill"
    assert load_profile(tmp_path) == p


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_profile(tmp_path) is None


def test_defaults_are_sane() -> None:
    p = SpeechProjectProfile()
    # v2 with the Phase 4-6 wizard fields added; older v1 documents still
    # load via from_dict (see round3 test for the v1->v2 tolerance contract).
    assert p.version == 2
    assert p.synthesizer.engine == "sapi5"
    assert p.output.format == "wav"
    assert p.chapters.mode == "none"
    assert p.pronunciation.enabled is True
    assert p.pronunciation.dictionaries == []
    # The two new top-level booleans default to False.
    assert p.book_credits is False
    assert p.library_mode is False


def test_from_dict_clamps_and_falls_back() -> None:
    p = SpeechProjectProfile.from_dict({
        "version": 1,
        "synthesizer": {"engine": "bogus", "rate": 99999, "volume": 5, "speed": -1},
        "output": {"format": "aiff"},  # unsupported -> falls back to wav
        "chapters": {"mode": "weird", "sound_volume": 500, "article_gap_ms": -10},
        "pronunciation": {
            "dictionaries": [
                {"scope": "x", "format": "y"},  # no id -> dropped
                {"id": "ok", "scope": "x", "format": "y"},  # bad scope/format -> defaults
            ]
        },
    })
    assert p.synthesizer.engine == "sapi5"
    assert p.synthesizer.rate == 800  # clamped
    assert p.synthesizer.volume == 1.0  # clamped
    assert p.synthesizer.speed == 0.25  # clamped
    assert p.output.format == "wav"
    assert p.chapters.mode == "none"
    assert p.chapters.sound_volume == 100
    assert p.chapters.article_gap_ms == 0
    assert [d.id for d in p.pronunciation.dictionaries] == ["ok"]
    assert p.pronunciation.dictionaries[0].scope == "global"
    assert p.pronunciation.dictionaries[0].format == "quill-json"


def test_from_dict_tolerates_garbage() -> None:
    assert SpeechProjectProfile.from_dict({}) == SpeechProjectProfile()
    # Non-dict sub-objects are ignored, not fatal.
    p = SpeechProjectProfile.from_dict({"synthesizer": "nope", "chapters": 5})
    assert p.synthesizer.engine == "sapi5"
    assert p.chapters.mode == "none"


def test_to_batch_options_piper(tmp_path: Path) -> None:
    opts = to_batch_options(_full_profile(), tmp_path / "src", tmp_path / "out")
    assert opts.engine == "piper"
    assert opts.output_format == "mp3"
    assert opts.skip_existing is True
    assert opts.piper_model == Path("C:/m/amy.onnx")
    assert opts.piper_executable == Path("C:/p/piper.exe")


def test_new_flexibility_fields_round_trip() -> None:
    from quill.core.speech.project_profile import (
        DiscoveryProfile,
        ExecutionProfile,
        MetadataProfile,
    )

    p = SpeechProjectProfile(
        discovery=DiscoveryProfile(
            extensions=[".md"], recursive=False, include_glob="keep-*", max_file_bytes=2048
        ),
        output=OutputProfile(
            format="m4b",
            on_existing="rename",
            mp3_vbr_quality=2,
            wav_sample_rate=44100,
            wav_channels=1,
            flatten=True,
            filename_template="{index:03d} - {stem}",
        ),
        metadata=MetadataProfile(album="My Book", author="Jeff", genre="Audiobook"),
        execution=ExecutionProfile(
            stop_on_error=True, retry_count=3, max_workers=4, write_manifest=True
        ),
    )
    assert SpeechProjectProfile.from_dict(p.to_dict()) == p


def test_output_profile_clamps_new_fields() -> None:
    out = OutputProfile.from_dict({
        "format": "m4b",
        "on_existing": "nonsense",  # -> overwrite
        "mp3_vbr_quality": 99,  # -> clamped to 9
        "wav_sample_rate": 10,  # below min -> clamped to 8000
        "wav_channels": "",  # blank -> None
    })
    assert out.format == "m4b"
    assert out.on_existing == "overwrite"
    assert out.mp3_vbr_quality == 9
    assert out.wav_sample_rate == 8000
    assert out.wav_channels is None


def test_to_batch_options_threads_flexibility(tmp_path: Path) -> None:
    from quill.core.speech.project_profile import (
        DiscoveryProfile,
        ExecutionProfile,
        MetadataProfile,
    )

    profile = SpeechProjectProfile(
        synthesizer=SynthesizerProfile(engine="piper"),
        discovery=DiscoveryProfile(include_glob="keep-*", max_file_bytes=4096),
        output=OutputProfile(format="m4b", on_existing="rename", flatten=True, mp3_vbr_quality=2),
        metadata=MetadataProfile(album="Book", author="Jeff"),
        execution=ExecutionProfile(retry_count=2, max_workers=3, write_manifest=True),
    )
    opts = to_batch_options(profile, tmp_path / "src", tmp_path / "out")
    assert opts.output_format == "m4b"
    assert opts.on_existing == "rename"
    assert opts.flatten is True
    assert opts.include_glob == "keep-*"
    assert opts.max_file_bytes == 4096
    assert opts.mp3_vbr_quality == "2"
    assert opts.retry_count == 2
    assert opts.max_workers == 3
    assert opts.write_manifest is True
    assert opts.metadata.album == "Book"
    assert opts.metadata.artist == "Jeff"


def test_to_batch_options_sapi5(tmp_path: Path) -> None:
    profile = SpeechProjectProfile(
        synthesizer=SynthesizerProfile(engine="sapi5", voice="David", rate=180, volume=0.8)
    )
    opts = to_batch_options(profile, tmp_path / "s", tmp_path / "o")
    assert opts.engine == "sapi5"
    assert opts.sapi5_voice == "David"
    assert opts.sapi5_rate == 180
    assert opts.sapi5_volume == 0.8


def test_to_chapter_options() -> None:
    co = to_chapter_options(_full_profile())
    assert co.article_gap_ms == 1500
    assert co.sound_enabled is True
    assert co.sound_volume == 80
    assert co.output_format == "mp3"
