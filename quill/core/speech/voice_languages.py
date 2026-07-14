"""Per-language voice selection for translated audio export (roadmap §7).

Given a target language (ISO 639-1 base subtag, e.g. ``"es"``), enumerate the voices
that can speak it, **tiered local-first**:

1. **eSpeak NG** — always-available, fully offline, covers nearly every language QUILL
   can translate to (the universal local tier). eSpeak voice ids *are* language codes.
2. **SAPI 5** — the installed Windows voices whose language matches (high-quality local
   when present; needs the voice's LCID, read best-effort by ``platform.windows.sapi5``).
3. **Cloud TTS** — OpenAI / Gemini / ElevenLabs are multilingual, so every one of their
   voices is a candidate for every language (the premium tier; needs a configured key).

wx-free, strict-typed. The picker shows local options first so "local where possible"
is the default, with cloud as the quality fallback.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tiers, ordered best-effort local-first for display.
TIER_LOCAL = "local"
TIER_CLOUD = "cloud"


@dataclass(frozen=True, slots=True)
class LanguageVoiceOption:
    """A voice that can speak a target language, with its engine and dialect."""

    engine: str  # espeak | sapi5 | openai | gemini | elevenlabs
    voice_id: str
    label: str
    language: str  # base subtag, e.g. "es"
    dialect: str = ""  # full tag / human dialect, e.g. "es-419" or "Latin America"
    tier: str = TIER_LOCAL

    @property
    def display(self) -> str:
        bits = [self.label]
        if self.dialect:
            bits.append(f"({self.dialect})")
        bits.append(f"— {self.engine}")
        return " ".join(bits)


def base_language(language: str) -> str:
    """Normalize a language tag to its lowercase base subtag (``es-ES`` -> ``es``)."""
    return language.strip().lower().replace("_", "-").split("-", 1)[0]


# eSpeak NG voices for each base language QUILL can translate to. Values are
# ``(espeak_voice_id, dialect_label)``; a language with regional variants lists each.
# eSpeak voice ids are the codes eSpeak accepts after ``-v``.
_ESPEAK_BY_LANG: dict[str, list[tuple[str, str]]] = {
    "en": [("en-us", "US"), ("en-gb", "UK")],
    "es": [("es", "Spain"), ("es-419", "Latin America")],
    "pt": [("pt", "Portugal"), ("pt-br", "Brazil")],
    "fr": [("fr", "France"), ("fr-be", "Belgium")],
    "zh": [("cmn", "Mandarin"), ("yue", "Cantonese")],
    "af": [("af", "")],
    "ar": [("ar", "")],
    "bg": [("bg", "")],
    "hr": [("hr", "")],
    "cs": [("cs", "")],
    "da": [("da", "")],
    "nl": [("nl", "")],
    "et": [("et", "")],
    "fi": [("fi", "")],
    "de": [("de", "")],
    "el": [("el", "")],
    "he": [("he", "")],
    "hi": [("hi", "")],
    "hu": [("hu", "")],
    "id": [("id", "")],
    "it": [("it", "")],
    "ja": [("ja", "")],
    "ko": [("ko", "")],
    "lv": [("lv", "")],
    "lt": [("lt", "")],
    "no": [("nb", "")],
    "pl": [("pl", "")],
    "ro": [("ro", "")],
    "ru": [("ru", "")],
    "sk": [("sk", "")],
    "sl": [("sl", "")],
    "sv": [("sv", "")],
    "th": [("th", "")],
    "tr": [("tr", "")],
    "uk": [("uk", "")],
    "vi": [("vi", "")],
}


def espeak_supports(language: str) -> bool:
    """True when eSpeak NG can speak *language* (a local option always exists)."""
    return base_language(language) in _ESPEAK_BY_LANG


def espeak_voices_for_language(language: str) -> list[LanguageVoiceOption]:
    """eSpeak voices for *language* (one per dialect), or empty if unsupported."""
    base = base_language(language)
    out: list[LanguageVoiceOption] = []
    for voice_id, dialect in _ESPEAK_BY_LANG.get(base, []):
        label = f"eSpeak {base.upper()}"
        out.append(
            LanguageVoiceOption(
                engine="espeak",
                voice_id=voice_id,
                label=label,
                language=base,
                dialect=dialect or voice_id,
                tier=TIER_LOCAL,
            )
        )
    return out


def sapi_voices_for_language(language: str) -> list[LanguageVoiceOption]:
    """Installed SAPI 5 voices whose language matches *language* (Windows; best-effort).

    Returns empty when SAPI is unavailable or no voice carries a matching language
    (the voice's LCID is read best-effort; voices without a known language are not
    assumed to match a specific target).
    """
    base = base_language(language)
    try:
        from quill.core.read_aloud import list_voices
    except Exception:  # noqa: BLE001
        return []
    out: list[LanguageVoiceOption] = []
    for voice in list_voices():
        vlang = base_language(getattr(voice, "language", "") or "")
        if vlang and vlang == base:
            out.append(
                LanguageVoiceOption(
                    engine="sapi5",
                    voice_id=voice.id,
                    label=voice.name or voice.id,
                    language=base,
                    dialect=getattr(voice, "language", "") or "",
                    tier=TIER_LOCAL,
                )
            )
    return out


def cloud_voices_for_language(language: str) -> list[LanguageVoiceOption]:
    """Multilingual cloud voices (any voice speaks any language); the premium tier."""
    base = base_language(language)
    out: list[LanguageVoiceOption] = []
    try:
        from quill.core.ai import cloud_tts
    except Exception:  # noqa: BLE001
        return []
    for provider in cloud_tts.PROVIDERS:
        for voice_id, label in cloud_tts.voices_for(provider):
            out.append(
                LanguageVoiceOption(
                    engine=provider,
                    voice_id=voice_id,
                    label=f"{cloud_tts.provider_label(provider)}: {label}",
                    language=base,
                    dialect="multilingual",
                    tier=TIER_CLOUD,
                )
            )
    return out


def voices_for_language(
    language: str, *, include_sapi: bool = True, include_cloud: bool = True
) -> list[LanguageVoiceOption]:
    """All voices that can speak *language*, local tiers first, then cloud."""
    out: list[LanguageVoiceOption] = list(espeak_voices_for_language(language))
    if include_sapi:
        out.extend(sapi_voices_for_language(language))
    if include_cloud:
        out.extend(cloud_voices_for_language(language))
    return out
