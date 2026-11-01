"""Which AI is in use: the one stored choice, its migration, and the words for it.

Choose Your AI (codex.md 10A) replaces a silent precedence -- a ChatGPT
sign-in, else a saved key, else the free AI -- with **one stored choice**,
``ai_connection``, the same field name in QUILL's and QUILL Lite's settings.
This module is everything about that choice that is not a window: what the
values are, how an older profile is migrated once, which connections are
ready, what each row of the window says, and the sentences a request speaks
when the choice cannot be honoured.

**No fall-through.** When the connection in use is not ready the request
fails with a sentence naming why (10A.5); it never quietly goes to the free AI
or a key (decision 15). Signing out of the row in use leaves no AI in use
until the person chooses one.

wx-free and strict-typed. Every sentence here is spoken and brailled by the
app's announcement service, so each is plain text (decision 13).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.ai.connection_caps import (
    CHATGPT,
    CODEX,
    CONNECTION_NAMES,
    CONNECTIONS,
    COPILOT,
    FREE,
    OWN_KEY,
)
from quill.core.ai.own_key_providers import PROVIDER_NAMES

__all__ = [
    "CHOICE_VALUES",
    "IN_USE",
    "NOT_AVAILABLE_YET",
    "NOT_FOR_ACCOUNT",
    "NOT_SET_UP",
    "NO_AI_IN_USE",
    "ROW_STATES",
    "SIGNED_IN",
    "SIGNED_OUT_BY_GITHUB",
    "SIGNED_OUT_BY_OPENAI",
    "ConnectionFacts",
    "ConnectionRow",
    "in_use",
    "legacy_route",
    "limit_sentence",
    "load_ai_fields",
    "load_connection_fields",
    "migrate_choice",
    "normalize_choice",
    "not_for_account_sentence",
    "not_ready_sentence",
    "ready",
    "request_route",
    "revoked_sentence",
    "row_states",
]

#: The stored values; "" means "not yet decided" and is migrated on first read.
CHOICE_VALUES: tuple[str, ...] = ("", *CONNECTIONS)

# -- row states (10A.3) ---------------------------------------------------------- #

IN_USE = "in_use"
SIGNED_IN = "signed_in"
NOT_SET_UP = "not_set_up"
SIGNED_OUT_BY_OPENAI = "signed_out_by_openai"
SIGNED_OUT_BY_GITHUB = "signed_out_by_github"
NOT_AVAILABLE_YET = "not_available_yet"
#: GitHub said Copilot is switched off for this account (R15, 10A.4).
NOT_FOR_ACCOUNT = "not_for_account"

#: Each state as the row reads it after the connection's name.
ROW_STATES: dict[str, str] = {
    IN_USE: "in use",
    SIGNED_IN: "signed in",
    NOT_SET_UP: "not set up",
    SIGNED_OUT_BY_OPENAI: "signed out by OpenAI",
    SIGNED_OUT_BY_GITHUB: "signed out by GitHub",
    NOT_AVAILABLE_YET: "not available yet",
    NOT_FOR_ACCOUNT: "not available for your account",
}

#: Said once by the next AI command after the row in use was signed out.
NO_AI_IN_USE = "No AI is in use. Choose one."

_OWN_KEY_PROVIDER_NAMES = PROVIDER_NAMES


# -- settings -------------------------------------------------------------------- #


def normalize_choice(value: object) -> str:
    """A stored choice, or "" for anything that is not one of the five."""
    text = str(value or "").strip().lower()
    return text if text in CONNECTIONS else ""


def load_connection_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    """``ai_connection``, ``ai_copilot_model`` and ``ai_codex_model``, cleaned.

    The one validator both editors' loaders use, so a hand-edited value means
    the same thing in each: an unknown connection is "not yet decided", and is
    migrated, rather than a guess.
    """
    return {
        "ai_connection": normalize_choice(data.get("ai_connection", "")),
        "ai_copilot_model": str(data.get("ai_copilot_model", "") or "").strip(),
        "ai_codex_model": str(data.get("ai_codex_model", "") or "").strip(),
    }


def load_ai_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    """Every hosted-AI field QUILL's settings loader reads: own key and connection."""
    from quill.core.ai.own_key import load_settings_fields

    return load_settings_fields(data) | load_connection_fields(data)


