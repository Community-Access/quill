"""AI onboarding model — a magical, frictionless first run for QUILL's AI (wx-free).

This is the brain of the AI Setup Wizard: the welcome, the one real decision (how
should AI run?), the friendly provider choices, the celebration of what just became
possible, and the persisted state (was setup done, and is the user in the gentle
**Basic** experience mode). It holds no wx — the wizard dialog drives it and applies
the chosen configuration through the existing settings/provider functions, so the
whole flow is unit-testable and the copy lives in one reviewable place.

Design promises: no jargon, no dead ends, no broken configurations. Every path can be
finished or skipped in seconds; the on-device path verifies a usable local Ollama
before it commits (``ollama_status``) so the user is never left "configured but not
working"; and the wizard's "keep it simple" checkbox puts a newcomer in Basic mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "EXPERIENCE_BASIC",
    "EXPERIENCE_ADVANCED",
    "OnboardingPath",
    "CloudProviderOption",
    "ONBOARDING_PATHS",
    "CLOUD_PROVIDER_OPTIONS",
    "ONDEVICE_PROVIDER_OPTION",
    "SETUP_PROVIDERS",
    "WELCOME_TITLE",
    "WELCOME_BODY",
    "FREE_PATH_GUIDANCE",
    "cloud_provider_option",
    "onboarding_path",
    "load_experience_mode",
    "save_experience_mode",
    "is_basic_mode",
    "onboarding_complete",
    "mark_onboarding_complete",
    "reset_onboarding",
    "ai_needs_setup",
    "celebration_lines",
    "apply_cloud_setup",
    "apply_on_device_setup",
    "stored_provider_key",
    "stored_provider_model",
    "remember_provider_key",
    "forget_provider_key",
    "configured_cloud_providers",
    "active_cloud_selection",
    "ai_connection_ready",
    "provider_consent_granted",
    "grant_provider_consent",
    "revoke_provider_consent",
    "active_connection_consented",
    "list_provider_models",
    "verify_model",
    "ollama_status",
]

EXPERIENCE_BASIC = "basic"
EXPERIENCE_ADVANCED = "advanced"
_VALID_MODES = (EXPERIENCE_BASIC, EXPERIENCE_ADVANCED)

WELCOME_TITLE = "Meet QUILL's AI"
WELCOME_BODY = (
    "QUILL has a friendly AI that helps you write, fix, summarize, and turn recordings "
    "into finished documents — only when you ask, always with a preview, and never "
    "sending your work anywhere unless you choose to.\n\n"
    "Let's set it up in a few seconds. You can change anything later, and you can stop "
    "at any point."
)


@dataclass(frozen=True, slots=True)
class OnboardingPath:
    """One way AI can run. The user picks exactly one (or skips)."""

    id: str  # "on_device" | "cloud" | "skip"
    title: str
    summary: str  # one line shown in the choice list
    detail: str  # the reassuring paragraph shown when focused


ONBOARDING_PATHS: tuple[OnboardingPath, ...] = (
    OnboardingPath(
        id="cloud",
        title="Set up an AI provider — recommended",
        summary="Connect a cloud account or local Ollama; add one or more, you pick a default.",
        detail=(
            "Connect one or more AI providers. Cloud accounts — Claude, OpenAI, Gemini, "
            "OpenRouter, or Ollama Cloud — paste a key once and give you the most capable "
            "models. Or run on your device with Ollama: completely private and free, your "
            "writing never leaves your machine (needs Ollama installed and running with a "
            "model pulled). You'll pick which provider and model is the default. Cloud is the "
            "simplest, most capable choice if you're not sure. Your text is sent only to the "
            "provider you choose, only when you run an AI action, after a preview you approve."
        ),
    ),
    OnboardingPath(
        id="agent",
        title="Use an AI agent you already pay for",
        summary="Drive QUILL's agent with your GitHub Copilot, ChatGPT, or Claude subscription.",
        detail=(
            "Already pay for GitHub Copilot, ChatGPT, or Claude? Use it as QUILL's agent — "
            "no second API key, no per-word charge on your card, and it runs on your plan's "
            "models. QUILL adds the connector on demand and signs you in; then every agent "
            "and Ask Quill runs on your chosen engine. And because QUILL owns every edit, the "
            "agent proposes and you approve — each change is a reviewable preview and a single "
            "undo, exactly like the rest of QUILL. You'll finish set-up on the AI Hub's "
            "Engines tab, which opens right after this."
        ),
    ),
    OnboardingPath(
        id="skip",
        title="Not right now",
        summary="Keep AI off for now. You can set it up any time from the AI menu.",
        detail=(
            "No problem — QUILL works beautifully without AI. You can turn it on whenever "
            "you like from AI > Set Up AI, with no pressure and nothing lost."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class CloudProviderOption:
    """One provider the user can connect during onboarding.

    ``local`` marks an on-device provider (Ollama): no API key, verified against a local
    server instead of a probe with a key. All other providers are keyed cloud accounts.
    """

    id: str  # matches assistant_ai provider ids
    name: str
    blurb: str
    key_hint: str  # where to get a key (or, for local, what's needed), in plain language
    signup_url: str
    local: bool = False


# The on-device (local Ollama) option. Listed alongside the cloud providers so the user
# picks cloud vs local right where they choose a provider, and the wizard handles each
# based on ``local``.
ONDEVICE_PROVIDER_OPTION = CloudProviderOption(
    id="ollama",
    name="Ollama (on your device)",
    blurb="Runs locally on your computer — private and free; your writing never leaves it.",
    key_hint=(
        "No key needed. Requires Ollama installed and running with a model pulled "
        "(for example, run 'ollama pull llama3.2')."
    ),
    signup_url="https://ollama.com/",
    local=True,
)


# Keyed cloud providers, in the requested display order (Ollama Cloud, OpenAI, Gemini,
# Claude, OpenRouter). The on-device option leads the combined SETUP_PROVIDERS list.
CLOUD_PROVIDER_OPTIONS: tuple[CloudProviderOption, ...] = (
    CloudProviderOption(
        id="ollama_cloud",
        name="Ollama Cloud",
        blurb="Hosted open models with one key.",
        key_hint="Get a key from ollama.com after signing in.",
        signup_url="https://ollama.com/",
    ),
    CloudProviderOption(
        id="openai",
        name="OpenAI",
        blurb="GPT models — widely used and reliable.",
        key_hint="Get a key from platform.openai.com under API keys.",
        signup_url="https://platform.openai.com/api-keys",
    ),
    CloudProviderOption(
        id="gemini",
        name="Google Gemini",
        blurb="Fast and capable, with a generous free tier.",
        key_hint="Get a key from aistudio.google.com under Get API key.",
        signup_url="https://aistudio.google.com/app/apikey",
    ),
    CloudProviderOption(
        id="claude",
        name="Claude (Anthropic)",
        blurb="Excellent, careful writing help. A great default.",
        key_hint="Get a key from console.anthropic.com under API Keys.",
        signup_url="https://console.anthropic.com/",
    ),
    CloudProviderOption(
        id="openrouter",
        name="OpenRouter",
        blurb="One key, many models — including strong free ones. The best free cloud path.",
        key_hint="Get a free key from openrouter.ai under Keys (tap Get API key).",
        signup_url="https://openrouter.ai/keys",
    ),
)


# The full provider list shown in the wizard: on-device Ollama first, then the keyed
# cloud providers. Cloud-only callers keep using CLOUD_PROVIDER_OPTIONS.
SETUP_PROVIDERS: tuple[CloudProviderOption, ...] = (
    ONDEVICE_PROVIDER_OPTION,
) + CLOUD_PROVIDER_OPTIONS


# Strong free-path guidance shown on the connect step (built in the free catalog,
# re-exported here so the wizard can read ob.FREE_PATH_GUIDANCE alongside the other
# onboarding copy).
from quill.core.ai.free_models import FREE_PATH_GUIDANCE  # noqa: E402


def onboarding_path(path_id: str) -> OnboardingPath | None:
    return next((p for p in ONBOARDING_PATHS if p.id == path_id), None)


def cloud_provider_option(provider_id: str) -> CloudProviderOption | None:
    target = provider_id.strip().lower()
    return next((p for p in SETUP_PROVIDERS if p.id == target), None)


def celebration_lines(path_id: str, *, provider_name: str = "") -> list[str]:
    """The 'you're all set' lines shown at the end, tailored to what was set up."""
    head = {
        "on_device": "Your private, on-device AI (Ollama) is connected.",
        "cloud": f"Connected to {provider_name or 'your AI provider'}. You're all set.",
        "agent": "Let's connect the AI agent you already pay for.",
        "skip": "No problem — AI is off for now.",
    }.get(path_id, "You're all set.")
    if path_id == "skip":
        return [head, "Turn it on any time from AI > Set Up AI."]
    if path_id == "agent":
        return [
            head,
            "Finish on the AI Hub's Engines tab, which opens next:",
            "- Pick GitHub Copilot, OpenAI Agents, or Claude Agent.",
            "- Select Set Up to install the connector and sign in with your account.",
            (
                "It runs on the subscription you already have, and every change the agent "
                + "proposes is a reviewable preview you approve — one keystroke to undo."
            ),
        ]
    return [
        head,
        "Here's what you can do now:",
        "- Ask Quill (Alt+Q): chat about your document, ask anything.",
        "- Turn a recording into minutes, action items, or notes (AI > Transcribe Audio).",
        "- Build your own AI actions in plain language (AI > AI Library > Build Action).",
        "Everything previews before it changes your work, and one keystroke undoes it.",
    ]


