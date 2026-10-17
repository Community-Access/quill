"""Keyword spotting for the command word (dict.md D-27) -- built, not switched on.

D-1 recognises the command word ("QUILL scratch that") by matching the *text*
of a finished phrase (:mod:`~quill.core.windows_dictation.command_mode`), so a
whole phrase must be recognised first. sherpa-onnx's ``KeywordSpotter`` is a
"tiny ASR" that decodes only a listed set of keywords; run on the same 16 kHz
stream, after the reader gate, it hears the command word as it is said.

**Both must agree.** A keyword hit marks the phrase it falls in
(:attr:`RecognizedPhrase.keyword_heard
<quill.core.windows_dictation.parser.RecognizedPhrase.keyword_heard>`), and
the text matcher stays as the confirmation: a phrase is a command only when the
spotter heard the word *and* the text opens with it, which lowers false
triggers. When the spotter is not running the field is ``None`` and the text
matcher decides alone, exactly as before.

**The keywords** are written from the command word, the wake phrase and the
stop phrase (:func:`keyword_phrases`), with a two-word "hey quill" beside a
one-word command word because a name like QUILL may tokenise poorly (dict.md's
own risk note). Each line carries a boosting score and a trigger threshold
(:func:`keyword_lines`), tokenised with sherpa-onnx's ``text2token`` when the
person changes the word.

**Why it is off.** dict.md's acceptance criteria are measurements: under one
false trigger an hour on a 60-minute soak of ordinary dictation that mentions
"Quill" (B-3), 95 percent or more detection after a pause, and under 0.02 of
one thread. The English model (``sherpa-onnx-kws-zipformer-gigaspeech-3.3M``)
has an unverified size and licence, so it is not in the download catalogue.
:data:`KWS_ADOPTED` is ``False`` and :func:`keyword_gate_for` returns ``None``
until the measurements pass, the model is pinned, and the per-word defaults
below are tuned and recorded.

**Measured 2026-10-17 (dictation design record section 35): not adopted.**
The GigaSpeech 3.3M spotter (Apache 2.0) made 1 false trigger in 60 minutes
of LibriSpeech, heard the command word after a pause in 90 percent of 72
synthetic clips, and used 0.031 of one thread: all three criteria missed
(2 an hour, 92 percent and 0.032 at boost 2.0, threshold 0.15).

wx-free. sherpa-onnx is passed in, never imported here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_BOOST",
    "DEFAULT_THRESHOLD",
    "KWS_ADOPTED",
    "KWS_FOLDER",
    "KeywordGate",
    "build_spotter",
    "keyword_gate_for",
    "keyword_lines",
    "keyword_phrases",
    "kws_ready",
    "write_keywords_file",
]

#: Switched on only once the D-27 measurements pass and the model is pinned.
KWS_ADOPTED = False
#: Where a pinned model will live under the shared model store.
KWS_FOLDER = "kws-zipformer-gigaspeech-3.3M"
_MODEL_FILES = ("encoder.onnx", "decoder.onnx", "joiner.onnx", "tokens.txt", "bpe.model")
#: sherpa-onnx's own defaults, until B-1 tunes them per word.
DEFAULT_BOOST = 1.0
DEFAULT_THRESHOLD = 0.25

Tokenize = Callable[[list[str]], list[list[str]]]


def keyword_phrases(prefix: str, wake_phrase: str = "", stop_phrase: str = "") -> list[str]:
    """The keywords to spot, upper-cased as the English model's tokens are,
    each once: the command word (and "hey" before a one-word one), then the
    wake and stop phrases."""
    found: list[str] = []

    def add(text: str) -> None:
        words = " ".join(str(text or "").replace(",", " ").split()).upper()
        if words and words not in found:
            found.append(words)

    add(prefix)
    if len(prefix.split()) == 1:
        add(f"hey {prefix}")
    add(wake_phrase)
    add(stop_phrase)
    return found


def keyword_lines(
    phrases: Sequence[str],
    tokenize: Tokenize,
    *,
    boost: float = DEFAULT_BOOST,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[str]:
    """sherpa-onnx keyword lines: the tokens, ``:boost``, ``#threshold`` and
    ``@`` the phrase itself, which is what the spotter answers with. The
    phrase's spaces become underscores: sherpa-onnx splits the line on spaces,
    so ``@HEY QUILL`` made it look for a token called ``QUILL`` and refuse the
    whole file (found by the first real run, 2026-10-17)."""
    if not phrases:
        return []
    lines = []
    for phrase, tokens in zip(phrases, tokenize(list(phrases)), strict=True):
        joined = " ".join(str(token) for token in tokens)
        label = "_".join(phrase.split())
        lines.append(f"{joined} :{boost:g} #{threshold:g} @{label}")
    return lines


def write_keywords_file(path: Path, lines: Iterable[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _model_folder() -> Path:
    from quill.core.windows_dictation.model_store import downloads_root

    return downloads_root() / KWS_FOLDER


def kws_ready(folder: Path | None = None) -> bool:
    """Adopted, and every model file on this computer."""
    where = folder or _model_folder()
    return KWS_ADOPTED and all((where / name).is_file() for name in _MODEL_FILES)


def build_spotter(sherpa_onnx: Any, folder: Path, keywords_file: Path, *, threads: int = 1) -> Any:
    """sherpa-onnx's keyword spotter for the model in *folder*. One thread: the
    budget is under 0.02 of it."""
    return sherpa_onnx.KeywordSpotter(
        tokens=str(folder / "tokens.txt"),
        encoder=str(folder / "encoder.onnx"),
        decoder=str(folder / "decoder.onnx"),
        joiner=str(folder / "joiner.onnx"),
        keywords_file=str(keywords_file),
        num_threads=threads,
        keywords_score=DEFAULT_BOOST,
        keywords_threshold=DEFAULT_THRESHOLD,
        provider="cpu",
    )


class KeywordGate:
    """The spotter on the dictation stream: :meth:`accept` each block, and
    :meth:`take` at the end of a phrase says whether a keyword was heard in it."""

    def __init__(self, spotter: Any) -> None:
        self._spotter = spotter
        self._stream = spotter.create_stream()
        self._heard = False

    def accept(self, samples: Any) -> None:
        self._stream.accept_waveform(16_000, samples)
        while self._spotter.is_ready(self._stream):
            self._spotter.decode_stream(self._stream)
            if str(self._spotter.get_result(self._stream) or "").strip():
                self._heard = True
                self._spotter.reset_stream(self._stream)

    def take(self) -> bool:
        heard, self._heard = self._heard, False
        return heard


def keyword_gate_for(
    preferences: Any,
    *,
    sherpa_onnx: Any = None,
    folder: Path | None = None,
    ready: Callable[[Path | None], bool] = kws_ready,
) -> KeywordGate | None:
    """The gate for these dictation preferences, or ``None`` -- always ``None``
    until :data:`KWS_ADOPTED`, and whenever the model or a command word is
    missing. Never raises: the text matcher works alone without it."""
    prefix = str(getattr(preferences, "command_prefix", "") or "")
    if not prefix.strip() or not ready(folder):
        return None
    where = folder or _model_folder()
    try:
        if sherpa_onnx is None:
            from quill.core.windows_dictation.local_recognizer import _import_sherpa

            sherpa_onnx = _import_sherpa()
        phrases = keyword_phrases(
            prefix,
            str(getattr(preferences, "wake_phrase", "") or ""),
            str(getattr(preferences, "stop_phrase", "") or ""),
        )

        def tokenize(texts: list[str]) -> list[list[str]]:
            tokens: list[list[str]] = sherpa_onnx.text2token(
                texts,
                tokens=str(where / "tokens.txt"),
                tokens_type="bpe",
                bpe_model=str(where / "bpe.model"),
            )
            return tokens

        keywords = write_keywords_file(where / "keywords.txt", keyword_lines(phrases, tokenize))
        return KeywordGate(build_spotter(sherpa_onnx, where, keywords))
    except Exception:  # noqa: BLE001 - spotting is a refinement, never a blocker
        return None
