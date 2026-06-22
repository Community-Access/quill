"""Curated whisper.cpp model catalog (#617 section 5.2).

Data-driven model tiers with approximate sizes and accessible speed/accuracy/use
descriptions. URLs and hashes are intentionally left for the provider/release
pipeline to fill in (kept data-driven per #617 section 17); this module is the
single place the model manager reads its menu of models from.
"""

from __future__ import annotations

from quill.core.speech.provider import SpeechModelInfo

RECOMMENDED_MODEL_ID = "small"
# A model that supports whisper.cpp tinydiarize (-tdrz) speaker-turn detection.
DIARIZATION_MODEL_ID = "small.en-tdrz"

# whisper.cpp GGML models are published on Hugging Face. Pinned to a specific
# commit (not "main") so a re-upload can't silently swap a model under us, and the
# per-file sha256 below stays valid (the download verifies it — #617 section 8).
# Bump the revision and the hashes together, deliberately.
_WHISPER_CPP_REVISION = "5359861c739e955e79d9a303bcbc70fb988958b1"
_HF_BASE = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/{_WHISPER_CPP_REVISION}"


def _ggml_url(name: str) -> str:
    return f"{_HF_BASE}/ggml-{name}.bin"


WHISPER_CPP_MODELS: tuple[SpeechModelInfo, ...] = (
    SpeechModelInfo(
        id="tiny",
        display_name="Tiny",
        language_mode="multilingual",
        approximate_size_mb=75,
        accuracy_tier="low",
        speed_tier="fast",
        recommended_use="Smallest download. Good for testing and simple voice commands.",
        download_url=_ggml_url("tiny"),
        sha256="be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="base",
        display_name="Base",
        language_mode="multilingual",
        approximate_size_mb=145,
        accuracy_tier="low",
        speed_tier="fast",
        recommended_use="Small download. Better than Tiny; good for quick notes.",
        download_url=_ggml_url("base"),
        sha256="60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="small",
        display_name="Small",
        language_mode="multilingual",
        approximate_size_mb=465,
        accuracy_tier="medium",
        speed_tier="medium",
        recommended_use="Recommended starting point: solid transcription without a huge download.",
        download_url=_ggml_url("small"),
        sha256="1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="small.en-tdrz",
        display_name="Small English with speaker detection",
        language_mode="english",
        approximate_size_mb=465,
        accuracy_tier="medium",
        speed_tier="medium",
        recommended_use=(
            "English only, and marks who is speaking when (speaker turns) in transcripts."
        ),
        # The tinydiarize model lives in its own repo, not ggerganov/whisper.cpp,
        # so it is pinned separately (the old ggerganov URL 404s).
        download_url=(
            "https://huggingface.co/akashmjn/tinydiarize-whisper.cpp/resolve/"
            "d44ba793fc67e509623a88a409723311fa677744/ggml-small.en-tdrz.bin"
        ),
        sha256="ceac3ec06d1d98ef71aec665283564631055fd6129b79d8e1be4f9cc33cc54b4",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="medium",
        display_name="Medium",
        language_mode="multilingual",
        approximate_size_mb=1500,
        accuracy_tier="high",
        speed_tier="slow",
        recommended_use="Higher accuracy. Larger download and slower on older computers.",
        download_url=_ggml_url("medium"),
        sha256="6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="large-v3",
        display_name="Large (v3)",
        language_mode="multilingual",
        approximate_size_mb=3100,
        accuracy_tier="highest",
        speed_tier="slow",
        recommended_use="Best local quality. Very large download and storage requirement.",
        download_url=_ggml_url("large-v3"),
        sha256="64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2",
        license_name="MIT",
    ),
)


def model_by_id(model_id: str) -> SpeechModelInfo | None:
    """Look up a catalog model by id."""
    for model in WHISPER_CPP_MODELS:
        if model.id == model_id:
            return model
    return None


# --------------------------------------------------------------------------- #
# Faster Whisper (CTranslate2) models — S4
#
# Faster Whisper loads CTranslate2 model *repositories* from the Hugging Face
# Hub, not single GGML files. We store the Hub repo id in ``download_url`` (the
# provider passes it to huggingface_hub.snapshot_download). Sizes are the
# approximate on-disk footprint of the CT2 weights.
# --------------------------------------------------------------------------- #

FASTER_WHISPER_RECOMMENDED_MODEL_ID = "small"


def _ct2_repo(name: str) -> str:
    return f"Systran/faster-whisper-{name}"