# ---------------------------------------------------------------------------
# Persisted state: experience mode + "setup was offered/completed".
# ---------------------------------------------------------------------------

_STATE_FILE = "onboarding.json"


def onboarding_state_path() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "ai" / _STATE_FILE


def _load_state() -> dict[str, object]:
    from quill.core.storage import read_json

    data = read_json(onboarding_state_path(), default={})
    return data if isinstance(data, dict) else {}


def _save_state(state: dict[str, object]) -> None:
    from quill.core.storage import write_json_atomic

    path = onboarding_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, state)


def load_experience_mode() -> str:
    """The current AI experience mode: 'basic' (gentle) or 'advanced' (everything).

    Defaults to **advanced** when the user has never chosen — so nothing is ever
    hidden from someone who did not opt into Basic (e.g. an existing user who has not
    run the wizard). The AI Setup Wizard's "keep it simple" checkbox is what puts a
    newcomer into Basic.
    """
    mode = str(_load_state().get("experience_mode", EXPERIENCE_ADVANCED)).strip().lower()
    return mode if mode in _VALID_MODES else EXPERIENCE_ADVANCED


def save_experience_mode(mode: str) -> None:
    normalized = mode.strip().lower()
    if normalized not in _VALID_MODES:
        normalized = EXPERIENCE_ADVANCED
    state = _load_state()
    state["experience_mode"] = normalized
    _save_state(state)


