"""The optional speech models dictation can download: what each is, and where from.

**Dictation works the moment QUILL or QUILL Lite is installed.** Moonshine tiny
and Whisper tiny ship inside both installers and every portable copy and stay
the default (:mod:`quill.core.windows_dictation.engines`). The models here are
extras for better accuracy -- the same local models VS Code's dictation offers,
and the rest of the Whisper family -- downloaded only when somebody chooses one
in Dictation Settings, Speech Models. Never on first run, never in the
background, never the default: a downloaded model becomes the engine only when
the person chooses it in the Speech engine list.

**The order is our suggestion, not a measurement** (Jeff, 2026-10-05): VS
Code's set first, Nemotron as the suggested download because it is VS Code's
default, then the rest of Whisper grouped by English-only and many-languages,
small to large. Every number in :attr:`DownloadableModel.accuracy` names the
published source it came from.

**Every entry is pinned:** a Hugging Face repository at a fixed commit (never
``main``) and, for each file, its exact size and SHA-256. Hugging Face publishes
the SHA-256 of every large file (its LFS object id); the small ones were hashed
by downloading them on 2026-10-05, and every file of Nemotron, both Parakeets,
Moonshine base and Whisper base, small, medium and turbo was downloaded whole
and matched (dict.md 4.5).

**CPU only.** Every file is an int8 (or 8-bit ``.ort``) CPU build, run by
sherpa-onnx's CPU execution provider. Nothing here needs a graphics card.

Pure data and wx-free; :mod:`~quill.core.windows_dictation.model_store` does the
downloading and :mod:`~quill.core.windows_dictation.model_loader` the loading.
"""

from __future__ import annotations

from quill.core.windows_dictation.model_catalog_whisper import WHISPER_FAMILY, WHISPER_VS_CODE
from quill.core.windows_dictation.model_types import (
    CPU_ONLY,
    GROUPS,
    SHERPA_SOURCE,
    STRONG,
    DownloadableModel,
    DownloadFile,
    file,
    megabytes,
)

__all__ = [
    "CATALOGUE",
    "CPU_ONLY",
    "GROUPS",
    "DownloadFile",
    "DownloadableModel",
    "catalogue_ids",
    "downloadable",
    "megabytes",
]

_NVIDIA_LICENCE = (
    "https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/"
)

