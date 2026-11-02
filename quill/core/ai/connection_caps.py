"""What each Choose Your AI connection can do, and where that fact comes from.

One record per connection (codex.md 10A.7): QUILL's free AI, My ChatGPT plan,
My GitHub Copilot, Codex for tasks, and My own key. Every claim names its
**source** -- a document a person can read, or the discovery call that
reports it -- because a capability somebody guessed is a request that fails
on the far side with a sentence nobody can act on. GATE-CAPS
(``quill/tools/connection_caps_audit.py``) fails the build on a claim whose
source is empty.

**The one rule (10A.8).** An AI command is always listed and keyed, and it
never pretends: when the connection in use cannot do what a command needs,
nothing is sent. :func:`require` is the check every request makes before it
leaves; :func:`switch_offer` is the sentence that names who *can* do it, for
the one-key switch the window offers.

Per-model facts override a connection's default when a service reports them
(:func:`set_model_capabilities`): the ChatGPT plan's ``/models`` metadata and
Copilot's ``models.list`` are where "pictures, per model" is decided.

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from quill.core.error_codes import CodedError

__all__ = [
    "AGENT_TOOLS",
    "CAPABILITIES",
    "CONNECTIONS",
    "CONNECTION_NAMES",
    "IMAGE_GENERATION",
    "PICTURES",
    "SPEECH",
    "STREAMING",
    "TEXT",
    "WEB_SEARCH",
    "CapabilityMissing",
    "Claim",
    "ConnectionRecord",
    "SwitchOffer",
    "all_records",
    "can",
    "clear_model_capabilities",
    "connections_that_can",
    "missing_sentence",
    "needs_label",
    "own_key_records",
    "record_for",
    "require",
    "set_model_capabilities",
    "switch_offer",
]

# -- the connections ---------------------------------------------------------- #

FREE = "free"
CHATGPT = "chatgpt"
COPILOT = "copilot"
CODEX = "codex"
OWN_KEY = "own_key"

#: Every connection, in the order the window lists them and offers them.
CONNECTIONS: tuple[str, ...] = (FREE, CHATGPT, COPILOT, CODEX, OWN_KEY)

#: Each connection as a person hears it (the window's row names, 10A.2).
CONNECTION_NAMES: dict[str, str] = {
    FREE: "QUILL's free AI",
    CHATGPT: "My ChatGPT plan",
    COPILOT: "My GitHub Copilot",
    CODEX: "Codex, for tasks",
    OWN_KEY: "My own key",
}

# -- the capabilities --------------------------------------------------------- #

TEXT = "text"
PICTURES = "pictures"
AGENT_TOOLS = "agent_tools"
WEB_SEARCH = "web_search"
STREAMING = "streaming"
IMAGE_GENERATION = "image_generation"
SPEECH = "speech"

CAPABILITIES: tuple[str, ...] = (
    TEXT,
    PICTURES,
    AGENT_TOOLS,
    WEB_SEARCH,
    STREAMING,
    IMAGE_GENERATION,
    SPEECH,
)

#: ``(subject of the sentence, what a connection must be, the menu suffix)``.
_NEEDS: dict[str, tuple[str, str, str]] = {
    TEXT: ("Text requests need", "a connection that answers in text", "(needs an AI connection)"),
    PICTURES: ("Pictures need", "a connection that can see", "(needs a connection that sees)"),
    AGENT_TOOLS: ("Agent tasks need", "a connection that runs tasks", "(needs Copilot or Codex)"),
    WEB_SEARCH: ("Web search needs", "a connection that can search", "(needs web search)"),
    STREAMING: ("Streaming needs", "a connection that streams", "(needs streaming)"),
    IMAGE_GENERATION: ("Pictures made by AI need", "your own key", "(needs your own key)"),
    SPEECH: ("AI voices need", "your own key", "(needs your own key)"),
}

#: How a connection is named when it is offered *for one capability*. An
#: OpenAI, Gemini or Claude key is what sees, not "my own key" in general
#: (10A.8's own sentence).
_OFFER_NAMES: dict[tuple[str, str], str] = {(OWN_KEY, PICTURES): "an OpenAI, Gemini or Claude key"}
#: A key that is set up, named for its provider in the switch offer.
_KEY_NAMES: dict[str, str] = {"openai": "OpenAI", "gemini": "Gemini", "claude": "Claude"}

# -- the sources, named once ---------------------------------------------------- #

_SRC_GATEWAY = "GatewayLimits.features and feature_flags, /v1/config (gateway_client.py)"
_SRC_GATEWAY_SEARCH = "GatewayLimits.web_search_enabled, /v1/config (gateway_client.py)"
_SRC_FREE_NO_IMAGE = "AiService.describe_image has no free branch (hosted_ai_service.py)"
_SRC_SIWC_LIMITS = "developers.openai.com/siwc/token-sharing-open-source/preview-limitations"
_SRC_SIWC_STREAM = "developers.openai.com/siwc/token-sharing-open-source/models-and-inference"
_SRC_SIWC_MODELS = "the plan's /models metadata (chatgpt_client.list_models), per model"
_SRC_COPILOT_MODELS = "Copilot SDK models.list at run time (github.com/github/copilot-sdk)"
_SRC_COPILOT_TOOLS = "Copilot SDK custom tools (github.com/github/copilot-sdk python/README.md)"
_SRC_CODEX_TOOLS = "Codex app-server dynamicTools (learn.chatgpt.com/docs/app-server)"
_SRC_OWN_SEE = "AiService.own_key_can_see (hosted_ai_own_key_route.py); own_key_models.list_models"
_SRC_OWN_STREAM = "own_key_gemini.stream_answer streams; the OpenAI own-key client does not"
_SRC_OWN_MEDIA = "image_generation.py, cloud_tts.py, gemini_tts.py: own key only (codex.md 7)"
_SRC_LAYER = "codex.md 10A.7: this layer runs no agent tools on a direct route"
#: The AI Hub's providers in My own key (decision 20): one text source each.
_SRC_OWN_TEXT: dict[str, str] = {
    "openai": _SRC_OWN_SEE,
    "gemini": _SRC_OWN_SEE,
    "claude": "assistant_ai.generate_assistant_response: Anthropic /v1/messages "
    "(docs.anthropic.com)",
    "openrouter": "assistant_ai.generate_assistant_response: OpenRouter /v1/chat/completions "
    "(openrouter.ai/docs)",
    "ollama_cloud": "assistant_ai.generate_assistant_response: ollama.com /v1/chat/completions "
    "(docs.ollama.com/cloud)",
    "custom": "assistant_ai.generate_assistant_response: the service's OpenAI-compatible "
    "/v1/chat/completions",
    "ollama": "assistant_ai.generate_assistant_response: Ollama /api/chat on this computer "
    "(docs.ollama.com/api)",
}
#: Pictures on a keyed provider, each with the page that says its models read
#: images and the request shape vision.build_image_description_body sends:
#: OpenAI image_url parts, Anthropic base64 image blocks, Gemini inline_data.
#: A text-only model answers with the provider's own error, said as it came.
_SRC_OWN_KEY_SEE: dict[str, str] = {
    "openai": "platform.openai.com/docs/guides/images-vision (image_url input on "
    "/v1/chat/completions); sent by vision.describe_image",
    "gemini": _SRC_OWN_SEE,
    "claude": "docs.anthropic.com/en/docs/build-with-claude/vision (base64 image blocks "
    "on /v1/messages); sent by vision.describe_image",
}
#: Pictures on the rest of the Hub's providers: only local Ollama, per model.
_SRC_OWN_HUB_SEE = (
    "the own-key route sends pictures only on OpenAI, Gemini, Claude and per-model Ollama"
)
_SRC_OLLAMA_SEE = "Ollama /api/show capabilities (ollama_capabilities.py), per model"
_SRC_OWN_NO_STREAM = "assistant_ai.generate_assistant_response answers whole, not streamed"
_SRC_PLAN_MEDIA = "codex.md 10A.7: plans carry no image generation or speech"


@dataclass(frozen=True, slots=True)
class Claim:
    """One capability fact: whether it holds, and where that was read."""

    supported: bool
    source: str
    #: How the claim reads in the window's About line, when it is conditional.
    note: str = ""


@dataclass(frozen=True, slots=True)
class ConnectionRecord:
    """Everything the registry says about one connection, as currently known."""

    connection: str
    claims: Mapping[str, Claim]
    #: False while a connection exists in the plan but not yet in this build
    #: (Copilot until Phase 2, Codex until Phase 4b): "Not available yet".
    available: bool = True
    available_source: str = "codex.md section 11: the phase that ships it"
    model: str = ""

    @property
    def name(self) -> str:
        return CONNECTION_NAMES.get(self.connection, self.connection)

    def claim(self, capability: str) -> Claim:
        return self.claims.get(capability, Claim(False, "not claimed: unknown capability"))


def _record(connection: str, available: bool = True, **claims: Claim) -> ConnectionRecord:
    missing = [cap for cap in CAPABILITIES if cap not in claims]
    if missing:  # pragma: no cover - a programming error caught by the tests
        raise ValueError(f"{connection} has no claim for {', '.join(missing)}")
    return ConnectionRecord(connection, dict(claims), available=available)


def _free(web_search_enabled: bool) -> ConnectionRecord:
    return _record(
        FREE,
        text=Claim(True, _SRC_GATEWAY),
        pictures=Claim(False, _SRC_FREE_NO_IMAGE),
        agent_tools=Claim(False, _SRC_GATEWAY),
        web_search=Claim(web_search_enabled, _SRC_GATEWAY_SEARCH, "if the service has it on"),
        streaming=Claim(False, _SRC_GATEWAY),
        image_generation=Claim(False, _SRC_GATEWAY),
        speech=Claim(False, _SRC_GATEWAY),
    )


def _chatgpt() -> ConnectionRecord:
    return _record(
        CHATGPT,
        text=Claim(True, _SRC_SIWC_STREAM),
        pictures=Claim(True, _SRC_SIWC_MODELS, "per model"),
        agent_tools=Claim(False, _SRC_LAYER),
        web_search=Claim(True, _SRC_SIWC_LIMITS, "if your account allows it"),
        streaming=Claim(True, _SRC_SIWC_STREAM),
        image_generation=Claim(False, _SRC_PLAN_MEDIA),
        speech=Claim(False, _SRC_PLAN_MEDIA),
    )


def _copilot() -> ConnectionRecord:
    return _record(
        COPILOT,
        available=False,
        text=Claim(True, _SRC_COPILOT_MODELS),
        pictures=Claim(True, _SRC_COPILOT_MODELS, "per model, as attachments"),
        agent_tools=Claim(True, _SRC_COPILOT_TOOLS),
        web_search=Claim(True, _SRC_COPILOT_TOOLS, "QUILL's consented tool only"),
        streaming=Claim(True, _SRC_COPILOT_MODELS),
        image_generation=Claim(False, _SRC_PLAN_MEDIA),
        speech=Claim(False, _SRC_PLAN_MEDIA),
    )


def _codex() -> ConnectionRecord:
    return _record(
        CODEX,
        available=False,
        text=Claim(True, _SRC_SIWC_STREAM),
        pictures=Claim(True, _SRC_SIWC_MODELS, "per model"),
        agent_tools=Claim(True, _SRC_CODEX_TOOLS),
        web_search=Claim(True, _SRC_CODEX_TOOLS, "QUILL's consented tool only"),
        streaming=Claim(True, _SRC_SIWC_STREAM),
        image_generation=Claim(False, _SRC_SIWC_LIMITS),
        speech=Claim(False, _SRC_PLAN_MEDIA),
    )


def _own_key_pictures(provider: str) -> Claim:
    if provider in _SRC_OWN_KEY_SEE:
        # Every current Gemini and Claude model reads pictures; some OpenAI
        # models (the o-series minis) do not, so that claim is per model.
        note = "per model" if provider == "openai" else ""
        return Claim(True, _SRC_OWN_KEY_SEE[provider], note)
    if provider == "ollama":
        return Claim(False, _SRC_OLLAMA_SEE, "per model")
    return Claim(False, _SRC_OWN_HUB_SEE)


def _own_key(provider: str) -> ConnectionRecord:
    """My own key's record for *provider*. Every provider has one (decision 20);
    an unknown provider is the text source's empty, which GATE-CAPS catches."""
    gemini = provider == "gemini"
    stream_source = _SRC_OWN_STREAM if provider in ("openai", "gemini") else _SRC_OWN_NO_STREAM
    return _record(
        OWN_KEY,
        text=Claim(True, _SRC_OWN_TEXT.get(provider, "")),
        pictures=_own_key_pictures(provider),
        agent_tools=Claim(False, _SRC_LAYER),
        web_search=Claim(False, _SRC_LAYER),
        streaming=Claim(gemini, stream_source, "per provider"),
        image_generation=Claim(True, _SRC_OWN_MEDIA),
        speech=Claim(True, _SRC_OWN_MEDIA),
    )


