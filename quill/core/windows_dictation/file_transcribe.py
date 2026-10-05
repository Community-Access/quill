"""Transcribe a Recording: a recording into text, in the background.

The same pipeline live dictation uses, fed from a file instead of a microphone
(the owner's request, 2026-10-05: "pass a mp3 and get it transcribed in the
background as a part of the dictation logic")::

    file -> decode, 16 kHz mono (audio_file.py) -> voice detection (Silero)
         -> speech engine, a phrase at a time -> normaliser and composer
         -> paragraphs, with optional timestamps

* **Decoding** is :mod:`~quill.core.windows_dictation.audio_file`: libsndfile,
  then Windows Media Foundation, then ffmpeg where there is one.
* **Phrases** are found by the Silero voice detector dictation already ships
  (``local_recognizer._vad``), so a recording is cut where its speakers pause,
  exactly as dictation cuts a talker.
* **The engines** are dictation's: the built-in Moonshine and Whisper, any
  downloaded model (``local_recognizer.transcribe``, with its loaded-model
  cache and its noise filter), or OpenAI with the person's own key
  (``openai_transcribe.transcribe_phrase``, the same endpoint dictation uses,
  sent about a minute at a time so every request stays far inside OpenAI's
  25 MB limit).
* **The text** goes through dictation's own tidying -- filler removal when
  Dictation Settings has it on, My Words and Phrases corrections, the
  composer's spacing and capitals, and the full stop a breath put in taken back
  when the next phrase carries on -- but **not** its commands: "new paragraph"
  spoken in a recording is two words, unless the person checks Obey spoken
  punctuation and commands (:attr:`FileJob.obey_commands`).
* **Paragraphs** break where the recording pauses for two seconds or more, and
  at the next pause after two minutes of unbroken talk. Each may start with its
  time in the recording, ``[00:01:23]``.

Everything here runs on a worker thread and never touches the interface:
progress, cancelling and the finished text go through the callables passed in.
wx-free, and every heavy piece -- decoder, voice detector, engine -- is
injectable, so the tests run with fakes.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from quill.core.error_codes import CodedError
from quill.core.windows_dictation.audio_file import RATE, AudioSource, open_audio
from quill.core.windows_dictation.composer import compose
from quill.core.windows_dictation.editing import _CONTINUATIONS
from quill.core.windows_dictation.options import clean_phrase
from quill.core.windows_dictation.parser import Piece, RecognizedPhrase, parse, words_from_text
from quill.core.windows_dictation.vocabulary import Command, vocabulary_for

__all__ = [
    "PARAGRAPH_PAUSE",
    "FileJob",
    "FileTranscribeError",
    "FileTranscriber",
    "FileTranscript",
    "Paragraph",
    "Segment",
    "TranscriptionCancelled",
    "done_sentence",
    "plain",
    "timestamp",
]

#: A pause this long (seconds) starts a new paragraph.
PARAGRAPH_PAUSE = 2.0
#: After this much talk without a long pause, the next pause of any length does.
_LONGEST_PARAGRAPH = 120.0
#: OpenAI is sent this much speech at a time, at most: 60 s of 16 kHz 16-bit
#: WAV is under 2 MB, far inside its 25 MB limit, and short enough that a
#: failed request costs little to send again.
_CLOUD_UNIT_SECONDS = 60.0
#: Between joined phrases in one OpenAI request, at most this much quiet.
_JOIN_GAP_SECONDS = 0.3
_PAUSE_SECONDS = 0.8
_WINDOW = 512  # Silero's window at 16 kHz
_WORD = re.compile(r"[a-z0-9']+")
_GLUED_CURRENCY = re.compile(r"(?<=[a-z])(?=[$\u00a3\u20ac]\d)")


class FileTranscribeError(CodedError):
    """A recording could not be transcribed. The message is a sentence."""

    code = "QUILL-DICTATION-FILE-FAILED"


class TranscriptionCancelled(CodedError):
    """The person stopped the transcription."""

    code = "QUILL-DICTATION-FILE-CANCELLED"


@dataclass(frozen=True, slots=True)
class FileJob:
    """One recording and every choice the dialog made for it."""

    path: Path
    #: An engine id (``moonshine``, ``parakeet``...) or ``openai:<model>``.
    model: str
    language: str = "en"
    timestamps: bool = False
    obey_commands: bool = False
    remove_fillers: bool = False
    dash: str = "em"
    #: ``new`` (a new document) or ``cursor``.
    destination: str = "new"
    #: My Words and Phrases, for OpenAI's ``keywords``.
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Segment:
    """One phrase the voice detector found: where it starts, and its sound."""

    start: int  # in samples from the start of the recording
    samples: Any

    @property
    def end(self) -> int:
        return self.start + len(self.samples)


@dataclass(frozen=True, slots=True)
class Paragraph:
    start: float  # seconds into the recording
    text: str


def plain(error: BaseException) -> str:
    """*error*'s sentence, without the ``[QUILL-...]`` code a coded error prints."""
    if error.args and isinstance(error.args[0], str) and error.args[0].strip():
        return error.args[0].strip()
    return str(error) or type(error).__name__


