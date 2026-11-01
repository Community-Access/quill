"""The first-time consent for pictures, per app and per connection (codex.md 10B.4).

A picture is not text: a screenshot can carry a name, an inbox or a password
field nobody meant to share. So the first time a person asks an app about a
picture on a connection, the app says where it goes in one sentence -- "Pictures
you ask about in QUILL Studio go to OpenAI on your ChatGPT plan. Nothing is sent
until you ask." -- and asks Yes or No, No the default. The answer is kept per
connection, and per company for an own key, because a change of connection is
a change of who receives the picture: the question is asked again then.

This module only holds the words and the bookkeeping; the app keeps the list
in its own settings and shows the question. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable

from quill.core.ai.connection_caps import CHATGPT, CODEX, COPILOT, FREE, OWN_KEY
from quill.core.ai.own_key_providers import COMPANIES, is_local

__all__ = ["consent_key", "consent_sentence", "given", "needs_consent", "receiver"]

_RECEIVERS = {
    CHATGPT: "OpenAI on your ChatGPT plan",
    CODEX: "OpenAI on your ChatGPT plan",
    COPILOT: "GitHub on your Copilot plan",
    FREE: "QUILL's free AI service",
}
_OWN_KEY_COMPANY = COMPANIES


def receiver(connection: str, own_key_provider: str = "openai") -> str:
    """Who receives a picture on *connection*: "OpenAI on your ChatGPT plan"."""
    if connection == OWN_KEY:
        company = _OWN_KEY_COMPANY.get(own_key_provider, own_key_provider or "the company")
        if is_local(own_key_provider):
            return f"{company}, and nowhere else"
        return f"{company}, billed to your own key"
    return _RECEIVERS.get(connection, connection)


def consent_key(connection: str, own_key_provider: str = "openai") -> str:
    """What a consent is remembered under: the connection, and an own key's company."""
    if connection == OWN_KEY:
        return f"{OWN_KEY}:{own_key_provider or 'openai'}"
    return connection


def consent_sentence(app_name: str, connection: str, own_key_provider: str = "openai") -> str:
    """The question's text, without the question mark's question."""
    return (
        f"Pictures you ask about in {app_name} go to "
        f"{receiver(connection, own_key_provider)}. Nothing is sent until you ask."
    )


def needs_consent(consented: Iterable[str], key: str) -> bool:
    """Whether the question must be asked before a picture goes on *key*."""
    return key not in set(consented)


def given(consented: Iterable[str], key: str) -> list[str]:
    """*consented* with *key* added once, in the order the answers came."""
    kept = [str(item) for item in consented]
    return kept if key in kept else [*kept, key]