CATALOGUE: tuple[DownloadableModel, ...] = (
    DownloadableModel(
        id="nemotron",
        name="NVIDIA Nemotron 3.5 ASR Streaming 0.6B",
        good_for="Suggested download. Excellent for live dictation; VS Code's default.",
        description=(
            "NVIDIA's streaming model, the one VS Code's dictation downloads. It is built "
            "to recognise while you speak, writes capitals itself, and understands "
            "English and Spanish. About 680 MB. " + CPU_ONLY
        ),
        group=GROUPS[0],
        kind="nemotron",
        languages=("en", "es"),
        works_best_on=STRONG,
        accuracy=(
            "NVIDIA's model card: word error rate 7.91 percent on FLEURS English and "
            "4.11 percent on FLEURS Spanish (es-419), at the 1.12-second chunk size this "
            "download uses (huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)."
        ),
        repo="csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-1120ms-int8-2026-06-11",
        commit="cba1c96ca5ef0e8393b50584ae153a79145dc492",
        files=(
            file(
                "encoder.int8.onnx",
                "encoder",
                657_601_521,
                "2fff2166acaa535bd969fb223c1f0783d71029f143cb298bc54c2afe85abf772",
            ),
            file(
                "decoder.int8.onnx",
                "decoder",
                14_978_075,
                "19f9c98fc6d0a2c33a65a43b36fdb2e914c26c0aa9764be3aebc502a1e982fb0",
            ),
            file(
                "joiner.int8.onnx",
                "joiner",
                9_504_438,
                "4101c7c679a0bc30483794b27a059e34e79232aa2068d78d51231a22c8b0d7ce",
            ),
            file(
                "tokens.txt",
                "tokens",
                131_440,
                "729cc103155bafa785f9cd45746cd41cabe97eab7182fc04d594129587958f8a",
            ),
        ),
        licence="NVIDIA OpenMDW-1.1",
        licence_url="https://openmdw.ai/license/1-1/",
        source=SHERPA_SOURCE,
        cost_factor=8.0,
        folder="nemotron-3.5-asr-streaming-int8",
        suggested=True,
    ),
    DownloadableModel(
        id="parakeet_unified",
        name="NVIDIA Parakeet Unified 0.6B",
        good_for="May give slightly better final text in some conditions. English only.",
        description=(
            "NVIDIA's newest English Parakeet, trained to work both while you speak "
            "and on a finished phrase; dictation uses it on each finished phrase. "
            "Punctuation and capitals included. About 660 MB. " + CPU_ONLY
        ),
        group=GROUPS[0],
        kind="nemo_transducer",
        languages=("en",),
        works_best_on=STRONG,
        accuracy=(
            "NVIDIA's model card: word error rate 1.63 percent on LibriSpeech test-clean "
            "and 3.11 percent on test-other, on finished phrases "
            "(huggingface.co/nvidia/parakeet-unified-en-0.6b)."
        ),
        repo="csukuangfj2/sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming",
        commit="8c3a10fb13408c7a7054f6898958bf1c64a8d6c7",
        files=(
            file(
                "encoder.int8.onnx",
                "encoder",
                654_040_552,
                "6716910b7a0833997fec7a410494c995d70124001a0e9b66d6370d6aced577e0",
            ),
            file(
                "decoder.int8.onnx",
                "decoder",
                7_257_753,
                "a5e223392c90e75f8144cdb5eb95af7625db389e39edef2bd1a9c872b3298fe6",
            ),
            file(
                "joiner.int8.onnx",
                "joiner",
                1_735_860,
                "869f43f7d24595c55581ad3bf249a935fb8a71389fbdaa7504b9f46f93140f8a",
            ),
            file(
                "tokens.txt",
                "tokens",
                8_952,
                "dc0b4584ab2e4ddbf888425c076c61b736e7356a015250db7d307e6f1a8188ff",
            ),
        ),
        licence="NVIDIA Open Model License",
        licence_url=_NVIDIA_LICENCE,
        source=SHERPA_SOURCE,
        cost_factor=6.1,
        folder="parakeet-unified-en-0.6b-int8",
    ),
    DownloadableModel(
        id="parakeet",
        name="NVIDIA Parakeet TDT 0.6B v3",
        good_for="Excellent recognition of each finished phrase. English and Spanish.",
        description=(
            "NVIDIA's Parakeet TDT, version 3: it recognises each phrase after you "
            "pause, with punctuation and capitals, and knows English, Spanish and 23 "
            "other European languages. About 670 MB. " + CPU_ONLY
        ),
        group=GROUPS[0],
        kind="nemo_transducer",
        languages=("en", "es"),
        works_best_on=STRONG,
        accuracy=(
            "NVIDIA's model card: word error rate 4.85 percent on FLEURS English, 3.45 "
            "percent on FLEURS Spanish (es-419) and 4.39 percent on Multilingual "
            "LibriSpeech Spanish (huggingface.co/nvidia/parakeet-tdt-0.6b-v3)."
        ),
        repo="csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
        commit="2bda32ec70b097a55adaa07d9a7173915b43cc78",
        files=(
            file(
                "encoder.int8.onnx",
                "encoder",
                652_184_281,
                "acfc2b4456377e15d04f0243af540b7fe7c992f8d898d751cf134c3a55fd2247",
            ),
            file(
                "decoder.int8.onnx",
                "decoder",
                11_845_275,
                "179e50c43d1a9de79c8a24149a2f9bac6eb5981823f2a2ed88d655b24248db4e",
            ),
            file(
                "joiner.int8.onnx",
                "joiner",
                6_355_277,
                "3164c13fc2821009440d20fcb5fdc78bff28b4db2f8d0f0b329101719c0948b3",
            ),
            file(
                "tokens.txt",
                "tokens",
                93_939,
                "d58544679ea4bc6ac563d1f545eb7d474bd6cfa467f0a6e2c1dc1c7d37e3c35d",
            ),
        ),
        licence="CC BY 4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/",
        source=SHERPA_SOURCE,
        cost_factor=6.3,
        folder="parakeet-tdt-0.6b-v3-int8",
    ),
    *WHISPER_VS_CODE,
    *WHISPER_FAMILY,
    DownloadableModel(
        id="moonshine_base",
        name="Moonshine base",
        good_for="A light step up from the built-in Moonshine. English only.",
        description=(
            "The bigger sister of the built-in Moonshine: a little more accurate in "
            "English and still quick on a modest computer; it punctuates itself. "
            "About 141 MB. " + CPU_ONLY
        ),
        group=GROUPS[3],
        kind="moonshine_v2",
        languages=("en",),
        works_best_on="Any computer that runs the built-in Moonshine well.",
        accuracy=(
            "Moonshine AI's model table: 10.07 percent average word errors across the "
            "Open ASR Leaderboard's English sets, against 12.66 for tiny "
            "(github.com/moonshine-ai/moonshine, docs/models/available-models.md)."
        ),
        repo="csukuangfj2/sherpa-onnx-moonshine-base-en-quantized-2026-02-27",
        commit="8f4d6c58c03d40bcea40043bb7120a878f2bbef6",
        files=(
            file(
                "encoder_model.ort",
                "encoder",
                31_326_816,
                "7c66495948d0d08ec1af454cd4b5514862ae6511e94712a60e6d83eaec8dc8cf",
            ),
            file(
                "decoder_model_merged.ort",
                "decoder",
                109_424_400,
                "d9d7b333af34bc552580576ddcf248a1c6c839e0d3b43b09afb9376ed009899d",
            ),
            file(
                "tokens.txt",
                "tokens",
                549_350,
                "2870d843e14c1e187bf1913a521562a63b53933814bd7f2145120468f494a049",
            ),
            file(
                "LICENSE",
                "licence",
                13_344,
                "6148d7574a6554b7379b633cfd4c4fe5840c3f548d13bc83e00b52dc6fa00abd",
            ),
        ),
        licence="MIT (English Moonshine models)",
        licence_url="https://github.com/moonshine-ai/moonshine/blob/main/LICENSE",
        source=SHERPA_SOURCE,
        cost_factor=1.5,
        folder="moonshine-base-en",
    ),
)

_BY_ID = {model.id: model for model in CATALOGUE}


def catalogue_ids() -> tuple[str, ...]:
    return tuple(_BY_ID)


def downloadable(model_id: object) -> DownloadableModel | None:
    """The catalogue entry *model_id* names, or ``None``."""
    return _BY_ID.get(str(model_id or "").strip().lower())