def is_basic_mode() -> bool:
    """True when the AI surface should stay simple (advanced controls hidden)."""
    return load_experience_mode() == EXPERIENCE_BASIC


def onboarding_complete() -> bool:
    return bool(_load_state().get("completed", False))


def mark_onboarding_complete() -> None:
    state = _load_state()
    state["completed"] = True
    _save_state(state)


def reset_onboarding() -> None:
    """Forget that setup was done (so the wizard offers itself again). For tests/support."""
    state = _load_state()
    state["completed"] = False
    _save_state(state)


def _consented_ids(state: dict[str, object]) -> set[str]:
    raw = state.get("share_consent", [])
    if not isinstance(raw, list):
        return set()
    return {str(p).strip().lower() for p in raw if str(p).strip()}


def provider_consent_granted(provider_id: str) -> bool:
    """True when the user has allowed QUILL to use *provider_id* for AI actions.

    Consent is captured once per provider at setup (the wizard's allow checkbox) and
    persisted. Granted providers skip the per-turn share preview entirely; providers
    without consent are blocked until the user allows them. Applies to every provider,
    including on-device Ollama, so "do not use until allowed" holds uniformly.
    """
    pid = provider_id.strip().lower()
    return bool(pid) and pid in _consented_ids(_load_state())


def grant_provider_consent(provider_id: str) -> None:
    """Record standing consent to use *provider_id* (idempotent)."""
    pid = provider_id.strip().lower()
    if not pid:
        return
    state = _load_state()
    ids = _consented_ids(state)
    ids.add(pid)
    state["share_consent"] = sorted(ids)
    _save_state(state)