def timestamp(seconds: float) -> str:
    """``[00:01:23]``: hours, minutes and seconds into the recording."""
    whole = max(0, int(seconds))
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


@dataclass(frozen=True, slots=True)
class FileTranscript:
    """What came out, and how long it took."""

    paragraphs: tuple[Paragraph, ...]
    audio_seconds: float
    elapsed_seconds: float
    #: A sentence when a downloaded model gave way to the built-in one.
    notice: str = ""

    def text(self, timestamps: bool = False) -> str:
        rows = [
            f"{timestamp(paragraph.start)} {paragraph.text}" if timestamps else paragraph.text
            for paragraph in self.paragraphs
        ]
        return "\n\n".join(rows)

    @property
    def words(self) -> int:
        return sum(len(paragraph.text.split()) for paragraph in self.paragraphs)


def done_sentence(name: str, transcript: FileTranscript) -> str:
    """``Transcribed meeting.mp3: 12 minutes, 1,804 words, in 3 minutes.``"""
    from quill.core.windows_dictation.file_models import spoken_length

    words = transcript.words
    if not words:
        return f"{name} was read to the end, but no speech was found in it."
    plural = "s" if words != 1 else ""
    took = spoken_length(transcript.elapsed_seconds)
    return (
        f"Transcribed {name}: {spoken_length(transcript.audio_seconds)}, "
        f"{words:,} word{plural}, in {took}."
    )


class Segmenter(Protocol):
    def accept(self, samples: Any) -> list[Segment]: ...

    def finish(self) -> list[Segment]: ...


class _SileroSegmenter:
    """Dictation's voice detector, fed a file instead of a microphone."""

    def __init__(self, vad: Any) -> None:
        import numpy as np

        self._vad = vad
        self._pending = np.zeros(0, dtype=np.float32)

    def _drain(self) -> list[Segment]:
        import numpy as np

        out: list[Segment] = []
        while not self._vad.empty():
            front = self._vad.front
            out.append(Segment(int(front.start), np.asarray(front.samples, dtype=np.float32)))
            self._vad.pop()
        return out

    def accept(self, samples: Any) -> list[Segment]:
        import numpy as np

        data = np.concatenate([self._pending, np.asarray(samples, dtype=np.float32)])
        whole = data.size - data.size % _WINDOW
        for begin in range(0, whole, _WINDOW):
            self._vad.accept_waveform(data[begin : begin + _WINDOW])
        self._pending = data[whole:]
        return self._drain()

    def finish(self) -> list[Segment]:
        import numpy as np

        if self._pending.size:
            padded = np.zeros(_WINDOW, dtype=np.float32)
            padded[: self._pending.size] = self._pending
            self._vad.accept_waveform(padded)
            self._pending = np.zeros(0, dtype=np.float32)
        self._vad.flush()
        return self._drain()


def silero_segmenter() -> Segmenter:
    """The real voice detector (raises a sentence when its model is missing)."""
    from quill.core.windows_dictation.local_recognizer import _vad

    return _SileroSegmenter(_vad(_PAUSE_SECONDS))


Recognize = Callable[[Any], str]


def local_engine(engine_id: str, language: str) -> tuple[Recognize, str]:
    """``(recognise, notice)`` for a model on this computer.

    A downloaded model that will not load gives way to the built-in engine,
    with the same one sentence dictation says (never a silent switch).
    """
    from quill.core.windows_dictation.engines import DEFAULT_ENGINE
    from quill.core.windows_dictation.local_recognizer import _load, transcribe
    from quill.core.windows_dictation.model_catalog import downloadable

    notice = ""
    try:
        _load(engine_id, language)
    except Exception as error:
        if downloadable(engine_id) is None:
            raise FileTranscribeError(
                plain(error) or "The speech model could not be loaded."
            ) from error
        from quill.core.windows_dictation.model_loader import fallback_sentence

        notice = fallback_sentence(engine_id).replace("dictation is using", "this used")
        engine_id = DEFAULT_ENGINE
        try:
            _load(engine_id, language)
        except Exception as again:
            raise FileTranscribeError(plain(again)) from again
    chosen = engine_id
    return (lambda samples: transcribe(chosen, samples, language)), notice


