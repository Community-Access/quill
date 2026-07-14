"""Static voice catalogs for the offline read-aloud engines (GATE-11 extract).

Pure data plus two pure helpers, split out of :mod:`quill.core.read_aloud` so
the engine module stays within its size budget. ``read_aloud`` re-exports every
name here, so existing imports keep working. wx-free, network-free.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Kokoro (neural, offline)
# ---------------------------------------------------------------------------

KOKORO_VOICES: list[tuple[str, str]] = [
    ("af_heart", "Heart (American Female, warm)"),
    ("af_bella", "Bella (American Female, expressive)"),
    ("af_nicole", "Nicole (American Female, conversational)"),
    ("af_alloy", "Alloy (American Female)"),
    ("af_aoede", "Aoede (American Female)"),
    ("af_jessica", "Jessica (American Female)"),
    ("af_kore", "Kore (American Female)"),
    ("af_nova", "Nova (American Female)"),
    ("af_river", "River (American Female)"),
    ("af_sarah", "Sarah (American Female)"),
    ("af_sky", "Sky (American Female)"),
    ("am_adam", "Adam (American Male, deep)"),
    ("am_echo", "Echo (American Male)"),
    ("am_eric", "Eric (American Male)"),
    ("am_fenrir", "Fenrir (American Male)"),
    ("am_liam", "Liam (American Male)"),
    ("am_michael", "Michael (American Male)"),
    ("am_onyx", "Onyx (American Male)"),
    ("am_puck", "Puck (American Male)"),
    ("am_santa", "Santa (American Male)"),
    ("bf_alice", "Alice (British Female)"),
    ("bf_emma", "Emma (British Female)"),
    ("bf_isabella", "Isabella (British Female)"),
    ("bf_lily", "Lily (British Female)"),
    ("bm_daniel", "Daniel (British Male)"),
    ("bm_fable", "Fable (British Male)"),
    ("bm_george", "George (British Male)"),
    ("bm_lewis", "Lewis (British Male)"),
    # Non-English voices shipped in the same voices-v1.0.bin QUILL already
    # downloads — no extra assets needed. Limited to the languages kokoro-onnx
    # phonemizes well through its bundled eSpeak data (Latin-script + Hindi);
    # Japanese and Mandarin voices exist upstream but need extra G2P packages,
    # so they are deliberately not listed yet.
    ("ef_dora", "Dora (Spanish Female)"),
    ("em_alex", "Alex (Spanish Male)"),
    ("em_santa", "Santa (Spanish Male)"),
    ("ff_siwis", "Siwis (French Female)"),
    ("hf_alpha", "Alpha (Hindi Female)"),
    ("hf_beta", "Beta (Hindi Female)"),
    ("hm_omega", "Omega (Hindi Male)"),
    ("hm_psi", "Psi (Hindi Male)"),
    ("if_sara", "Sara (Italian Female)"),
    ("im_nicola", "Nicola (Italian Male)"),
    ("pf_dora", "Dora (Portuguese Female)"),
    ("pm_alex", "Alex (Portuguese Male)"),
    ("pm_santa", "Santa (Portuguese Male)"),
]

# Official quality grades from hexgrad/Kokoro-82M VOICES.md.
# Grades are descriptive metadata only — never used to filter voice availability.
KOKORO_VOICE_GRADES: dict[str, str] = {
    "af_heart": "A",
    "af_alloy": "C",
    "af_aoede": "C+",
    "af_bella": "A-",
    "af_jessica": "D",
    "af_kore": "C+",
    "af_nicole": "B-",
    "af_nova": "C",
    "af_river": "D",
    "af_sarah": "C+",
    "af_sky": "C-",
    "am_adam": "F+",
    "am_echo": "D",
    "am_eric": "D",
    "am_fenrir": "C+",
    "am_liam": "D",
    "am_michael": "C+",
    "am_onyx": "D",
    "am_puck": "C+",
    "am_santa": "D-",
    "bf_alice": "D",
    "bf_emma": "B-",
    "bf_isabella": "C",
    "bf_lily": "D",
    "bm_daniel": "D",
    "bm_fable": "C",
    "bm_george": "C",
    "bm_lewis": "D+",
    # Spanish and Portuguese voices carry no overall grade in VOICES.md.
    "ef_dora": "unrated",
    "em_alex": "unrated",
    "em_santa": "unrated",
    "ff_siwis": "B-",
    "hf_alpha": "C",
    "hf_beta": "C",
    "hm_omega": "C",
    "hm_psi": "C",
    "if_sara": "C",
    "im_nicola": "C",
    "pf_dora": "unrated",
    "pm_alex": "unrated",
    "pm_santa": "unrated",
}

KOKORO_ACCENTS: dict[str, str] = {
    "af": "American English",
    "am": "American English",
    "bf": "British English",
    "bm": "British English",
    "ef": "Spanish",
    "em": "Spanish",
    "ff": "French",
    "hf": "Hindi",
    "hm": "Hindi",
    "if": "Italian",
    "im": "Italian",
    "pf": "Portuguese (Brazil)",
    "pm": "Portuguese (Brazil)",
}

# eSpeak language codes kokoro-onnx phonemizes with, keyed by the voice-id
# language letter (the first character: a=American, b=British, e=Spanish, ...).
# The same letter is the KPipeline lang_code in the kokoro+torch fallback.
KOKORO_LANG_BY_LETTER: dict[str, str] = {
    "a": "en-us",
    "b": "en-gb",
    "e": "es",
    "f": "fr-fr",
    "h": "hi",
    "i": "it",
    "p": "pt-br",
}


def kokoro_lang_for_voice(voice: str) -> str:
    """The eSpeak language code kokoro-onnx needs for *voice* (default en-us)."""
    return KOKORO_LANG_BY_LETTER.get(voice[:1].lower(), "en-us")


# ---------------------------------------------------------------------------
# eSpeak NG
# ---------------------------------------------------------------------------

ESPEAK_ENGLISH_VOICES: list[tuple[str, str]] = [
    # 8 English definition files in the eSpeak NG data (lang/gmw/en*)
    ("en-gb", "English (British)"),
    ("en-us", "English (American)"),
    ("en-029", "English (Caribbean)"),
    ("en-gb-scotland", "English (Scottish)"),
    ("en-gb-x-gbclan", "English (Lancashire)"),
    ("en-gb-x-gbcwmd", "English (West Midlands)"),
    ("en-gb-x-rp", "English (Received Pronunciation)"),
    ("en-us-nyc", "English (New York City)"),
]

# Non-English eSpeak NG languages QUILL lists. The pinned espeak-ng.msi ships
# the complete upstream espeak-ng-data directory, so these definition files are
# present in both the bundled and on-demand installs. Kept to the same language
# set as the Kokoro catalog so the multilingual story is consistent; eSpeak
# itself supports far more (a follow-up can widen this).
ESPEAK_WORLD_VOICES: list[tuple[str, str]] = [
    ("es", "Spanish (Spain)"),
    ("es-419", "Spanish (Latin American)"),
    ("fr-fr", "French (France)"),
    ("hi", "Hindi"),
    ("it", "Italian"),
    ("pt-br", "Portuguese (Brazil)"),
    ("pt", "Portuguese (Portugal)"),
]

# Generic voice characters appended as ``accent+variant`` (e.g. ``en-gb+m1``).
# All entries verified in the bundled eSpeak NG voices/!v directory.
ESPEAK_VARIANTS: list[tuple[str, str]] = [
    ("", "Default"),
    ("m1", "Male 1"),
    ("m2", "Male 2"),
    ("m3", "Male 3"),
    ("m4", "Male 4"),
    ("m5", "Male 5"),
    ("f1", "Female 1"),
    ("f2", "Female 2"),
    ("f3", "Female 3"),
    ("f4", "Female 4"),
    ("whisper", "Whisper"),
    ("whisperf", "Whisper (feminine)"),
    ("klatt", "Klatt"),
    ("croak", "Croak"),
    ("grandma", "Grandma"),
    ("grandpa", "Grandpa"),
    ("Tweaky", "Tweaky (robotic)"),
    ("UniRobot", "UniRobot"),
]

ESPEAK_ACCENTS: dict[str, str] = {
    "en": "English",
    "en-us": "American English",
    "en-gb": "British English",
    "en-au": "Australian English",
    "en-ca": "Canadian English",
    "en-in": "Indian English",
    "en-sc": "Scottish English",
    "en-wls": "Welsh English",
    "en-rp": "British English",
    "en-gb-x-rp": "British English",
}

# ---------------------------------------------------------------------------
# Piper (neural, offline)
# ---------------------------------------------------------------------------

PIPER_VOICES: list[tuple[str, str]] = [
    # British English
    ("en_GB-alan-low", "Alan (British, low)"),
    ("en_GB-alan-medium", "Alan (British, medium)"),
    ("en_GB-alba-medium", "Alba (British, medium)"),
    ("en_GB-aru-medium", "Aru (British, medium)"),
    ("en_GB-cori-high", "Cori (British, high)"),
    ("en_GB-cori-medium", "Cori (British, medium)"),
    ("en_GB-jenny_dioco-medium", "Jenny Dioco (British, medium)"),
    ("en_GB-northern_english_male-medium", "Northern English Male (British, medium)"),
    ("en_GB-semaine-medium", "Semaine (British, medium)"),
    ("en_GB-southern_english_female-low", "Southern English Female (British, low)"),
    ("en_GB-vctk-medium", "VCTK (British, medium)"),
    # American English
    ("en_US-amy-low", "Amy (US, low)"),
    ("en_US-amy-medium", "Amy (US, medium)"),
    ("en_US-arctic-medium", "Arctic (US, medium)"),
    ("en_US-bryce-medium", "Bryce (US, medium)"),
    ("en_US-danny-low", "Danny (US, low)"),
    ("en_US-hfc_female-medium", "HFC Female (US, medium)"),
    ("en_US-hfc_male-medium", "HFC Male (US, medium)"),
    ("en_US-joe-medium", "Joe (US, medium)"),
    ("en_US-john-medium", "John (US, medium)"),
    ("en_US-kathleen-low", "Kathleen (US, low)"),
    ("en_US-kristin-medium", "Kristin (US, medium)"),
    ("en_US-kusal-medium", "Kusal (US, medium)"),
    ("en_US-l2arctic-medium", "L2Arctic (US, medium)"),
    ("en_US-lessac-high", "Lessac (US, high)"),
    ("en_US-lessac-low", "Lessac (US, low)"),
    ("en_US-lessac-medium", "Lessac (US, medium)"),
    ("en_US-libritts-high", "LibriTTS (US, high)"),
    ("en_US-libritts_r-medium", "LibriTTS R (US, medium)"),
    ("en_US-ljspeech-high", "LJSpeech (US, high)"),
    ("en_US-ljspeech-medium", "LJSpeech (US, medium)"),
    ("en_US-norman-medium", "Norman (US, medium)"),
    ("en_US-reza_ibrahim-medium", "Reza Ibrahim (US, medium)"),
    ("en_US-ryan-high", "Ryan (US, high)"),
    ("en_US-ryan-low", "Ryan (US, low)"),
    ("en_US-ryan-medium", "Ryan (US, medium)"),
    ("en_US-sam-medium", "Sam (US, medium)"),
    # Italian — both voices published in rhasspy/piper-voices (it/it_IT).
    ("it_IT-paola-medium", "Paola (Italian, medium)"),
    ("it_IT-riccardo-x_low", "Riccardo (Italian, x_low)"),
]

# Accent labels for the Piper catalog, keyed by voice-id language prefix.
PIPER_ACCENTS_BY_LANG: dict[str, str] = {
    "en_GB": "British English",
    "en_US": "American English",
    "it_IT": "Italian",
}


def piper_voice_download_urls(voice_id: str) -> tuple[str, str] | None:
    """The HuggingFace (.onnx, .onnx.json) URLs for a catalog voice id.

    Voice ids follow ``<lang>_<REGION>-<name>-<quality>`` for any language
    (``en_US-amy-low``, ``it_IT-paola-medium``). Returns ``None`` for ids that
    do not match, so callers can show a clear error instead of a broken URL.
    """
    m = re.match(r"^([a-z]{2,3}_[A-Z]{2,3})-([^-]+)-(\w+)$", voice_id)
    if m is None:
        return None
    lang_code, voice_name, quality = m.group(1), m.group(2), m.group(3)
    lang_family = lang_code.split("_")[0]
    base = (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main"
        f"/{lang_family}/{lang_code}/{voice_name}/{quality}"
    )
    return f"{base}/{voice_id}.onnx", f"{base}/{voice_id}.onnx.json"
