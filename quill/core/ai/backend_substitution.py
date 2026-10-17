"""Ask before Ask Quill answers from a provider nobody chose (2026-10-16).

:func:`quill.core.ai.assistant.make_default_backend` resolves where QUILL's own
AI requests go -- Ask Quill and the AI tools that share its assistant. It tries
the connection saved in AI settings first, then the provider saved by Ask Quill's
inline setup, then the on-device model. The first step falling through was
already announced (``last_backend_note``). The second was not: when the saved
connection was, say, Anthropic and unavailable, and Ask Quill's setup had once
been pointed at OpenAI, the next question went to OpenAI with nothing said.
That is a different company receiving the person's text, which QUILL never
does without asking (:mod:`quill.core.ai.fallback`, "never quietly change the
privacy posture").

So that step now *holds* the other cloud provider instead of using it: the
assistant keeps the on-device model, and this module keeps the held backend and
the :class:`~quill.core.ai.fallback.FallbackPlan` whose announcement is the
question. Ask Quill puts the question when it opens; Yes swaps the held backend
in (:meth:`quill.core.ai.assistant.Assistant.accept_substitute`), No keeps the
on-device model and sends nothing anywhere else. A substitute that is itself
on-device (Ollama, for instance) keeps the text on this computer, so it is used
directly, as before.

Module state, like ``assistant._LAST_BACKEND_NOTE`` beside it: resolution runs
once per assistant, on the UI thread, and the assistant takes what it needs at
construction. wx-free and strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.fallback import FallbackPlan, is_local_provider, plan_substitution

__all__ = ["fell_past", "hold_for_consent", "reset", "take"]

_fell_past = ""
_plan: FallbackPlan = FallbackPlan.none()
_held: Any = None


def reset() -> None:
    """Forget the last resolution; called as a new one starts."""
    global _fell_past, _plan, _held
    _fell_past, _plan, _held = "", FallbackPlan.none(), None


def fell_past(provider: str) -> None:
    """Record that resolution fell past the provider the person configured."""
    global _fell_past
    _fell_past = (provider or "").strip() or "Your configured AI provider"


def hold_for_consent(provider: str, backend: Any) -> bool:
    """Whether *backend* (for *provider*) must wait for a yes before it is used.

    True only when resolution has already fallen past a configured provider and
    *provider* is a different, off-device one. Then the backend and the plan
    are kept for :func:`take`, and the caller carries on to the on-device model.
    """
    global _plan, _held
    if not _fell_past:
        return False
    plan = plan_substitution(
        chosen=_fell_past,
        substitute=provider,
        substitute_is_local=is_local_provider(provider),
    )
    if not plan.requires_consent:
        return False
    _plan, _held = plan, backend
    return True


def take() -> tuple[FallbackPlan, Any]:
    """The held plan and backend (``FallbackPlan.none()``, None when nothing is
    held), handed over once: a second assistant does not inherit the question."""
    global _plan, _held
    plan, held = _plan, _held
    _plan, _held = FallbackPlan.none(), None
    return plan, held
