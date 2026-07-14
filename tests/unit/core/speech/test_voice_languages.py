"""Tests for per-language voice selection (translated audio export, §7)."""

from __future__ import annotations

from quill.core.speech import voice_languages as vl


def test_base_language_normalizes_region() -> None:
    assert vl.base_language("es-ES") == "es"
    assert vl.base_language("ES_419") == "es"
    assert vl.base_language("en") == "en"


def test_espeak_supports_and_voices_for_spanish() -> None:
    assert vl.espeak_supports("es") is True
    assert vl.espeak_supports("es-419") is True
    assert vl.espeak_supports("tlh") is False  # Klingon is not translatable/eSpeak here
    voices = vl.espeak_voices_for_language("es")
    ids = {v.voice_id for v in voices}
    assert ids == {"es", "es-419"}
    assert all(v.engine == "espeak" and v.language == "es" and v.tier == "local" for v in voices)


def test_espeak_single_dialect_language() -> None:
    fr = vl.espeak_voices_for_language("de")
    assert [v.voice_id for v in fr] == ["de"]


def test_cloud_voices_are_multilingual_premium_tier() -> None:
    cloud = vl.cloud_voices_for_language("es")
    assert cloud, "cloud providers should offer voices for any language"
    assert all(v.tier == "cloud" and v.dialect == "multilingual" for v in cloud)
    # ElevenLabs / OpenAI / Gemini all appear.
    engines = {v.engine for v in cloud}
    assert {"openai", "gemini", "elevenlabs"} <= engines


def test_voices_for_language_local_first_then_cloud() -> None:
    voices = vl.voices_for_language("es", include_sapi=False)
    # eSpeak (local) entries come before the cloud entries.
    first_cloud = next(i for i, v in enumerate(voices) if v.tier == "cloud")
    assert all(v.tier == "local" for v in voices[:first_cloud])


def test_lcid_to_base_maps_common_languages() -> None:
    from quill.platform.windows.sapi5 import _lcid_to_base

    assert _lcid_to_base("40a") == "es"  # Spanish (Spain)
    assert _lcid_to_base("80a") == "es"  # Spanish (Mexico) -> same base
    assert _lcid_to_base("409") == "en"  # English (US)
    assert _lcid_to_base("40c") == "fr"  # French (France)
    assert _lcid_to_base("") == ""
    assert _lcid_to_base("zzz") == ""