def own_key_records() -> dict[str, ConnectionRecord]:
    """My own key's record for every provider it offers, for GATE-CAPS and the tests."""
    from quill.core.ai.own_key_providers import PROVIDERS

    return {provider: _own_key(provider) for provider in PROVIDERS}


# -- per-model overrides -------------------------------------------------------- #

_overrides_lock = threading.Lock()
_model_overrides: dict[tuple[str, str], dict[str, Claim]] = {}


def set_model_capabilities(
    connection: str, model: str, capabilities: Mapping[str, bool], *, source: str
) -> None:
    """Record what a service reported about one model, overriding the default.

    *source* names the discovery call that said so and must not be empty, for
    the same reason every claim needs one.
    """
    if not source.strip():
        raise ValueError("A model capability needs the source that reported it.")
    unknown = [cap for cap in capabilities if cap not in CAPABILITIES]
    if unknown:
        raise ValueError(f"Unknown capability: {', '.join(unknown)}")
    with _overrides_lock:
        slot = _model_overrides.setdefault((connection, model.strip()), {})
        for cap, supported in capabilities.items():
            slot[cap] = Claim(bool(supported), source.strip())


def clear_model_capabilities() -> None:
    """Forget every per-model override (a sign-out, and the tests)."""
    with _overrides_lock:
        _model_overrides.clear()


