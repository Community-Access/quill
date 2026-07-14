"""AI summaries of GitHub issue/PR discussion threads.

Unified GitHub Management, "AI Summarization": a long issue thread or PR
discussion condensed to a screen-reader-friendly TL;DR — the decision so far,
open questions, and next steps — through the same assistant connection (and
the same consent gates) every other QUILL AI feature uses. One bounded
completion per explicit request; nothing runs automatically.

wx-free; the UI resolves the connection (consent, key) and passes it in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.core.error_codes import CodedError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from quill.core.assistant_ai import AssistantConnectionSettings

__all__ = ["ThreadSummaryError", "compose_thread_text", "summarize_thread"]

#: Keep the prompt bounded: a monster thread is truncated middle-out so the
#: opening post and the latest comments (where the current state lives) survive.
_MAX_THREAD_CHARS = 24_000

_PROMPT_TEMPLATE = (
    "Summarize this GitHub discussion for a screen reader user in plain "
    "prose, no markdown tables or decorations. Give: (1) one sentence on "
    "what the thread is about, (2) the current state or decision, (3) open "
    "questions if any, (4) the apparent next step. Be concrete and short — "
    "under 150 words.\n\nThe discussion:\n\n{thread}"
)


class ThreadSummaryError(CodedError):
    """The thread summary could not be produced (no AI, provider error)."""

    code = "QUILL-GITHUB-THREAD-SUMMARY"


def compose_thread_text(title: str, author: str, body: str, comments: list[dict[str, str]]) -> str:
    """Flatten an issue/PR thread into the text the summary prompt consumes."""
    parts = [f"Title: {title}", f"Opened by: {author}", "", body.strip(), ""]
    for comment in comments:
        parts.append(
            f"Comment by {comment.get('author', '?')} ({comment.get('created_at', '')[:10]}):"
        )
        parts.append(str(comment.get("body", "")).strip())
        parts.append("")
    text = "\n".join(parts).strip()
    if len(text) > _MAX_THREAD_CHARS:
        half = _MAX_THREAD_CHARS // 2
        text = text[:half] + "\n\n[... middle of the thread truncated ...]\n\n" + text[-half:]
    return text


def summarize_thread(
    connection: AssistantConnectionSettings,
    api_key: str,
    thread_text: str,
    *,
    timeout_seconds: float = 60.0,
) -> str:
    """Return the TL;DR for *thread_text*, or raise :class:`ThreadSummaryError`."""
    from quill.core.assistant_ai import generate_assistant_response

    text = thread_text.strip()
    if not text:
        raise ThreadSummaryError("There is no discussion text to summarize.")
    response, error = generate_assistant_response(
        connection,
        api_key,
        _PROMPT_TEMPLATE.format(thread=text),
        max_tokens=512,
        timeout_seconds=timeout_seconds,
    )
    if error:
        raise ThreadSummaryError(error)
    summary = (response or "").strip()
    if not summary:
        raise ThreadSummaryError("The AI returned an empty summary; try again.")
    return summary
