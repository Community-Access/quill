"""Plain-language wording for errors returned by the AI assistant."""

from __future__ import annotations

__all__ = ["classify_assistant_error"]

#: Words a provider's error uses for each kind: a refused key, a limit or
#: overload that passes, and a connection that never arrived.
_AI_SIGNED_OUT = ("401", "unauthorized", "invalid api key", "invalid_api_key", "authentication")
_AI_BUSY = ("429", "rate limit", "rate_limit", "overloaded", "quota", "503")
_AI_OFFLINE = ("timed out", "timeout", "connection", "network", "could not resolve", "unreachable")


def classify_assistant_error(error: str) -> tuple[str, bool]:
    """Return (user-facing message, whether to disable input)."""
    text = (error or "").strip()
    lowered = text.lower()
    if "failed to load native code" in lowered or "0xc000001d" in lowered:
        return (
            "On-device AI couldn't start. This processor may not support the built-in "
            "AI engine. Use the setup strip to connect a cloud provider, or turn AI off "
            "from Tools > AI Assistant.",
            True,
        )
    if any(word in lowered for word in _AI_SIGNED_OUT):
        lead = (
            "The AI provider did not accept the key or sign-in. Check it in the AI Hub, "
            "or pick another AI with Choose Your AI."
        )
    elif any(word in lowered for word in _AI_BUSY):
        lead = (
            "The AI provider is busy or a usage limit was reached. Wait a minute, then send again."
        )
    elif any(word in lowered for word in _AI_OFFLINE):
        lead = "QUILL could not reach the AI provider. Check the connection, then send again."
    else:
        lead = "The AI provider returned an error."
    lead += " Your document was not changed."
    return (f"{lead} Details: {text}" if text else lead, False)