def record_for(
    connection: str,
    *,
    own_key_provider: str = "openai",
    web_search_enabled: bool = False,
    model: str = "",
    available: bool | None = None,
) -> ConnectionRecord:
    """The record for *connection*, with any per-model override applied.

    *available* overrides whether this build carries the connection, for a
    connection whose availability is read at run time (Copilot: a client id,
    the bundled SDK and CLI, :func:`quill.core.ai.copilot_state.readiness`).
    None keeps the record's own default.
    """
    if connection == FREE:
        base = _free(web_search_enabled)
    elif connection == CHATGPT:
        base = _chatgpt()
    elif connection == COPILOT:
        base = _copilot()
    elif connection == CODEX:
        base = _codex()
    elif connection == OWN_KEY:
        base = _own_key(own_key_provider)
    else:
        raise ValueError(f"Unknown connection: {connection!r}")
    if available is not None:
        base = replace(base, available=bool(available))
    chosen = model.strip()
    if not chosen:
        return base
    with _overrides_lock:
        override = dict(_model_overrides.get((connection, chosen), {}))
    claims = {**base.claims, **override}
    return replace(base, claims=claims, model=chosen)


def all_records(
    *, own_key_provider: str = "openai", web_search_enabled: bool = False
) -> list[ConnectionRecord]:
    """Every connection's record, in window order."""
    return [
        record_for(c, own_key_provider=own_key_provider, web_search_enabled=web_search_enabled)
        for c in CONNECTIONS
    ]