def openai_engine(model: str, language: str, keywords: Sequence[str]) -> Recognize:
    """OpenAI's file transcription with the person's own key; one retry per piece."""
    from quill.core.windows_dictation.openai_models import cloud_problem, load_key
    from quill.core.windows_dictation.openai_transcribe import (
        ModelGoneError,
        OpenAIDictationError,
        transcribe_phrase,
    )

    problem = cloud_problem()
    if problem:
        raise FileTranscribeError(problem)
    key = load_key()

    def recognise(samples: Any) -> str:
        for attempt in (1, 2):
            try:
                return transcribe_phrase(
                    key, model, samples, language=language, keywords=keywords, timeout=180.0
                )
            except ModelGoneError as error:
                raise FileTranscribeError(plain(error)) from None
            except OpenAIDictationError as error:
                if attempt == 2 or "key" in plain(error).lower():
                    raise FileTranscribeError(plain(error)) from None
        return ""

    return recognise


@dataclass
class _Writer:
    """The transcript as it grows: paragraphs, tidied the way dictation tidies."""

    job: FileJob
    rewrite: Callable[[str], str] | None = None
    paragraphs: list[Paragraph] = field(default_factory=list)
    _text: str = ""
    _start: float = 0.0
    _pieces_added: list[int] = field(default_factory=list)
    _auto_period: bool = False

    def break_paragraph(self) -> None:
        text = self._text.strip()
        if text:
            self.paragraphs.append(Paragraph(self._start, text))
        self._text = ""
        self._pieces_added = []
        self._auto_period = False

    def add(self, heard: str, start: float) -> None:
        # Parakeet's tokens join a currency sign to the word before it
        # ("about$12,000", measured 2026-10-05); a space puts it back.
        heard = _GLUED_CURRENCY.sub(" ", " ".join(heard.split()))
        if not heard:
            return
        if self.rewrite is not None:
            try:
                heard = " ".join(self.rewrite(heard).split()) or heard
            except Exception:  # noqa: BLE001 - a broken profile never stops a transcription
                pass
        phrase = clean_phrase(
            RecognizedPhrase(words_from_text(heard), text=heard),
            remove_fillers=self.job.remove_fillers,
            strip_punctuation=False,
            language=self.job.language,
        )
        if self.job.obey_commands:
            parsed = parse(phrase, vocabulary=vocabulary_for(self.job.language))
            if parsed.command is Command.SCRATCH:
                self._scratch()
                return
            if parsed.command is not None:
                return  # editing commands mean nothing in a recording
            pieces, auto = parsed.pieces, parsed.auto_period
        else:
            pieces = tuple(Piece(word.display) for word in phrase.words if word.display)
            last = pieces[-1].text if pieces else ""
            auto = last.endswith(".") and not last.endswith("..")
        if not pieces:
            return
        if not self._text:
            self._start = start
        pieces = self._carry_on(pieces)
        written = compose(
            pieces, before=self._text[-300:], dash=self.job.dash, close_paragraphs=True
        )
        if not written.strip():
            return
        self._text += written
        self._pieces_added.append(len(written))
        self._auto_period = auto

    def _carry_on(self, pieces: tuple[Piece, ...]) -> tuple[Piece, ...]:
        """Take back a full stop a breath put in, when this phrase continues it."""
        first = pieces[0]
        if not self._auto_period or first.mark is not None or not self._text.endswith("."):
            return pieces
        word = "".join(_WORD.findall(first.text.lower()))
        if word not in _CONTINUATIONS:
            return pieces
        self._text = self._text[:-1]
        if self._pieces_added:
            self._pieces_added[-1] -= 1
        lowered = first.text[:1].lower() + first.text[1:] if first.text != "I" else first.text
        return (Piece(lowered, first.mark, first.verbatim), *pieces[1:])

    def _scratch(self) -> None:
        if self._pieces_added:
            size = self._pieces_added.pop()
            self._text = self._text[:-size] if size else self._text
            self._auto_period = False