def legacy_route(*, chatgpt_signed_in: bool, own_key_ready: bool) -> str:
    """What the silent precedence chose before Choose Your AI (10A.1)."""
    if chatgpt_signed_in:
        return CHATGPT
    if own_key_ready:
        return OWN_KEY
    return FREE


def migrate_choice(
    settings: Any,
    *,
    chatgpt_signed_in: Callable[[], bool],
    own_key_ready: Callable[[], bool],
    save: Callable[[], None] | None = None,
) -> str:
    """The stored choice, set once from :func:`legacy_route` when it is empty.

    So nobody's behaviour changes on upgrade: the first read with an empty
    ``ai_connection`` stores what the old precedence would have picked and
    saves it (each editor's save goes through ``write_json_atomic``). A
    settings object without the field at all -- an older stand-in -- gets the
    old precedence live and nothing is stored.
    """
    if settings is None or not hasattr(settings, "ai_connection"):
        return legacy_route(chatgpt_signed_in=chatgpt_signed_in(), own_key_ready=own_key_ready())
    stored = normalize_choice(getattr(settings, "ai_connection", ""))
    if stored:
        return stored
    chosen = legacy_route(chatgpt_signed_in=chatgpt_signed_in(), own_key_ready=own_key_ready())
    settings.ai_connection = chosen
    if save is not None:
        try:
            save()
        except Exception:  # noqa: BLE001 - the choice holds for this session regardless
            pass
    return chosen


# -- readiness ------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ConnectionFacts:
    """What this computer knows about every connection, read without a network call."""

    stored: str
    free_connected: bool = False
    chatgpt_signed_in: bool = False
    #: OpenAI refused the sign-in (a 401, or a refresh it called dead).
    chatgpt_ended: bool = False
    own_key_ready: bool = False
    own_key_provider: str = "openai"
    copilot_signed_in: bool = False
    copilot_ended: bool = False
    #: Whether this build carries the connection at all (Phase 1: neither).
    copilot_available: bool = False
    codex_available: bool = False
    #: GitHub said Copilot is switched off for this account (R15).
    copilot_policy_off: bool = False

    def available(self, connection: str) -> bool:
        if connection == COPILOT:
            return self.copilot_available
        if connection == CODEX:
            return self.codex_available
        return connection in CONNECTIONS


def ready(facts: ConnectionFacts, connection: str) -> bool:
    """Whether a request could go to *connection* now.

    The free AI is always ready: its one Connect step happens when the first
    command needs it (decision 23), not as a precondition of choosing it.
    """
    if not facts.available(connection):
        return False
    if connection == FREE:
        return True
    if connection in (CHATGPT, CODEX):
        return facts.chatgpt_signed_in
    if connection == COPILOT:
        return facts.copilot_signed_in and not facts.copilot_policy_off
    if connection == OWN_KEY:
        return facts.own_key_ready
    return False


def in_use(facts: ConnectionFacts) -> str:
    """The connection in use, or "" when none is (signed out of the row in use)."""
    return facts.stored if facts.stored and ready(facts, facts.stored) else ""


def request_route(connection: str) -> str:
    """Where a single request travels for *connection*.

    Codex is an agent engine; its single requests go over the ChatGPT plan's
    direct route with the same sign-in (decision 21), so starting a child
    process for one rewrite never happens.
    """
    return CHATGPT if connection == CODEX else connection


# -- the window's rows ------------------------------------------------------------ #