# -- the check --------------------------------------------------------------- #


def can(record: ConnectionRecord, capability: str) -> bool:
    """Whether *record* can do *capability* now (an unavailable connection cannot)."""
    return record.available and record.claim(capability).supported


class CapabilityMissing(CodedError):
    """A request needed something the connection in use cannot do; nothing was sent."""

    code = "QUILL-AI-CAPS-MISSING"
    user_hint = "Press Ctrl+4 to choose a connection that can, or ask for something else."

    def __init__(self, message: str, *, connection: str = "", capability: str = "") -> None:
        super().__init__(message)
        self.connection = connection
        self.capability = capability


def missing_sentence(capability: str) -> str:
    """The statement made when a request was refused for *capability*."""
    subject, needed, _label = _NEEDS.get(
        capability, (f"{capability} needs", "another connection", "")
    )
    return f"{subject} {needed}. Nothing was sent."


def require(record: ConnectionRecord, *capabilities: str) -> None:
    """Raise :class:`CapabilityMissing` unless *record* can do every one of *capabilities*.

    The check every hosted-AI request makes before anything leaves this
    computer (GATE-CAPS). The first capability missing is the one named.
    """
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise ValueError(f"Unknown capability: {capability!r}")
        if not can(record, capability):
            raise CapabilityMissing(
                missing_sentence(capability),
                connection=record.connection,
                capability=capability,
            )