def revoke_provider_consent(provider_id: str) -> None:
    """Forget consent for *provider_id* (e.g. when it's removed in the wizard)."""
    pid = provider_id.strip().lower()
    if not pid:
        return
    state = _load_state()
    ids = _consented_ids(state)
    if pid not in ids:
        return
    ids.discard(pid)
    state["share_consent"] = sorted(ids)
    _save_state(state)


def active_connection_consented() -> bool:
    """True when the active AI provider has standing share consent."""
    from quill.core.assistant_ai import load_assistant_connection_settings

    try:
        provider = load_assistant_connection_settings().provider.strip().lower()
    except Exception:  # noqa: BLE001 - unreadable connection means "not consented"
        return False
    return provider_consent_granted(provider)


def apply_cloud_setup(provider_id: str, api_key: str, *, model: str = "") -> None:
    """Configure a cloud provider and turn AI on. Stores the key on this device only.

    Mirrors what the AI Hub does, in one call: set the connection (provider, default
    host, model), save the API key, and enable AI. Uses ``set_active_provider`` so the
    key lands in *both* the per-provider store and the active-key store the generation
    path reads (``load_assistant_api_key``). Saving only the per-provider key — as an
    earlier version did — left the active key empty, so Ask Quill reported "no API key
    configured / active provider: none" right after a successful wizard run.
    """
    from quill.core.ai.model_manager import save_ai_enabled
    from quill.core.ai.providers import default_host_for_provider, default_model_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings, set_active_provider

    chosen_model = model.strip() or default_model_for_provider(provider_id)
    set_active_provider(
        AssistantConnectionSettings(
            provider=provider_id,
            host=default_host_for_provider(provider_id),
            model=chosen_model,
        ),
        api_key.strip(),
    )
    save_ai_enabled(True)


def stored_provider_key(provider_id: str) -> str:
    """Return a previously saved key for *provider_id*, or "" if none.

    Lets the wizard reuse a key the user already configured (e.g. in the AI Hub) when
    they switch providers on the model step, instead of forcing them to paste it again.
    """
    from quill.core.assistant_ai import load_provider_api_key

    try:
        return load_provider_api_key(provider_id).strip()
    except Exception:  # noqa: BLE001 - a missing/locked key just means "none on hand"
        return ""


def stored_provider_model(provider_id: str) -> str:
    """Return the saved default model for *provider_id*, or "" if none."""
    from quill.core.assistant_ai import load_provider_model

    try:
        return load_provider_model(provider_id).strip()
    except Exception:  # noqa: BLE001 - missing model just means "use the default"
        return ""


