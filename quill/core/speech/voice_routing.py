"""Voice utterance routing (Hey QUILL Phase 4).

Pure, wx-free: decide what a spoken utterance *is* before the UI acts on it —
a cancel phrase, a question to hand to Ask Quill, or a command/other to resolve
against the safe-tool allowlist. Keeping the decision here makes it testable
with plain strings and keeps one definition of "this sounds like a question."

Routing never runs anything and never calls the AI; it only classifies. The UI
still enforces consent and the allowlist: a ``QUESTION`` route opens Ask Quill
with the text pre-filled (a person presses send), and a ``COMMAND`` route goes
through the same safe-tool resolution as every other voice surface.
"""

from __future__ import annotations

from quill.core.speech.voice_commands import CANCEL_PHRASES, normalize

#: Route kinds.
CANCEL = "cancel"
QUESTION = "question"
COMMAND = "command"

#: Explicit "send this to the assistant" lead-ins. After one of these, the rest
#: of the utterance is the question (even if it has no question word).
_ASK_PREFIXES = ("ask quill", "ask", "question", "hey quill ask")

#: Leading words that make an utterance a question by shape.
_QUESTION_WORDS = frozenset({
    "what",
    "whats",
    "who",
    "whos",
    "where",
    "wheres",
    "when",
    "whens",
    "why",
    "how",
    "hows",
    "which",
    "can",
    "could",
    "would",
    "should",
    "is",
    "are",
    "do",
    "does",
    "did",
    "will",
    "explain",
    "define",
    "summarize",
    "tell",
})


def classify(transcript: str) -> str:
    """Return the route for ``transcript``: :data:`CANCEL`, :data:`QUESTION`,
    or :data:`COMMAND`."""
    spoken = normalize(transcript)
    if not spoken:
        return COMMAND
    if spoken in CANCEL_PHRASES:
        return CANCEL
    if _extract_question(spoken) is not None:
        return QUESTION
    return COMMAND


def _extract_question(spoken: str) -> str | None:
    """The question text if ``spoken`` (already normalized) is a question, else
    ``None``. An explicit ask-prefix or a question-word lead-in both count; a
    trailing question mark is normalized away, so shape carries the signal."""
    for prefix in _ASK_PREFIXES:
        if spoken == prefix:
            return ""
        lead = f"{prefix} "
        if spoken.startswith(lead):
            return spoken[len(lead) :].strip()
    first = spoken.split(" ", 1)[0]
    if first in _QUESTION_WORDS:
        return spoken
    return None


def question_text(transcript: str) -> str:
    """The question to hand to Ask Quill (prefix stripped), or the *normalized*
    utterance (lowercased, punctuation stripped) for a bare question. Empty
    when it is not a question."""
    result = _extract_question(normalize(transcript))
    if result is None:
        return ""
    # A bare "ask" with nothing after it: fall back to the raw transcript so the
    # composer is not empty.
    return result or transcript.strip()


__all__ = ["CANCEL", "COMMAND", "QUESTION", "classify", "question_text"]
