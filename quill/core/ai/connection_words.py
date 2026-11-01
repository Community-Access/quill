"""What Choose Your AI says: the row's action, the About line and the outcomes.

The window itself (:mod:`quill.ui.hosted_ai_connections`) composes nothing; it
reads every sentence from here, so QUILL and QUILL Lite cannot word the same
moment two ways (rule 10), and a test can read the words without a window.

**Spoken outcomes only (GATE-13).** Nothing here is said on open, on focus or
on a selection change -- the reader already says the title, the row and its
state. The sentences below are the outcomes only the app knows: a sign-in that
finished, a switch, a sign-out. They go through the announcement service, so
they are brailled too (GATE-BRAILLE).

wx-free and strict-typed (decision 13: every word is text).
"""

from __future__ import annotations

from quill.core.ai.connection_caps import (
    AGENT_TOOLS,
    CHATGPT,
    CODEX,
    CONNECTION_NAMES,
    COPILOT,
    FREE,
    OWN_KEY,
    PICTURES,
    TEXT,
    ConnectionRecord,
)
from quill.core.ai.connection_choice import IN_USE, SIGNED_IN, ConnectionRow
from quill.core.ai.own_key_providers import COMPANIES, LOCAL_ABOUT, is_local
from quill.core.ai.own_key_providers import CUSTOM as _CUSTOM

__all__ = [
    "ACTION_LABELS",
    "CODEX_MODEL",
    "COMMAND_NEEDS",
    "FREE_MODEL",
    "MODELS_FAILED",
    "NOT_AVAILABLE_MODELS",
    "SAFE_MODE_ABOUT",
    "SIGNED_OUT_IN_USE",
    "SIGN_IN",
    "SIGN_IN_FOR_MODELS",
    "SIGN_OUT",
    "USE",
    "about_line",
    "asking_sentence",
    "engine_unavailable_about",
    "model_items",
    "not_available_sentence",
    "now_using",
    "row_action",
    "sign_in_sentence",
    "signed_in_sentence",
    "signed_out_sentence",
    "with_needs",
]

# -- the one action button (10A.3) -------------------------------------------- #

USE = "use"
SIGN_IN = "sign_in"
SIGN_OUT = "sign_out"

#: The button's label for each action. Three letters, distinct from each other
#: and from everything else in the window (GATE-14): U, S and O.
ACTION_LABELS: dict[str, str] = {
    USE: "&Use This",
    SIGN_IN: "&Sign In...",
    SIGN_OUT: "Sign &Out",
}


def row_action(row: ConnectionRow, *, free_connected: bool) -> str:
    """What the action button does on *row*: use it, sign in, or sign out.

    The free AI is the one row that can be in use without being connected
    (decision 23: Connect happens when somebody asks). Its button then
    connects, because signing out of something not signed in does nothing.
    """
    if row.state == IN_USE:
        if row.connection == FREE and not free_connected:
            return SIGN_IN
        return SIGN_OUT
    if row.state == SIGNED_IN:
        return USE
    return SIGN_IN


# -- the About line ------------------------------------------------------------- #

SAFE_MODE_ABOUT = "AI is off in Safe Mode. Nothing can be signed in until QUILL starts normally."

_WHO_PAYS: dict[str, str] = {
    FREE: "Goes to QUILL's service, free within its limits.",
    CHATGPT: "Goes to OpenAI and counts toward your ChatGPT plan.",
    COPILOT: "Billed to your Copilot plan.",
    CODEX: "Runs tasks on your ChatGPT plan.",
}

_OWN_KEY_COMPANY = COMPANIES


def about_line(record: ConnectionRecord, *, own_key_provider: str = "openai") -> str:
    """Who receives the text, what it costs and what it can do, from the registry.

    "Text and pictures. Agent tasks: yes. Billed to your Copilot plan."
    """
    pictures = record.claim(PICTURES)
    what = "Text only."
    if pictures.supported:
        per_model = "per model" in pictures.note
        what = "Text and pictures, per model." if per_model else "Text and pictures."
    tasks = "Agent tasks: yes." if record.claim(AGENT_TOOLS).supported else "Agent tasks: no."
    if record.connection == OWN_KEY:
        company = _OWN_KEY_COMPANY.get(own_key_provider, own_key_provider)
        who = f"Goes to {company}, billed per request to your own key."
        if is_local(own_key_provider):
            who = LOCAL_ABOUT
        elif own_key_provider == _CUSTOM:
            who = f"Goes to {company}, under that service's own terms."
    else:
        who = _WHO_PAYS.get(record.connection, "")
    line = " ".join(part for part in (what, tasks, who) if part)
    if not record.available:
        return f"Not available yet; it comes in a later update. {line}"
    return line


# -- the model choice (10A.3, 10A.4) --------------------------------------------- #