def remember_provider_key(provider_id: str, api_key: str) -> None:
    """Persist a verified provider key (per-provider store) without making it active.

    Used by the wizard's "Verify and add" so several accounts can be configured in one
    pass; the active provider is chosen later (``apply_cloud_setup``). A default model is
    remembered for the provider too, unless one was already stored.
    """
    from quill.core.ai.providers import default_model_for_provider
    from quill.core.assistant_ai import save_provider_api_key, save_provider_model

    key = api_key.strip()
    if not key:
        return
    save_provider_api_key(provider_id, key)
    if not stored_provider_model(provider_id):
        save_provider_model(provider_id, default_model_for_provider(provider_id))


def forget_provider_key(provider_id: str) -> None:
    """Forget a provider's stored key and its share consent (used on removal)."""
    from quill.core.assistant_ai import clear_provider_api_key

    try:
        clear_provider_api_key(provider_id)
    except Exception:  # noqa: BLE001 - best effort; absence is the desired end state
        pass
    # Removing a provider also withdraws consent: re-adding it must ask again.
    revoke_provider_consent(provider_id)


def configured_cloud_providers() -> list[tuple[str, str]]:
    """Cloud providers that already have a stored key, as ``(id, display name)``.

    Lets the wizard show previously configured accounts on relaunch.
    """
    return [(opt.id, opt.name) for opt in CLOUD_PROVIDER_OPTIONS if stored_provider_key(opt.id)]


def verify_model(provider_id: str, model: str) -> tuple[bool, str]:
    """Quick check that *provider_id* + *model* actually returns a response.

    Uses a short timeout and a single attempt so it fails fast instead of hanging — the
    point is to catch a model that isn't installed/available (a common cause of a chat
    that "just sits there") before it's saved as the active connection. Never raises;
    returns ``(ok, detail)`` where ``detail`` is a reason on failure.
    """
    from quill.core.ai.providers import default_host_for_provider, default_model_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings, generate_assistant_response

    settings = AssistantConnectionSettings(
        provider=provider_id,
        host=default_host_for_provider(provider_id),
        model=(model or "").strip() or default_model_for_provider(provider_id),
    )
    try:
        text, error = generate_assistant_response(
            settings,
            stored_provider_key(provider_id),
            "Reply with exactly one word: ok",
            timeout_seconds=12.0,
            max_attempts=1,
        )
    except Exception as exc:  # noqa: BLE001 - report the reason, never crash the UI
        return False, str(exc)
    if error:
        return False, error
    return (bool(text and text.strip()), "" if (text and text.strip()) else "No response.")


def list_provider_models(provider_id: str) -> tuple[list[str], str]:
    """Return ``(models, error_message)`` for a provider, using its stored key.

    Lists what the provider actually exposes — locally installed models for Ollama, or
    the account's available models for a cloud provider — so the wizard can offer the
    full set instead of only the curated suggestions. Never raises; ``error_message`` is
    "" on success.
    """
    from quill.core.ai.providers import default_host_for_provider, default_model_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings, list_assistant_models

    settings = AssistantConnectionSettings(
        provider=provider_id,
        host=default_host_for_provider(provider_id),
        model=default_model_for_provider(provider_id),
    )
    try:
        models, error = list_assistant_models(settings, stored_provider_key(provider_id))
    except Exception as exc:  # noqa: BLE001 - report the reason, never crash the UI
        return [], str(exc)
    return list(models), (error or "")


def ai_connection_ready() -> bool:
    """True when the active AI connection is configured enough to actually use.

    The AI master switch defaults on, but the default connection points at a local
    Ollama most users do not run, and a keyed provider may have no key — so "enabled"
    alone does not mean "ready". This lets callers offer the setup on-ramp instead of
    failing at request time. Keyed providers need a key (per-provider or active store).
    Local Ollama is the default connection but "configured" is not "running": we probe
    it here (fast-fails when nothing is listening) so a fresh install with no Ollama
    gets the setup on-ramp instead of a chat that hangs on "Thinking".
    """
    from quill.core.ai.providers import provider_requires_api_key
    from quill.core.assistant_ai import load_assistant_api_key, load_assistant_connection_settings

    try:
        conn = load_assistant_connection_settings()
    except Exception:  # noqa: BLE001 - unreadable connection means "not ready"
        return False
    provider = conn.provider.strip().lower()
    if provider in ("", "off"):
        return False
    if provider_requires_api_key(provider):
        return bool(stored_provider_key(provider) or load_assistant_api_key().strip())
    # No-key provider (local Ollama): only ready if a usable server actually answers.
    ok, _message, _model = ollama_status(conn.host or "http://localhost:11434")
    return ok


