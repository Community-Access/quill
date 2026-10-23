"""The Whisper family, as optional downloads: English-only and many-language.

Split out of :mod:`~quill.core.windows_dictation.model_catalog` (GATE-11). All
are sherpa-onnx's int8 CPU exports of OpenAI's and Hugging Face's (Distil-Whisper)
models; the bundled tiny and tiny.en are not here because they ship inside
both installers. sherpa-onnx rather than whisper.cpp: on the same recordings
and one thread it ran Whisper base, small and medium about five times faster
(dict.md 4.5), and it is the runtime the bundled engines already use.

**English-only or many languages.** The ``.en`` models are more accurate in
English than a many-language model of the same size; the many-language ones
also dictate Spanish. Only base.en is left of the English-only family: small.en,
medium.en and the three English Distil-Whisper models were removed on
2026-10-22, because Parakeet Unified beat each of them on accuracy and speed
in real recordings (``removed_models.py``; dictation design, sections 36-37).

Pure data and wx-free.
"""

from __future__ import annotations

from quill.core.windows_dictation.model_types import (
    CPU_ONLY,
    GROUPS,
    MODEST,
    SHERPA_SOURCE,
    STRONG,
    TOO_BIG,
    DownloadableModel,
    file,
)

__all__ = ["WHISPER_FAMILY", "WHISPER_VS_CODE"]

_WHISPER_PAPER = "arxiv.org/abs/2212.04356"
_DISTIL_CARD = "huggingface.co/distil-whisper/distil-small.en"
_TOKENS_MULTI = "b34b360dbb493e781e479794586d661700670d65564001f23024971d1f2fa126"
_TOKENS_EN = "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930"


def _librispeech(rate: str) -> str:
    return (
        f"OpenAI's Whisper paper, Appendix D: {rate} percent word errors on LibriSpeech "
        f"test-clean, greedy decoding ({_WHISPER_PAPER})."
    )


def _whisper(
    model_id: str,
    size: str,
    *,
    english: bool,
    good_for: str,
    description: str,
    accuracy: str,
    commit: str,
    encoder: tuple[int, str],
    decoder: tuple[int, str],
    cost: float,
    works_best_on: str,
    group: str = "",
    name: str = "",
) -> DownloadableModel:
    """A Whisper entry: the sherpa-onnx export ``<size>-encoder.int8.onnx`` etc."""
    distil = size.startswith("distil")
    tokens = (835_554, _TOKENS_EN) if english else (816_730, _TOKENS_MULTI)
    return DownloadableModel(
        id=model_id,
        name=name or ("Distil-Whisper " if distil else "Whisper ") + size.removeprefix("distil-"),
        good_for=good_for,
        description=f"{description} {CPU_ONLY}",
        group=group or ("Whisper, English only" if english else "Whisper, many languages"),
        kind="whisper",
        languages=("en",) if english else ("en", "es"),
        works_best_on=works_best_on,
        accuracy=accuracy,
        repo=f"csukuangfj/sherpa-onnx-whisper-{size}",
        commit=commit,
        files=(
            file(f"{size}-encoder.int8.onnx", "encoder", *encoder),
            file(f"{size}-decoder.int8.onnx", "decoder", *decoder),
            file(f"{size}-tokens.txt", "tokens", *tokens),
        ),
        licence="MIT",
        licence_url=(
            "https://github.com/huggingface/distil-whisper/blob/main/LICENSE"
            if distil
            else "https://github.com/openai/whisper/blob/main/LICENSE"
        ),
        source=SHERPA_SOURCE,
        cost_factor=cost,
        folder=f"whisper-{size}-int8",
    )


#: Whisper small and base: VS Code's own Whisper choices, listed with its models.
WHISPER_VS_CODE: tuple[DownloadableModel, ...] = (
    _whisper(
        "whisper_small",
        "small",
        english=False,
        group=GROUPS[0],
        good_for="A VS Code alternative: good accuracy, English and Spanish.",
        description=(
            "OpenAI's Whisper small, many languages: clearly better than the built-in "
            "tiny on accents, names and Spanish, and it punctuates itself. About 375 MB."
        ),
        accuracy=(
            "OpenAI's Whisper paper, Appendix D: 3.4 percent word errors on LibriSpeech "
            "test-clean (tiny: 7.6) and 10.3 percent on Common Voice 9 Spanish (tiny: "
            f"30.3), greedy decoding ({_WHISPER_PAPER})."
        ),
        commit="8f3c18b358db4d1f2fc1eae49d75cd20989e4309",
        encoder=(112_442_483, "4cbe7b22fa9026b843b60a68640c747de05bafb1a11b57edc0e66c232d9f33a9"),
        decoder=(262_226_114, "acad50b5c782696e91b55914cc5ab4f756f1532f76e22aa6fc615f39fb69a8ee"),
        cost=24.0,
        works_best_on=STRONG,
    ),
    _whisper(
        "whisper_base",
        "base",
        english=False,
        group=GROUPS[0],
        good_for="A VS Code alternative: moderate accuracy, English and Spanish.",
        description=(
            "OpenAI's Whisper base, many languages: a step up from the built-in tiny, "
            "most of all in Spanish, and it punctuates itself. About 160 MB."
        ),
        accuracy=(
            "OpenAI's Whisper paper, Appendix D: 5.0 percent word errors on LibriSpeech "
            "test-clean (tiny: 7.6) and 19.6 percent on Common Voice 9 Spanish (tiny: "
            f"30.3), greedy decoding ({_WHISPER_PAPER})."
        ),
        commit="bb53ee204431c90d314c1cc08d28d23e5b7927cc",
        encoder=(29_120_534, "0b8fb1304b6109976038efff5ace81720e00386f3ff6b54ee8c75291ca0a1e11"),
        decoder=(130_672_026, "9759d217388a01b3a4c7c15533201067b48ae819c4daafc8624e64b9409dc02d"),
        # Real speech, 2026-10-22 (English FLEURS, against Moonshine tiny); was 6.8.
        cost=7.0,
        works_best_on=MODEST,
    ),
)

