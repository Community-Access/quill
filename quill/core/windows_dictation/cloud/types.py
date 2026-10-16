"""The shape every cloud speech provider has (D-31).

A provider is **data plus two verbs**. The data -- its fields, its
capabilities, the facts its consent question is built from -- is what the
Speech Providers page and the consent read; the verbs are
:meth:`CloudProvider.live` (a session that hears audio as it is spoken and
answers with provisional and final words) and :meth:`CloudProvider.phrase`
(one finished phrase, one answer). The recogniser
(:mod:`~quill.core.windows_dictation.cloud.recognizer`) plugs either into the
built-in engines' own listening loop, so QUILL's voice detector, reader gate,
echo guard, commands, target lock and held words apply unchanged -- exactly as
for OpenAI.

**The capability table drives features** (point 7): the live preview turns on
only with ``streaming``; "Learns your words" only when ``biasing_limit`` is
above nought; speaker labels only with ``diarization``.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.windows_dictation.cloud.errors import CloudFieldError, CloudUnsupportedError

__all__ = [
    "Capabilities",
    "CloudProvider",
    "LiveSession",
    "ProviderField",
    "Values",
    "locale_for",
]

#: What the person entered for one provider: field key -> text. Secrets are
#: in here only in memory, read from the credential store when needed.
Values = Mapping[str, str]

#: The kinds of field a provider can ask for.
FIELD_KINDS = ("secret", "text", "choice", "file")


@dataclass(frozen=True, slots=True)
class ProviderField:
    """One thing the person enters for a provider, as the page shows it."""

    key: str
    #: The label, without an access key ("Key", "Region").
    label: str
    #: ``secret`` (Credential Manager), ``text``, ``choice`` or ``file``.
    kind: str = "text"
    required: bool = True
    #: The F1 sentence for the field.
    help: str = ""
    #: ``(value, label)`` rows for a ``choice`` field.
    choices: tuple[tuple[str, str], ...] = ()
    default: str = ""
    #: ``value -> problem sentence`` ("" when fine). Runs before anything is sent.
    validate: Callable[[str], str] | None = field(default=None, compare=False)

    @property
    def secret(self) -> bool:
        return self.kind in ("secret", "file")


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What a provider can do, which decides what QUILL offers with it."""

    #: Words while you speak (the live preview).
    streaming: bool = False
    #: How many of My Words it can be told; 0 when it cannot be told any.
    biasing_limit: int = 0
    #: What the provider calls it ("phrase list", "keyterm").
    biasing_name: str = ""
    punctuation: bool = True
    #: Plain words: "many languages", "English and Spanish".
    languages: str = "many languages"
    diarization: bool = False
    timestamps: bool = False

    @property
    def biasing(self) -> bool:
        return self.biasing_limit > 0


class LiveSession(Protocol):
    """One streaming session for the length of a dictation session.

    The same shape :class:`~quill.core.windows_dictation.openai_transcribe.LiveTranscription`
    has, so the recogniser drives every provider the same way.
    """

    def open(self) -> None: ...

    def append(self, samples: Any) -> None: ...

    def commit(self, timeout: float = 15.0) -> str: ...

    def clear(self) -> None: ...

    def close(self) -> None: ...


def locale_for(language: str, override: str = "") -> str:
    """The BCP-47 locale a provider is told: the person's own code when they
    gave one, else the dictation language's usual one ("en" -> "en-US")."""
    chosen = override.strip()
    if chosen:
        return chosen
    return {"en": "en-US", "es": "es-ES"}.get(language.strip().lower(), language or "en-US")


class CloudProvider:
    """One cloud speech provider. Subclasses fill in the facts and the verbs."""

    #: Short id, used in settings and as ``cloud-<id>`` for the engine.
    id: str = ""
    #: The name people know it by ("Azure AI Speech").
    name: str = ""
    #: Who receives the speech ("Microsoft"), for the consent question.
    company: str = ""
    #: The company's short name for "Speech goes to ..." lines ("Azure").
    short_name: str = ""
    #: Where the person sees what they are billed.
    console_url: str = ""
    #: The company's privacy terms for its speech service.
    privacy_url: str = ""
    #: The hosts this provider ever talks to (also in the egress audit).
    hosts: tuple[str, ...] = ()
    #: When the protocol facts here were last checked against the provider's docs.
    last_checked: str = "2026-10-16"
    #: Bumped when what is sent changes, so the consent is asked again.
    consent_version: int = 1
    #: One sentence for the page's description and F1.
    description: str = ""

    def fields(self) -> tuple[ProviderField, ...]:
        return ()

    def capabilities(self) -> Capabilities:
        return Capabilities()

    def available(self) -> str:
        """Why this copy of QUILL cannot use the provider ("" when it can)."""
        return ""

    def where(self, values: Values) -> str:
        """The region the speech goes to, in words ("westeurope"), or ""."""
        del values
        return ""

    def problem(self, values: Values) -> CloudFieldError | None:
        """The first missing or impossible field, before anything is sent."""
        for spec in self.fields():
            value = str(values.get(spec.key, "") or "").strip()
            if spec.required and not value:
                return CloudFieldError(
                    f"{spec.label} is empty. Fill in {spec.label}.", field=spec.label
                )
            if value and spec.validate is not None:
                sentence = spec.validate(value)
                if sentence:
                    return CloudFieldError(sentence, field=spec.label)
        return None

    def test(self, values: Values) -> str:
        """Check the fields with the provider, never with the person's speech.

        Returns the sentence to say ("Azure answered: ready, region westeurope.");
        raises :class:`~quill.core.windows_dictation.cloud.errors.CloudSpeechError`.
        """
        raise CloudUnsupportedError(f"{self.name} has no connection test yet.")

    def live(
        self,
        values: Values,
        *,
        language: str,
        terms: Sequence[str],
        on_delta: Callable[[str], None] | None = None,
    ) -> LiveSession:
        """A streaming session (not yet open). Only when ``capabilities().streaming``."""
        raise CloudUnsupportedError(f"{self.name} does not give words while you speak.")

    def phrase(
        self,
        values: Values,
        samples: Any,
        *,
        language: str,
        terms: Sequence[str],
    ) -> str:
        """One finished phrase (16 kHz float samples) to text. Blocking."""
        raise CloudUnsupportedError(f"{self.name} cannot take one phrase at a time.")
