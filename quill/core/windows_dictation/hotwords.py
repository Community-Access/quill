"""Hotwords: My Words learned while listening (dict.md D-28) -- the plumbing, off.

Today only OpenAI is biased towards the person's words (its ``keywords``);
every local model hears My Words and Phrases only *after* recognition, through
the corrector (:func:`quill.core.speech.vocabulary.apply_custom_vocabulary`).
sherpa-onnx can bias a transducer while it decodes -- "Only transducer models
support hotwords", and only with ``modified_beam_search`` -- given a hotwords
file and, for a BPE model, its ``bpe.vocab``.

**Measured not working on what QUILL has.** Nemotron's streaming decoder is
greedy-only, and Parakeet's NeMo hotwords came out upper-cased and garbled
(2026-10-05, dictation design, section 5 B). The realistic route is an English
Zipformer transducer, and dict.md says to *evaluate* it first: a model joins
:data:`~quill.core.windows_dictation.model_types.HOTWORD_MODELS` only when 20
names are recognised 50 percent better than without hotwords, with word errors
on the real-voice benchmark (B-1) no worse.

So this is the plumbing behind a capability flag that defaults off
(:data:`HOTWORDS_ENABLED`): writing the hotwords file in the model's case
(:func:`hotword_lines`), the decoder options a transducer needs
(:func:`decoder_options`, which :func:`~quill.core.windows_dictation.model_loader.build`
accepts), and putting the person's own spelling back afterwards
(:func:`restore_spelling`, the corrector dictation already runs). Turning it
on is a measurement, a catalogue entry and this flag. A pinned test should
recheck the NeMo path on every sherpa-onnx upgrade (the version is pinned
exactly in pyproject.toml for that reason).

wx-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from quill.core.windows_dictation.model_types import HOTWORDS

__all__ = [
    "DEFAULT_SCORE",
    "HOTWORDS_ENABLED",
    "decoder_options",
    "hotword_lines",
    "restore_spelling",
]

#: The capability flag. Off until D-28's evaluation passes on B-1.
HOTWORDS_ENABLED = False
#: sherpa-onnx's default boost.
DEFAULT_SCORE = 1.5


def hotword_lines(words: Iterable[str], *, upper: bool = True) -> list[str]:
    """One hotword per line, in the model's case (the English transducers are
    trained upper-case), each once, blank and over-long entries dropped."""
    lines: list[str] = []
    for word in words:
        text = " ".join(str(word or "").split())
        if not text or len(text) > 60:
            continue
        cased = text.upper() if upper else text
        if cased not in lines:
            lines.append(cased)
    return lines


def decoder_options(
    model: Any,
    folder: Path,
    words: Sequence[str],
    *,
    enabled: bool | None = None,
    score: float = DEFAULT_SCORE,
) -> dict[str, Any]:
    """The extra sherpa-onnx arguments that make *model* listen for *words*:
    ``{}`` unless the flag is on, the model is measured to benefit
    (``hotwords`` in its tasks) and there are words. Writes ``hotwords.txt``
    beside the model."""
    on = HOTWORDS_ENABLED if enabled is None else enabled
    lines = hotword_lines(words)
    if not on or HOTWORDS not in model.tasks or not lines:
        return {}
    hotwords = folder / "hotwords.txt"
    hotwords.write_text("\n".join(lines) + "\n", encoding="utf-8")
    options: dict[str, Any] = {
        "decoding_method": "modified_beam_search",
        "hotwords_file": str(hotwords),
        "hotwords_score": score,
    }
    vocab = folder / "bpe.vocab"
    if vocab.is_file():
        options.update(modeling_unit="bpe", bpe_vocab=str(vocab))
    return options


def restore_spelling(text: str, words: Sequence[str]) -> str:
    """*text* with My Words' own spelling put back ("QUILLVILLE" is QuillVille):
    the corrector every engine's text already goes through."""
    from quill.core.speech.vocabulary import apply_custom_vocabulary

    return apply_custom_vocabulary(text, tuple(words))