#: The rest of the family: base.en, then many-language, small to large.
WHISPER_FAMILY: tuple[DownloadableModel, ...] = (
    _whisper(
        "whisper_base_en",
        "base.en",
        english=True,
        good_for="Light and quick, a little more accurate in English than base.",
        description=(
            "Whisper base, English only. English-only models are more accurate in "
            "English than the many-language one of the same size. About 161 MB."
        ),
        accuracy=_librispeech("4.2"),
        commit="59eea950fc76df2453efb57e6c0fd334548e8ffe",
        encoder=(29_120_534, "ef6b936f4c9b1d90a3b68634b60c4ed8576b26172b33c2535ec0e933c9edb823"),
        decoder=(130_669_978, "f7162ad6db2dbef16cfaeaa7f945b9d7dd9c1b8d472f6aca82f2273d185e4d41"),
        # Real speech, 2026-10-22 (English FLEURS run, against Moonshine tiny); was 6.8.
        cost=4.3,
        works_best_on=MODEST,
    ),
    _whisper(
        "whisper_medium",
        "medium",
        english=False,
        good_for="Best for accuracy when you can wait. English and Spanish.",
        description="Whisper medium, many languages. About 946 MB.",
        accuracy=(
            "OpenAI's Whisper paper: 2.9 percent on LibriSpeech test-clean and 6.9 "
            f"percent on Common Voice 9 Spanish ({_WHISPER_PAPER})."
        ),
        commit="8c31d28503847560985df21f90e14f0c736e075e",
        encoder=(374_196_283, "1c54582b4d829de0089f6cb63bbbdb3bf7555398bacaf855fbecf1a84dfd193e"),
        decoder=(571_059_257, "595d00a338a365a7bfa0ca7f296cabc639583bef770ab6130df90f49a6412747"),
        cost=56.0,
        works_best_on=TOO_BIG,
    ),
    _whisper(
        "whisper_turbo",
        "turbo",
        english=False,
        name="Whisper large-v3-turbo",
        good_for="Large-v3 quality, much faster than large-v3. English and Spanish.",
        description="OpenAI's Whisper large-v3-turbo, many languages. About 1.0 GB.",
        accuracy=(
            "OpenAI publishes no word error rate for turbo; its model card says it is "
            "much faster than large-v3 with a minor drop in quality "
            "(huggingface.co/openai/whisper-large-v3-turbo)."
        ),
        commit="2ca6ff69fc878651b770880507669577ac41c2ff",
        encoder=(674_716_297, "b02dcdf54f348741e93fe732b67d933c8dcb6735655f710640143081db38878b"),
        decoder=(361_080_764, "20accd02388482eb3a46bd615631adfdc85e1eb2c7db9ea3f02a40ffe6b81547"),
        cost=78.0,
        works_best_on=TOO_BIG,
    ),
    _whisper(
        "whisper_large_v3",
        "large-v3",
        english=False,
        good_for="The most accurate Whisper. Very slow on most computers.",
        description="OpenAI's Whisper large-v3, many languages. About 1.8 GB.",
        accuracy=(
            "The Distil-Whisper model card: 8.4 percent average word errors on short "
            f"recordings, the best of the Whisper family it compares ({_DISTIL_CARD})."
        ),
        commit="2a6507094dd6020d939d78e3f1834a1d06267fca",
        encoder=(766_671_985, "d531cf17248acc43e8c09b472a0877055e770877857a5332fc1304b36534ec85"),
        decoder=(1_008_265_203, "ebc6bfd88e162a46cb3edee8a7e727e1dcbc65cabecb19e2573695e4d495e1af"),
        cost=150.0,
        works_best_on=TOO_BIG,
    ),
)
