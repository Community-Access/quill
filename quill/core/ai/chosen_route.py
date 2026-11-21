"""QUILL's advanced AI commands, sent on the AI chosen in Choose Your AI (codex.md 10A).

QUILL had two ways of deciding where an AI request went. The AI menu's own
commands follow the one stored choice, ``ai_connection``, through the shared
route (:class:`quill.ui.hosted_ai_connection_route.ConnectionRouteMixin`): it
refuses with a sentence when the chosen AI is not ready, asks "Send to a
Different AI?" before another company is used, and names Auto's pick before
sending. The older, advanced commands -- spell check, grammar, translate,
Document Q&A, rewrite, summarize, Ask Quill, the agents, Improve Reading Order,
Train Writing Style, chapter inference, the watch folder and GitHub's AI
commands -- read a separate choice, ``assistant-connection.json``, which Which
AI Am I Using never described. Jeff's decision (2026-11-20): they follow Choose
Your AI too.

They all reach a provider through one function,
:func:`quill.core.assistant_ai.generate_assistant_response`, with an
:class:`~quill.core.assistant_ai.AssistantConnectionSettings`. So the route is
one more "provider" there: :data:`ROUTE_PROVIDER`. Settings naming it are
handed to the **sender** the editor registers at start-up
(:func:`set_sender`), which asks the shared route where the request may go --
with every check and question that route makes -- and sends it there. Nothing
in the feature code has to know.

An app that registers no sender (QUILL Studio, the standalone tools) keeps its
own provider settings; :func:`active` says whether this process has the route.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.error_codes import CodedError

if TYPE_CHECKING:
    from quill.core.assistant_ai import AssistantConnectionSettings

__all__ = [
    "ROUTE_PROVIDER",
    "ChosenRouteError",
    "Sender",
    "active",
    "choose",
    "describe",
    "route_settings",
    "send",
    "send_picture",
    "send_streamed",
    "set_sender",
]

#: The provider name that means "the AI chosen in Choose Your AI".
ROUTE_PROVIDER = "choose_your_ai"

#: ``sender(prompt, system_prompt) -> answer``; raises with a finished sentence.
#: A sender may also have ``picture(path, prompt) -> answer`` for pictures.
Sender = Callable[[str, str], str]

_sender: Any = None


class ChosenRouteError(CodedError):
    """The chosen AI could not take the request; the message is the sentence to say."""

    code = "QUILL-AI-ROUTE-REFUSED"
    user_hint = "Press Ctrl+4 to see which AI is in use, or to choose another."


def set_sender(sender: Sender | None) -> None:
    """Register (or, with None, remove) the editor's sender for the chosen AI."""
    global _sender
    _sender = sender


def active() -> bool:
    """Whether this process sends its advanced AI requests on the chosen AI."""
    return _sender is not None


def describe() -> str:
    """The AI in use, as Choose Your AI names it, or "" without a sender."""
    try:
        return str(getattr(_sender, "describe", lambda: "")())
    except Exception:  # noqa: BLE001 - a description is never worth a crash
        return ""


def choose() -> bool:
    """Open Choose Your AI; False when this process has no route."""
    opener = getattr(_sender, "choose", None)
    if opener is None:
        return False
    opener()
    return True


def route_settings() -> AssistantConnectionSettings:
    """Connection settings that mean "the AI chosen in Choose Your AI"."""
    from quill.core.assistant_ai import AssistantConnectionSettings

    return AssistantConnectionSettings(provider=ROUTE_PROVIDER, host="", model="")


def send(prompt: str, system_prompt: str = "") -> tuple[str | None, str | None]:
    """Send *prompt* on the chosen AI: ``(text, None)``, or ``(None, sentence)``."""
    sender = _sender
    if sender is None:
        return None, "No AI is in use. Press Ctrl+4 to choose one."
    return _answer(lambda: str(sender(prompt, system_prompt)))


def send_streamed(prompt: str, on_delta: Callable[[str], None]) -> tuple[str | None, str | None]:
    """:func:`send`, with the whole answer delivered to *on_delta* once."""
    text, error = send(prompt)
    if text:
        on_delta(text)
    return text, error


def send_picture(path: Path, prompt: str) -> tuple[str | None, str | None]:
    """Ask the chosen AI about the picture at *path*, after its picture consent."""
    picture = getattr(_sender, "picture", None)
    if picture is None:
        return None, "No AI is in use. Press Ctrl+4 to choose one."
    return _answer(lambda: str(picture(path, prompt)))


def _answer(work: Callable[[], str]) -> tuple[str | None, str | None]:
    try:
        return work(), None
    except ChosenRouteError as refused:
        return None, str(refused.args[0]) if refused.args else "Nothing was sent."
    except Exception as error:  # noqa: BLE001 - every failure is a sentence here
        return None, str(error) or "The AI did not answer. Nothing was changed."
