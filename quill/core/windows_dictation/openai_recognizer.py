"""OpenAI dictation: the same microphone and pauses, OpenAI's ears.

Everything about listening is the built-in engines' own
(:class:`~quill.core.windows_dictation.local_recognizer.LocalDictationRecognizer`):
the microphone, the voice detector that finds the pause, the watchdog that
notices an unplugged headset, Escape, and finishing the last phrase when the
key is let go. Only the recognising goes to OpenAI
(:mod:`~quill.core.windows_dictation.openai_transcribe`), so the commands, the
normaliser and the read-back cannot tell the difference -- and nothing is sent
while nobody is speaking, because only speech the detector heard leaves the
computer.

**Refuses to start**, with a sentence and before the microphone opens, when
Safe Mode is on, when no OpenAI key is saved, when the person has not agreed
to send their speech, or when no model has been chosen
(:func:`~quill.core.windows_dictation.openai_models.cloud_problem`).

**When OpenAI answers with a problem** the listener's ``on_engine_problem``
hears the sentence once. A model that has gone, a key OpenAI refuses, or an
account out of credit stops dictation -- it never moves to another model or
engine on its own; a network hiccup costs that one phrase and dictation keeps
listening.

wx-free.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.engines import CLOUD_ENGINE
from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer
from quill.core.windows_dictation.openai_models import cloud_problem, is_live_model, load_key
from quill.core.windows_dictation.openai_transcribe import (
    LiveTranscription,
    ModelGoneError,
    OpenAIDictationError,
    transcribe_phrase,
)

__all__ = ["OpenAIDictationRecognizer"]

#: Problems after which dictation stops rather than trying the next phrase.
_FATAL_WORDS = ("key", "credit", "no longer available")


def _said(error: BaseException) -> str:
    """The sentence, without the error code in front."""
    return str(error.args[0]) if error.args else str(error)


class _OpenAILive:
    """The worker's live engine for OpenAI's Realtime transcription."""

    def __init__(self, report: Any) -> None:
        self._session: Any = None
        self._report = report
        self._partial = ""

    def attach(self, session: LiveTranscription) -> None:
        self._session = session

    def on_delta(self, text: str) -> None:
        self._partial = text.strip()

    def begin(self, lead_in: Any) -> None:
        self._partial = ""
        if lead_in is not None and len(lead_in):
            self._session.append(lead_in)

    def feed(self, samples: Any, *, speaking: bool) -> str:
        del speaking  # the pause is QUILL's to find: all of it goes
        self._session.append(samples)
        return self._partial

    def end(self) -> tuple[str, str]:
        try:
            return "", self._session.commit()
        except OpenAIDictationError as error:
            self._report(error)
            return "", ""
        finally:
            self._partial = ""

    def clear(self) -> None:
        try:
            self._session.clear()
        except OpenAIDictationError:
            pass
        self._partial = ""

    def close(self) -> None:
        self._session.close()


class OpenAIDictationRecognizer(LocalDictationRecognizer):
    """One listening session whose phrases OpenAI recognises."""

    def __init__(
        self,
        listener: Any,
        *,
        post: Any,
        model: str,
        consent: bool,
        keywords: Sequence[str] = (),
        pause_seconds: float = 0.8,
        language: str = "en",
    ) -> None:
        super().__init__(
            listener, CLOUD_ENGINE, post=post, pause_seconds=pause_seconds, language=language
        )
        self._model = model
        self._consent = consent
        self._keywords = list(keywords)
        self._key = ""
        self._stopped_for_problem = False

    def _prepare_engine(self) -> None:
        problem = cloud_problem(consent=self._consent)
        if problem:
            raise DictationStartError(problem)
        if not self._model:
            raise DictationStartError(
                "Choose an OpenAI model in Dictation Settings, More Dictation Settings, first."
            )
        self._key = load_key()
        if not is_live_model(self._model):
            return
        live = _OpenAILive(self._problem)
        session = LiveTranscription(
            self._key,
            self._model,
            language=self._language,
            keywords=self._keywords,
            on_delta=live.on_delta,
        )
        live.attach(session)
        try:
            session.open()
        except OpenAIDictationError as error:
            raise DictationStartError(_said(error)) from None
        self._live = live

    def _transcribe_healing(self, samples: Any) -> str:
        """One phrase through the file endpoint, its words streaming to the preview."""
        handler = getattr(self._listener, "on_partial", None)

        def delta(text: str) -> None:
            if callable(handler) and text.strip():
                self._post(handler, text.strip())

        try:
            return transcribe_phrase(
                self._key,
                self._model,
                samples,
                language=self._language,
                keywords=self._keywords,
                on_delta=delta,
            )
        except OpenAIDictationError as error:
            self._problem(error)
            return ""

    def _problem(self, error: OpenAIDictationError) -> None:
        """Say what OpenAI said, once; stop when there is no point going on."""
        if self._stopped_for_problem:
            return
        sentence = _said(error)
        fatal = isinstance(error, ModelGoneError) or any(word in sentence for word in _FATAL_WORDS)
        if fatal:
            self._stopped_for_problem = True
            self._running.clear()
        handler = getattr(self._listener, "on_engine_problem", None)
        if callable(handler):
            self._post(handler, sentence, fatal)
        elif fatal:
            self._post(self._listener.on_failure, sentence)