@dataclass(frozen=True, slots=True)
class ConnectionRow:
    """One row of Choose Your AI, ready to read."""

    connection: str
    name: str
    state: str

    @property
    def text(self) -> str:
        """The row as read: QUILL's free AI, in use; My own key, OpenAI, signed in."""
        return f"{self.name}, {ROW_STATES[self.state]}"


def _row_state(facts: ConnectionFacts, connection: str, active: str) -> str:
    if not facts.available(connection):
        return NOT_AVAILABLE_YET
    if connection == COPILOT and facts.copilot_policy_off:
        return NOT_FOR_ACCOUNT
    if connection == active:
        return IN_USE
    if connection in (CHATGPT, CODEX) and facts.chatgpt_ended and not facts.chatgpt_signed_in:
        return SIGNED_OUT_BY_OPENAI
    if connection == COPILOT and facts.copilot_ended and not facts.copilot_signed_in:
        return SIGNED_OUT_BY_GITHUB
    if connection == FREE:
        return SIGNED_IN if facts.free_connected else NOT_SET_UP
    return SIGNED_IN if ready(facts, connection) else NOT_SET_UP


def _row_name(facts: ConnectionFacts, connection: str) -> str:
    name = CONNECTION_NAMES[connection]
    if connection == OWN_KEY and facts.own_key_ready:
        provider = _OWN_KEY_PROVIDER_NAMES.get(facts.own_key_provider, facts.own_key_provider)
        return f"{name}, {provider}"
    return name


def row_states(facts: ConnectionFacts) -> list[ConnectionRow]:
    """Every row of the window, in order, with the state it reads (10A.3)."""
    active = in_use(facts)
    return [
        ConnectionRow(c, _row_name(facts, c), _row_state(facts, c, active)) for c in CONNECTIONS
    ]


# -- the sentences of 10A.5 -------------------------------------------------------- #


def revoked_sentence(connection: str) -> str:
    """Said when OpenAI or GitHub ended the sign-in: nothing was sent, nothing retried."""
    if connection == COPILOT:
        return (
            "Your GitHub Copilot sign-in has ended. Nothing was sent. "
            "Press Ctrl+4 to sign in again or choose another."
        )
    return (
        "Your ChatGPT plan sign-in has ended. Nothing was sent. "
        "Press Ctrl+4 to sign in again or choose another."
    )


def limit_sentence(connection: str, app_name: str) -> str:
    """Said once when a limit is reached; never retried, never switched."""
    app = app_name or "QUILL"
    owner = {
        CHATGPT: "Your ChatGPT plan's",
        CODEX: "Your ChatGPT plan's",
        COPILOT: "Your GitHub Copilot",
        OWN_KEY: "Your own key's",
        FREE: "QUILL's free AI",
    }.get(connection, "This connection's")
    return (
        f"{owner} limit for {app} is reached. Nothing was sent. "
        "Manage usage is in the Usage window."
    )


def not_for_account_sentence() -> str:
    """Said when GitHub reports Copilot switched off for the account (R15)."""
    return (
        "My GitHub Copilot is not available for your account; your organisation "
        "or plan has it switched off. Nothing was sent. Press Ctrl+4 to choose another."
    )


def not_ready_sentence(facts: ConnectionFacts) -> str:
    """Why the stored choice cannot take a request right now, or "" when it can."""
    stored = facts.stored
    if stored and ready(facts, stored):
        return ""
    if stored in (COPILOT, CODEX) and not facts.available(stored):
        name = "My GitHub Copilot" if stored == COPILOT else "Codex"
        return f"{name} is not available yet. Nothing was sent. Press Ctrl+4 to choose another."
    if stored in (CHATGPT, CODEX) and facts.chatgpt_ended:
        return revoked_sentence(CHATGPT)
    if stored == COPILOT and facts.copilot_policy_off:
        return not_for_account_sentence()
    if stored == COPILOT and facts.copilot_ended:
        return revoked_sentence(COPILOT)
    return NO_AI_IN_USE
