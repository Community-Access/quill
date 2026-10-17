"""OpenAI dictation, described on the same interface as every cloud provider (D-31).

**Nothing about OpenAI dictation changes here.**
:class:`~quill.core.windows_dictation.openai_recognizer.OpenAIDictationRecognizer`
still drives OpenAI dictation, under the ``openai`` engine id, and its consent
stays ``windows_dictation_openai_consent``. This provider is how the Speech
Providers page lists OpenAI beside the others and tests it: its key lives in
Use My Own AI Key (so it has no fields of its own), its test is the model list
OpenAI dictation already reads, and its verbs wrap the existing
:mod:`~quill.core.windows_dictation.openai_transcribe` calls, turning their
errors into :class:`~quill.core.windows_dictation.cloud.errors.CloudSpeechError`
sentences.

No new network call site: every call goes through
:func:`openai_models.list_transcription_models`,
:class:`openai_transcribe.LiveTranscription` and
:func:`openai_transcribe.transcribe_phrase`, each already in the egress audit.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from quill.core.windows_dictation import openai_models, openai_transcribe
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudNetworkError,
    CloudQuotaError,
    CloudSpeechError,
)
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    LiveSession,
    ProviderField,
    Values,
)

__all__ = ["OpenAIProvider"]

_LIVE_MODEL = "gpt-live-transcribe"
_PHRASE_MODEL = "gpt-transcribe"
_NO_KEY = "No OpenAI key is saved. Save one in Use My Own AI Key, in the AI menu."


def _translated(error: openai_transcribe.OpenAIDictationError) -> CloudSpeechError:
    """The same sentence, as the cloud layer's error."""
    sentence = str(error.args[0]) if error.args else "OpenAI could not transcribe that."
    if isinstance(error, openai_transcribe.ModelGoneError):
        return CloudFieldError(sentence, field="Model")
    lowered = sentence.lower()
    if "did not accept the saved key" in lowered:
        return CloudAuthError(sentence)
    if "out of credit" in lowered:
        return CloudQuotaError(sentence)
    if "could not be reached" in lowered or "connection" in lowered:
        return CloudNetworkError(sentence)
    return CloudSpeechError(sentence)


@contextmanager
def _as_cloud_errors() -> Iterator[None]:
    try:
        yield
    except openai_transcribe.OpenAIDictationError as error:
        raise _translated(error) from None


class _OpenAILive:
    """:class:`openai_transcribe.LiveTranscription` with cloud-layer errors."""

    def __init__(self, session: openai_transcribe.LiveTranscription) -> None:
        self._session = session

    def open(self) -> None:
        with _as_cloud_errors():
            self._session.open()

    def append(self, samples: Any) -> None:
        with _as_cloud_errors():
            self._session.append(samples)

    def commit(self, timeout: float = 15.0) -> str:
        with _as_cloud_errors():
            return self._session.commit(timeout)

    def clear(self) -> None:
        with _as_cloud_errors():
            self._session.clear()

    def close(self) -> None:
        with _as_cloud_errors():
            self._session.close()


class OpenAIProvider(CloudProvider):
    id = "openai"
    name = "OpenAI"
    short_name = "OpenAI"
    company = "OpenAI"
    console_url = "https://platform.openai.com/usage"
    privacy_url = "https://openai.com/policies"
    hosts = ("api.openai.com",)
    consent_version = 1
    description = (
        "OpenAI transcription, with live words while you speak and up to 100 of your "
        "words. It uses the OpenAI key saved in Use My Own AI Key, in the AI menu."
    )

    def fields(self) -> tuple[ProviderField, ...]:
        return ()

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, biasing_limit=100, biasing_name="keywords")

    def problem(self, values: Values) -> CloudFieldError | None:
        del values
        if not openai_models.load_key():
            return CloudFieldError(_NO_KEY, field="")
        return None

    def test(self, values: Values) -> str:
        del values
        key = openai_models.load_key()
        if not key:
            raise CloudFieldError(_NO_KEY, field="")
        models, error = openai_models.list_transcription_models(key)
        if error:
            if "did not accept" in error:
                raise CloudAuthError(error)
            if "could not be reached" in error:
                raise CloudNetworkError(error)
            raise CloudSpeechError(error)
        count = len(models)
        return f"OpenAI answered: ready, {count} speech model{'s' if count != 1 else ''}."

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        session = openai_transcribe.LiveTranscription(
            openai_models.load_key(),
            str(values.get("model") or _LIVE_MODEL),
            language=language,
            keywords=terms,
            on_delta=on_delta,
        )
        return _OpenAILive(session)

    def phrase(
        self,
        values: Values,
        samples: Any,
        *,
        language: str,
        terms: Sequence[str],
    ) -> str:
        with _as_cloud_errors():
            return openai_transcribe.transcribe_phrase(
                openai_models.load_key(),
                str(values.get("model") or _PHRASE_MODEL),
                samples,
                language=language,
                keywords=terms,
            )
