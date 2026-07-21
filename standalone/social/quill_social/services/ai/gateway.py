"""The AI provider gateway (PRD 21.2).

Every AI feature runs through the gateway so the product can keep the promises of
PRD 21.1: AI is optional, inspectable, and reversible. The gateway:

- selects a provider per feature (a mode, or an explicit override);
- refuses to run when a feature's mode is ``disabled``, returning a clear,
  non-throwing result instead of failing;
- redacts secrets from the payload before anything reaches a prompt (PRD 21.7);
- emits a :class:`Disclosure` describing the provider, model, the data that
  would be sent, the context included, and the redactions applied (PRD 21.2).

A deterministic :class:`MockProvider` stands in for a real model so the whole
layer is testable with no network. Live modes (local model, user API key,
org-managed, QUILL-brokered) are a documented boundary: unless a real provider
is injected, :meth:`AIGateway.available` reports the mode's dependency as absent
and :meth:`AIGateway.run` returns an honest "not configured" result rather than
pretending. This module is wx-free, has no I/O, and uses no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

from quill_social.services.ai.prompt_guard import redact_secrets, secret_kinds


class ProviderMode(StrEnum):
    """How (and whether) a feature is allowed to reach a model (PRD 21.2)."""

    disabled = "disabled"
    local = "local"
    api_key = "api_key"
    org_managed = "org_managed"
    quill_brokered = "quill_brokered"
    mock = "mock"


@runtime_checkable
class AIProvider(Protocol):
    """The one thing a provider must do: turn a prompt into text.

    ``tools`` is deliberately narrow -- a list of allowed tool names -- and
    content-facing features pass ``None`` so untrusted social text can never
    invoke a tool (PRD 21.7).
    """

    name: str
    model: str

    def complete(self, system: str, user: str, tools: list[str] | None = None) -> str:
        ...


class MockProvider:
    """A deterministic, offline provider used everywhere in tests (PRD 21.2).

    It never calls the network and produces no randomness: it echoes the (already
    secret-redacted) user payload back, optionally normalizing whitespace. That
    makes every downstream transformation predictable -- a shortening tool can
    trust the returned length, a variant tool can trust the returned text -- while
    still exercising the real gateway, disclosure, and redaction paths.
    """

    name = "mock"
    model = "mock-echo-v1"

    def __init__(self, *, normalize_whitespace: bool = False) -> None:
        self.normalize_whitespace = normalize_whitespace

    def complete(self, system: str, user: str, tools: list[str] | None = None) -> str:
        text = user
        if self.normalize_whitespace:
            text = " ".join(text.split())
        return text


def _local_runtime_available() -> bool:
    """Whether a local model runtime is importable (honest boundary, PRD 21.2)."""
    for module in ("llama_cpp", "ollama", "gpt4all"):
        try:
            __import__(module)
        except ImportError:
            continue
        return True
    return False


@dataclass
class Disclosure:
    """What the product tells the user before a feature sends anything (PRD 21.2)."""

    provider: str = "mock"
    model: str = ""
    mode: str = ProviderMode.mock.value
    data_being_sent: str = ""
    context_included: list[str] = field(default_factory=list)
    redactions_applied: list[str] = field(default_factory=list)
    estimated_cost: float | None = None

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "data_being_sent": self.data_being_sent,
            "context_included": list(self.context_included),
            "redactions_applied": list(self.redactions_applied),
            "estimated_cost": self.estimated_cost,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Disclosure:
        return cls(
            provider=d.get("provider", "mock"),
            model=d.get("model", ""),
            mode=d.get("mode", ProviderMode.mock.value),
            data_being_sent=d.get("data_being_sent", ""),
            context_included=list(d.get("context_included", [])),
            redactions_applied=list(d.get("redactions_applied", [])),
            estimated_cost=d.get("estimated_cost"),
        )


@dataclass
class GatewayResult:
    """The outcome of one gateway call: text plus a disclosure, or a refusal."""

    feature: str = ""
    text: str = ""
    refused: bool = False
    reason: str = ""
    disclosure: Disclosure | None = None

    @property
    def ok(self) -> bool:
        return not self.refused

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "text": self.text,
            "refused": self.refused,
            "reason": self.reason,
            "disclosure": self.disclosure.to_dict() if self.disclosure else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> GatewayResult:
        disc = d.get("disclosure")
        return cls(
            feature=d.get("feature", ""),
            text=d.get("text", ""),
            refused=bool(d.get("refused", False)),
            reason=d.get("reason", ""),
            disclosure=Disclosure.from_dict(disc) if disc else None,
        )


def _summarize_payload(text: str) -> str:
    """A short, speech-friendly description of what would be sent."""
    n = len(text)
    words = len(text.split())
    preview = " ".join(text.split())[:60]
    if not text:
        return "no text"
    ellipsis = "..." if len(preview) < len(" ".join(text.split())) else ""
    return f"{n} characters, {words} words; starts: {preview}{ellipsis}"


class AIGateway:
    """Selects providers per feature and enforces the AI principles (PRD 21.1)."""

    def __init__(
        self,
        *,
        mode: ProviderMode = ProviderMode.mock,
        provider: AIProvider | None = None,
        feature_modes: dict[str, ProviderMode] | None = None,
        feature_providers: dict[str, AIProvider] | None = None,
    ) -> None:
        self.mode = mode
        self._provider = provider
        self.feature_modes = dict(feature_modes or {})
        self.feature_providers = dict(feature_providers or {})

    def mode_for(self, feature: str) -> ProviderMode:
        return self.feature_modes.get(feature, self.mode)

    def provider_for(self, feature: str) -> AIProvider | None:
        """Resolve the provider for a feature (PRD 21.2 per-feature selection).

        Precedence: an explicit per-feature provider, then a gateway-wide injected
        provider, then the built-in :class:`MockProvider` for ``mock`` mode. Every
        other live mode without an injected provider resolves to ``None`` -- the
        documented boundary.
        """
        if feature in self.feature_providers:
            return self.feature_providers[feature]
        if self._provider is not None:
            return self._provider
        if self.mode_for(feature) == ProviderMode.mock:
            return MockProvider()
        return None

    def available(self, mode: ProviderMode) -> bool:
        """Whether a mode's dependency exists in this build (honest boundary)."""
        if mode in (ProviderMode.disabled, ProviderMode.mock):
            return True
        if mode == ProviderMode.local:
            return _local_runtime_available()
        # api_key / org_managed / quill_brokered need a configured, injected
        # provider (credentials + endpoint); without one the dependency is absent.
        return self._provider is not None

    def build_disclosure(
        self,
        feature: str,
        user: str,
        *,
        context: list[str] | None = None,
    ) -> Disclosure:
        """Describe exactly what a feature would send, secrets already accounted."""
        provider = self.provider_for(feature)
        mode = self.mode_for(feature)
        redacted = redact_secrets(user)
        return Disclosure(
            provider=provider.name if provider is not None else mode.value,
            model=getattr(provider, "model", "") if provider is not None else "",
            mode=mode.value,
            data_being_sent=_summarize_payload(redacted),
            context_included=list(context or []),
            redactions_applied=secret_kinds(user),
            estimated_cost=None,
        )

    def run(
        self,
        feature: str,
        system: str,
        user: str,
        *,
        tools: list[str] | None = None,
        context: list[str] | None = None,
    ) -> GatewayResult:
        """Run one feature, returning text + disclosure or a clear refusal.

        Never raises for a policy state: a disabled feature or an unconfigured
        live provider returns ``refused=True`` with a plain-language reason.
        """
        mode = self.mode_for(feature)
        disclosure = self.build_disclosure(feature, user, context=context)
        if mode == ProviderMode.disabled:
            return GatewayResult(
                feature=feature,
                refused=True,
                reason="AI is disabled for this feature. Enable a provider in settings.",
                disclosure=disclosure,
            )
        provider = self.provider_for(feature)
        if provider is None:
            return GatewayResult(
                feature=feature,
                refused=True,
                reason=(
                    f"The '{mode.value}' provider is a documented boundary and is not "
                    "configured in this build. Inject a provider to enable it."
                ),
                disclosure=disclosure,
            )
        # Redact before the model ever sees the text (PRD 21.7).
        safe_user = redact_secrets(user)
        text = provider.complete(system, safe_user, tools)
        return GatewayResult(feature=feature, text=text, disclosure=disclosure)