def needs_label(capability: str) -> str:
    """What a menu label adds after a command's name: "(needs a connection that sees)"."""
    return _NEEDS.get(capability, ("", "", f"(needs {capability})"))[2]


def connections_that_can(
    capability: str, records: Iterable[ConnectionRecord], *, set_up: Iterable[str] | None = None
) -> list[str]:
    """The connections among *records* that can do *capability*, in window order.

    With *set_up*, only those connections; without it, every connection that
    could do it once set up.
    """
    allowed = None if set_up is None else set(set_up)
    return [
        record.connection
        for record in records
        if can(record, capability) and (allowed is None or record.connection in allowed)
    ]


@dataclass(frozen=True, slots=True)
class SwitchOffer:
    """The one-key switch the window offers (10A.8), already in words.

    ``target`` is the connection Yes switches to; empty when nothing set up can
    do it, in which case Yes opens Choose Your AI on ``open_row``.
    """

    sentence: str
    target: str = ""
    open_row: str = ""
    candidates: tuple[str, ...] = field(default_factory=tuple)


def _offer_name(connection: str, capability: str) -> str:
    if connection == CODEX:
        return "Codex"  # "Codex, for tasks" is the row; inside a sentence it is Codex
    return _OFFER_NAMES.get((connection, capability), CONNECTION_NAMES.get(connection, connection))


def _either(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " or " + names[-1]


def switch_offer(
    capability: str,
    *,
    set_up: Iterable[str],
    in_use: str = "",
    own_key_provider: str = "openai",
    web_search_enabled: bool = False,
) -> SwitchOffer:
    """The sentence offering the switch, for a command the connection in use cannot do.

    "Pictures need a connection that can see. My ChatGPT plan can. Switch to it
    and ask?" when something set up can; otherwise "Pictures need My ChatGPT
    plan, My GitHub Copilot, Codex or an OpenAI, Gemini or Claude key. Choose one
    now?". A key that is set up is named for its provider ("Your Claude key
    can."). The
    candidates that *could* do it ignore availability, because they are what
    the person is being told exists, not what this build has switched on.
    """
    subject, needed, _label = _NEEDS.get(
        capability, (f"{capability} needs", "another connection", "")
    )
    records = all_records(own_key_provider=own_key_provider, web_search_enabled=web_search_enabled)
    ready = [c for c in connections_that_can(capability, records, set_up=set_up) if c != in_use]
    if ready:
        target = ready[0]
        who = _offer_name(target, capability)
        if (target, capability) in _OFFER_NAMES and own_key_provider in _KEY_NAMES:
            who = f"your {_KEY_NAMES[own_key_provider]} key"
        who = who[:1].upper() + who[1:]
        return SwitchOffer(
            f"{subject} {needed}. {who} can. Switch to it and ask?",
            target=target,
            candidates=tuple(ready),
        )
    possible = [
        r.connection
        for r in all_records(own_key_provider="gemini", web_search_enabled=True)
        if r.claim(capability).supported and r.connection != in_use
    ]
    if capability == WEB_SEARCH:
        possible = [c for c in possible if c != FREE]
    names = [_offer_name(c, capability) for c in possible]
    if not names:
        return SwitchOffer(f"{subject} {needed}. No connection here can do it yet.")
    return SwitchOffer(
        f"{subject} {_either(names)}. Choose one now?",
        open_row=possible[0],
        candidates=tuple(possible),
    )