FASTER_WHISPER_MODELS: tuple[SpeechModelInfo, ...] = (
    SpeechModelInfo(
        id="tiny",
        display_name="Tiny (Faster Whisper)",
        language_mode="multilingual",
        approximate_size_mb=75,
        accuracy_tier="low",
        speed_tier="fast",
        recommended_use="Smallest download. Fastest, lowest accuracy.",
        download_url=_ct2_repo("tiny"),
        revision="d90ca5fe260221311c53c58e660288d3deb8d356",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="base",
        display_name="Base (Faster Whisper)",
        language_mode="multilingual",
        approximate_size_mb=145,
        accuracy_tier="low",
        speed_tier="fast",
        recommended_use="Small and quick; good for short notes.",
        download_url=_ct2_repo("base"),
        revision="ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="small",
        display_name="Small (Faster Whisper)",
        language_mode="multilingual",
        approximate_size_mb=465,
        accuracy_tier="medium",
        speed_tier="fast",
        recommended_use="Recommended: solid accuracy and fast, especially with a GPU.",
        download_url=_ct2_repo("small"),
        revision="536b0662742c02347bc0e980a01041f333bce120",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="medium",
        display_name="Medium (Faster Whisper)",
        language_mode="multilingual",
        approximate_size_mb=1500,
        accuracy_tier="high",
        speed_tier="medium",
        recommended_use="Higher accuracy; comfortable on a GPU or a fast CPU.",
        download_url=_ct2_repo("medium"),
        revision="08e178d48790749d25932bbc082711ddcfdfbc4f",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="large-v3",
        display_name="Large v3 (Faster Whisper)",
        language_mode="multilingual",
        approximate_size_mb=3100,
        accuracy_tier="highest",
        speed_tier="medium",
        recommended_use="Best quality. Large download; a GPU is recommended.",
        download_url=_ct2_repo("large-v3"),
        revision="edaa852ec7e145841d8ffdb056a99866b5f0a478",
        license_name="MIT",
    ),
    SpeechModelInfo(
        id="distil-large-v3",
        display_name="Distil-Large v3 (Faster Whisper, English)",
        language_mode="english",
        approximate_size_mb=1500,
        accuracy_tier="high",
        speed_tier="fast",
        recommended_use=(
            "English-only, near-Large accuracy at roughly half the size and twice the speed."
        ),
        download_url="Systran/faster-distil-whisper-large-v3",
        revision="c3058b475261292e64a0412df1d2681c06260fab",
        license_name="MIT",
    ),
)


def fw_model_by_id(model_id: str) -> SpeechModelInfo | None:
    """Look up a Faster Whisper catalog model by id."""
    for model in FASTER_WHISPER_MODELS:
        if model.id == model_id:
            return model
    return None


# --------------------------------------------------------------------------- #
# Parakeet (NVIDIA NeMo) models — optional, offline, English, GPU-oriented.
#
# Parakeet models are single ``.nemo`` archives on the Hugging Face Hub. We store
# the Hub repo id in ``download_url`` (the provider snapshot-downloads it) and pin
# the commit ``revision`` for supply-chain safety. English-only, high accuracy;
# a GPU is strongly recommended. Both are CC-BY-4.0 (attribution required).
# --------------------------------------------------------------------------- #

PARAKEET_RECOMMENDED_MODEL_ID = "parakeet-tdt-0.6b-v2"

PARAKEET_MODELS: tuple[SpeechModelInfo, ...] = (
    SpeechModelInfo(
        id="parakeet-tdt-0.6b-v2",
        display_name="Parakeet TDT 0.6B v2 (NVIDIA, English)",
        language_mode="english",
        approximate_size_mb=2400,
        accuracy_tier="highest",
        speed_tier="fast",
        recommended_use="Recommended: high-accuracy English with timestamps; fast on a GPU.",
        download_url="nvidia/parakeet-tdt-0.6b-v2",
        revision="1b149a3589351c96ddb101709fe7dd9c7069572f",
        license_name="CC-BY-4.0",
    ),
    SpeechModelInfo(
        id="parakeet-tdt-1.1b",
        display_name="Parakeet TDT 1.1B (NVIDIA, English)",
        language_mode="english",
        approximate_size_mb=4300,
        accuracy_tier="highest",
        speed_tier="medium",
        recommended_use="Largest, highest-accuracy English. Big download; a GPU is recommended.",
        download_url="nvidia/parakeet-tdt-1.1b",
        revision="53276c6469d1f17a1352e30c4d11be3d0d7e9575",
        license_name="CC-BY-4.0",
    ),
)


def parakeet_model_by_id(model_id: str) -> SpeechModelInfo | None:
    """Look up a Parakeet catalog model by id."""
    for model in PARAKEET_MODELS:
        if model.id == model_id:
            return model
    return None


def is_diarization_model(model_id: str) -> bool:
    """True when a model supports speaker-turn detection (whisper.cpp tinydiarize)."""
    return model_id.endswith("-tdrz")


def recommended_model() -> SpeechModelInfo:
    """The model QUILL recommends for a first download."""
    found = model_by_id(RECOMMENDED_MODEL_ID)
    if found is None:  # pragma: no cover - RECOMMENDED_MODEL_ID is always present
        return WHISPER_CPP_MODELS[0]
    return found