@dataclass
class FileTranscriber:
    """Runs one :class:`FileJob`. Every heavy piece can be replaced for a test."""

    job: FileJob
    opener: Callable[[Path], AudioSource] = open_audio
    segmenter: Callable[[], Segmenter] = silero_segmenter
    #: ``(model, language, keywords) -> (recognise, notice)``; None picks the real engine.
    engine: Callable[[FileJob], tuple[Recognize, str]] | None = None
    rewrite: Callable[[str], str] | None = None
    clock: Callable[[], float] = time.monotonic

    def run(
        self,
        progress: Callable[[float | None, float], None] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> FileTranscript:
        """Transcribe, calling *progress(fraction, seconds_heard)* now and then.

        Raises :class:`TranscriptionCancelled` as soon as *cancelled* says so,
        and :class:`FileTranscribeError` (or ``AudioFileError``) with a sentence
        when something cannot be done.
        """
        unloader: Any = None
        if self.engine is None and not self.job.model.startswith("openai:"):
            # Dictation's loaded-model cache: kept while this runs, unloaded a
            # few minutes after the last user lets go (keep_up.IdleUnloader).
            from quill.core.windows_dictation.local_recognizer import _UNLOADER

            unloader = _UNLOADER
            unloader.busy()
        try:
            return self._run(progress, cancelled)
        finally:
            if unloader is not None:
                unloader.idle()

    def _run(
        self,
        progress: Callable[[float | None, float], None] | None,
        cancelled: Callable[[], bool],
    ) -> FileTranscript:
        started = self.clock()
        source = self.opener(self.job.path)
        recognise, notice = (self.engine or _real_engine)(self.job)
        cloud = self.job.model.startswith("openai:")
        segmenter = self.segmenter()
        writer = _Writer(self.job, self.rewrite)
        total = source.duration * RATE
        heard = 0
        reported = -1
        last_end: int | None = None
        paragraph_from = 0
        unit: list[Segment] = []

        def check() -> None:
            if cancelled():
                raise TranscriptionCancelled("Transcription stopped.")

        def flush_unit() -> None:
            if not unit:
                return
            text = recognise(_joined(unit))
            check()
            writer.add(text, unit[0].start / RATE)
            unit.clear()

        def take(segment: Segment) -> None:
            nonlocal last_end, paragraph_from
            check()
            gap = (segment.start - last_end) / RATE if last_end is not None else 0.0
            long_talk = (segment.start - paragraph_from) / RATE >= _LONGEST_PARAGRAPH
            new_paragraph = last_end is not None and (gap >= PARAGRAPH_PAUSE or long_talk)
            if cloud:
                unit_seconds = (segment.end - unit[0].start) / RATE if unit else 0.0
                if new_paragraph or unit_seconds > _CLOUD_UNIT_SECONDS:
                    flush_unit()
            if new_paragraph:
                writer.break_paragraph()
                paragraph_from = segment.start
            last_end = segment.end
            if cloud:
                unit.append(segment)
                return
            writer.add(recognise(segment.samples), segment.start / RATE)

        for block in _blocks(source):
            check()
            heard += len(block)
            for segment in segmenter.accept(block):
                take(segment)
            if progress is not None:
                fraction = min(0.99, heard / total) if total > 0 else None
                step = int(fraction * 100) if fraction is not None else heard // (RATE * 60)
                if step != reported:
                    reported = step
                    progress(fraction, heard / RATE)
        for segment in segmenter.finish():
            take(segment)
        flush_unit()
        writer.break_paragraph()
        audio = source.duration or heard / RATE
        return FileTranscript(tuple(writer.paragraphs), audio, self.clock() - started, notice)


def _blocks(source: AudioSource) -> Iterator[Any]:
    try:
        yield from source.blocks()
    except (TranscriptionCancelled, FileTranscribeError):
        raise
    except CodedError:
        raise
    except Exception as error:
        raise FileTranscribeError(
            f"{source.path.name} stopped being readable part way through: {error}"
        ) from error


def _joined(unit: list[Segment]) -> Any:
    """Several phrases as one piece of sound, with their pauses kept short."""
    import numpy as np

    parts: list[Any] = []
    previous: Segment | None = None
    for segment in unit:
        if previous is not None:
            gap = min(_JOIN_GAP_SECONDS, max(0.0, (segment.start - previous.end) / RATE))
            parts.append(np.zeros(int(gap * RATE), dtype=np.float32))
        parts.append(np.asarray(segment.samples, dtype=np.float32))
        previous = segment
    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)


def _real_engine(job: FileJob) -> tuple[Recognize, str]:
    if job.model.startswith("openai:"):
        return openai_engine(job.model.split(":", 1)[1], job.language, job.keywords), ""
    return local_engine(job.model, job.language)