FREE_MODEL = "QUILL chooses the model"
#: Codex runs on the plan; its single requests use the plan's own model (10A.13).
CODEX_MODEL = "Codex chooses the model"
SIGN_IN_FOR_MODELS = "Sign in to see the models"
NOT_AVAILABLE_MODELS = "Not available yet"
MODELS_FAILED = "Could not read the model list. The recommended model is used."


def model_items(labels: list[str]) -> list[str]:
    """The Model choice's items: the service's own order, its first marked
    "(recommended)" -- that order is the service's recommendation, never ours."""
    if not labels:
        return []
    return [f"{labels[0]} (recommended)", *labels[1:]]


# -- the sentences ---------------------------------------------------------------- #

SIGNED_OUT_IN_USE = "Signed out. No AI is in use until you choose one."

_COMPANY_PAGE = {CHATGPT: "OpenAI's", CODEX: "OpenAI's", COPILOT: "GitHub's"}


def now_using(connection: str) -> str:
    """Use This, or a switch the capability offer made."""
    return f"Now using {CONNECTION_NAMES.get(connection, connection)}."


def signed_in_sentence(connection: str) -> str:
    """A sign-in that finished: signing in is choosing (10A.5)."""
    return f"Signed in to {CONNECTION_NAMES.get(connection, connection)}. It is now in use."


def signed_out_sentence(connection: str, *, was_in_use: bool) -> str:
    """A sign-out. Out of the row in use, nothing is in use (decision 15)."""
    if connection == FREE:
        return "Signed out. This computer is no longer connected to QUILL's free AI."
    if was_in_use:
        return SIGNED_OUT_IN_USE
    return f"Signed out of {CONNECTION_NAMES.get(connection, connection)}."


def not_available_sentence(connection: str) -> str:
    """The Copilot and Codex rows, until their phases ship."""
    return (
        f"{CONNECTION_NAMES.get(connection, connection)} is not available yet. "
        "It comes in a later update."
    )


def engine_unavailable_about(
    connection: str, *, registered: bool = True, app_name: str = "QUILL"
) -> str:
    """The About line for a Copilot or Codex row this build cannot offer: one sentence.

    *registered* is False when this app has no GitHub sign-in registration yet
    (Copilot's client id, 10A.12); otherwise the engine is missing from the build.
    """
    app = app_name or "QUILL"
    if connection == COPILOT and not registered:
        return (
            f"Not available yet: GitHub sign-in for {app} has not been registered, "
            "so it comes in a later update."
        )
    engine = "GitHub Copilot" if connection == COPILOT else "Codex"
    return f"Not available yet: this copy of {app} does not include the {engine} engine."


def sign_in_sentence(connection: str, app_name: str) -> str:
    """The sign-in step's one sentence: the same shape for every connection."""
    page = _COMPANY_PAGE.get(connection, "the service's")
    name = CONNECTION_NAMES.get(connection, connection)
    return f"To use {name}, approve {app_name or 'QUILL'} on {page} page."


def asking_sentence(connection: str) -> str:
    """The first line of Ask (10C.2): which connection is being asked."""
    if not connection:
        return "No AI is in use. Press Ctrl+4 to choose one."
    return f"Asking {CONNECTION_NAMES.get(connection, connection)} about this document."


# -- capability gating (10A.8) ------------------------------------------------------ #

#: What each gated AI command needs, by QUILL Lite handler. QUILL reads the same
#: table through ``COMMAND_EQUIVALENTS`` so one list governs both editors.
COMMAND_NEEDS: dict[str, str] = {
    "cmd_ai_assistant": TEXT,
    "cmd_ai_ask_document": TEXT,
    "cmd_ai_chat_key": TEXT,
    "cmd_ai_prompt_library": TEXT,
    "cmd_ai_image": PICTURES,
    "cmd_studio_describe_picture": PICTURES,
    # codex.md Phase 3: the small apps' first features.
    "cmd_weather_go_out": TEXT,
    "cmd_converter_will_play": TEXT,
    "cmd_player_chapter_summary": TEXT,
    "cmd_player_recap": TEXT,
    "cmd_inkwell_suggest": TEXT,
    "cmd_beacon_describe_picture": PICTURES,
    "cmd_dictation_tidy": TEXT,
    "cmd_ai_task": AGENT_TOOLS,
}


def with_needs(label: str, suffix: str) -> str:
    """*label* with "(needs ...)" after the name and before any ellipsis.

    "Ask About an Image..." becomes "Ask About an Image (needs a connection
    that sees)...": the name stays first, so first-letter navigation and the
    access key still land on it.
    """
    if not suffix:
        return label
    if label.endswith("..."):
        return f"{label[:-3]} {suffix}..."
    return f"{label} {suffix}"
