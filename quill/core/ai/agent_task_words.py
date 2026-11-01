"""What the agent window says (codex.md 5.2, 5.3, 6.2): its status line and sentences.

The window (:mod:`quill.ui.agent_window`) composes none of its own, so QUILL and
QUILL Lite cannot word the same moment two ways (rule 10) and a test can read
the words without a window. Everything is text (decision 13).

**Spoken outcomes only (GATE-13).** The status line and the transcript change
silently; the app speaks only what it alone knows -- a task's closing summary,
a task that could not start -- through the announcement service, so it is
brailled too (GATE-BRAILLE). Opening the window and the approval question are
said by the reader, never by the app.

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.ai.connection_caps import CODEX, COPILOT

__all__ = [
    "APPROVAL_TITLE",
    "NO_ENGINE",
    "STOPPING",
    "TITLE",
    "WORKING",
    "engine_name",
    "status_line",
    "transcript_line",
]

TITLE = "Do a Document Task"
APPROVAL_TITLE = "Allow This Step?"

_USING: dict[str, str] = {
    COPILOT: "Using GitHub Copilot",
    CODEX: "Using Codex on your ChatGPT plan",
}

WORKING = "Working."
STOPPING = "Stopping."
NO_ENGINE = "Document tasks need My GitHub Copilot or Codex. Press Ctrl+4 to choose one."


def status_line(connection: str, state: str = "") -> str:
    """The status line: "Using GitHub Copilot", then what is happening, if anything."""
    using = _USING.get(connection, "No engine")
    return f"{using}. {state}".strip() if state else using


def transcript_line(who: str, text: str) -> str:
    """One turn of the transcript: "You: ..." or "GitHub Copilot: ..."."""
    return f"{who}: {text.strip()}"


def engine_name(connection: str) -> str:
    """Who speaks in the transcript for *connection*."""
    return "Codex" if connection == CODEX else "GitHub Copilot"
