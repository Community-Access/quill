"""Dictation with a cloud provider: the same microphone and pauses, its ears.

Exactly the shape of
:class:`~quill.core.windows_dictation.openai_recognizer.OpenAIDictationRecognizer`:
everything about listening is the built-in engines' own
(:class:`~quill.core.windows_dictation.local_recognizer.LocalDictationRecognizer`)
-- the microphone, the voice detector that finds the pause, the reader gate,
the watchdog, Escape -- and only the recognising goes to the provider. So the
commands, the normaliser, the target lock, held words and the read-back cannot
tell the difference, and nothing is sent while nobody is speaking.

* A provider with ``streaming`` gets a live session for the dictation session;
  its provisional words feed the live preview.
* A provider without it gets each finished phrase, once; **no live preview**,
  because there is nothing provisional to show.

**Refuses to start**, with a sentence and before the microphone opens, in Safe
Mode, with a field missing, or without consent
(:func:`~quill.core.windows_dictation.cloud.consent.start_problem`) -- so with
consent declined **no request is made at all**.

**When the provider answers with a problem** the listener's
``on_engine_problem`` hears the sentence once. A refused key, an empty account
or a missing part stops dictation; a network hiccup costs that one phrase and
dictation keeps listening. It never moves to another engine on its own.

wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.windows_dictation.cloud.consent import biasing_terms, start_problem
from quill.core.windows_dictation.cloud.errors import (
    CloudNetworkError,
    CloudSpeechError,
    said,
)
from quill.core.windows_dictation.cloud.registry import engine_id_for
from quill.core.windows_dictation.cloud.types import CloudProvider, LiveSession
from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer

__all__ = ["CloudDictationRecognizer"]


class _CloudLive:
    """The worker's live engine for a streaming provider."""

    def __init__(self, report: Any) -> None:
        self._session: Any = None
        self._report = report
        self._partial = ""
        self._failed = False

    def _fail(self, error: CloudSpeechError) -> None:
        # A streaming session that lost its connection cannot hear the next
        # phrase either: said once, and dictation stops (never another engine).
        if not self._failed:
            self._failed = True
            self._report(error, live=True)

    def attach(self, session: LiveSession) -> None:
        self._session = session

    def on_delta(self, text: str) -> None:
        self._partial = text.strip()

    def begin(self, lead_in: Any) -> None:
        self._partial = ""
        if lead_in is not None and len(lead_in):
            self._session.append(lead_in)

    def feed(self, samples: Any, *, speaking: bool) -> str:
        del speaking  # the pause is QUILL's to find: all of it goes
        if self._failed:
            return ""
        try:
            self._session.append(samples)
        except CloudSpeechError as error:
            self._fail(error)
        return self._partial

    def end(self) -> tuple[str, str]:
        if self._failed:
            return "", ""
        try:
            return "", self._session.commit()
        except CloudSpeechError as error:
            self._fail(error)
            return "", ""
        finally:
            self._partial = ""

    def clear(self) -> None:
        try:
            self._session.clear()
        except CloudSpeechError:
            pass
        self._partial = ""

    def close(self) -> None:
        self._session.close()


class CloudDictationRecognizer(LocalDictationRecognizer):
    """One listening session whose phrases a cloud provider recognises."""

    def __init__(
        self,
        listener: Any,
        *,
        post: Any,
        provider: CloudProvider,
        values: Mapping[str, str],
        consents: Mapping[str, Any] | None,
        keywords: Sequence[str] = (),
        pause_seconds: float = 0.8,
        language: str = "en",
    ) -> None:
        super().__init__(
            listener,
            engine_id_for(provider.id),
            post=post,
            pause_seconds=pause_seconds,
            language=language,
        )
        self._provider = provider
        self._values = dict(values)
        self._consents = dict(consents or {})
        self._keywords = list(keywords)
        self._terms: list[str] = []
        #: How many of My Words did not fit the provider's limit (said by the host).
        self.words_left_out = 0
        self._stopped_for_problem = False

    @property
    def streaming(self) -> bool:
        """Whether this provider shows words while you speak (the live preview)."""
        return self._provider.capabilities().streaming

    def _prepare_engine(self) -> None:
        problem = start_problem(self._provider, self._values, self._consents)
        if problem:
            raise DictationStartError(problem)
        capabilities = self._provider.capabilities()
        self._terms, self.words_left_out = biasing_terms(self._keywords, capabilities.biasing_limit)
        if not capabilities.streaming:
            return
        live = _CloudLive(self._problem)
        try:
            session = self._provider.live(
                self._values,
                language=self._language,
                terms=self._terms,
                on_delta=live.on_delta,
            )
            live.attach(session)
            session.open()
        except CloudNetworkError as error:
            raise DictationStartError(
                f"{said(error)} Nothing was switched: try again, or choose a built-in engine."
            ) from None
        except CloudSpeechError as error:
            raise DictationStartError(said(error)) from None
        self._live = live

    def _transcribe_healing(self, samples: Any) -> str:
        """One phrase to the provider, for a provider that does not stream."""
        try:
            return self._provider.phrase(
                self._values, samples, language=self._language, terms=self._terms
            )
        except CloudSpeechError as error:
            self._problem(error)
            return ""

    def _problem(self, error: CloudSpeechError, *, live: bool = False) -> None:
        """Say what the provider said, once; stop when there is no point going on."""
        if self._stopped_for_problem:
            return
        sentence = said(error)
        fatal = live or bool(getattr(error, "fatal", True))
        if fatal:
            self._stopped_for_problem = True
            self._running.clear()
        handler = getattr(self._listener, "on_engine_problem", None)
        if callable(handler):
            self._post(handler, sentence, fatal)
        elif fatal:
            self._post(self._listener.on_failure, sentence)