def active_cloud_selection() -> tuple[str, str]:
    """Return ``(provider_id, model)`` of the active connection when it is a cloud
    provider, else ``("", "")`` — so the wizard can default to what's already active."""
    from quill.core.assistant_ai import load_assistant_connection_settings

    try:
        settings = load_assistant_connection_settings()
    except Exception:  # noqa: BLE001 - no/unreadable connection means "no active cloud"
        return "", ""
    pid = settings.provider.strip().lower()
    if any(pid == opt.id for opt in CLOUD_PROVIDER_OPTIONS):
        return pid, settings.model.strip()
    return "", ""


def ollama_status(host: str = "http://localhost:11434") -> tuple[bool, str, str]:
    """Check whether a usable local Ollama is present. Returns ``(ok, message, model)``.

    Used by the on-device setup path so QUILL never "configures" Ollama before it is
    actually there to talk to. On success, ``model`` is a model that is genuinely
    installed (so we never point the user at a model they don't have); on failure,
    ``message`` is plain-language guidance to fix it. Fast-fails (short timeout, single
    attempt) — a missing Ollama refuses the connection immediately.
    """
    from quill.core.ai.providers import default_model_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings, list_assistant_models

    settings = AssistantConnectionSettings(
        provider="ollama", host=host, model=default_model_for_provider("ollama")
    )
    try:
        models, error = list_assistant_models(settings, "", timeout_seconds=3.0, max_attempts=1)
    except Exception:  # noqa: BLE001 - any failure means "not reachable", with guidance
        return (
            False,
            "Could not reach Ollama on this computer. Install it free from ollama.com, "
            "then try again — or choose 'Use an AI account' instead.",
            "",
        )
    if error or not models:
        if error:
            return (
                False,
                "Ollama isn't running on this computer. Install it free from ollama.com "
                "and start it, then try again — or choose 'Use an AI account' instead.",
                "",
            )
        return (
            False,
            "Ollama is running but has no models yet. In a terminal run, for example, "
            "'ollama pull llama3.2', then try again.",
            "",
        )
    return True, "", models[0]


def apply_on_device_setup(*, host: str = "http://localhost:11434", model: str = "") -> None:
    """Point QUILL at a local Ollama server and turn AI on (private, no key).

    Uses ``set_active_provider`` with an empty key so the active connection becomes
    Ollama and any stale active key from a previous cloud provider is cleared — local
    Ollama needs no key, and a leftover key must not be treated as the active one.
    """
    from quill.core.ai.model_manager import save_ai_enabled
    from quill.core.ai.providers import default_model_for_provider
    from quill.core.assistant_ai import AssistantConnectionSettings, set_active_provider

    chosen_model = model.strip() or default_model_for_provider("ollama")
    set_active_provider(
        AssistantConnectionSettings(provider="ollama", host=host, model=chosen_model),
        "",
    )
    save_ai_enabled(True)


def ai_needs_setup() -> bool:
    """True when it's kind to offer the AI Setup Wizard.

    Offered once: when the user has not been through setup and AI is still off. If they
    have already turned AI on, or already completed (or skipped) setup, QUILL never
    nags — the wizard stays one click away in the AI menu.
    """
    from quill.core.ai.model_manager import load_ai_enabled

    if onboarding_complete():
        return False
    try:
        return not load_ai_enabled()
    except Exception:  # noqa: BLE001 - never let a setup check break startup
        return False
