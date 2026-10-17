"""Moving around an AI conversation: numbered messages, the recent ten, and
headings that nest under the speaker.

Shared by both conversation windows -- Ask Quill (QUILL) and the AI
Conversation window both editors open (:mod:`quill.ui.hosted_ai_chat`) -- so
the two count, name and read messages the same way. wx-free and strict-typed.

**Numbering.** Every message is "Message 3 of 12, AI": the speaker and where
it sits are said together, so a listener who jumped in from a key never has to
work out whose words they are hearing or how far back they went.

**The recent ten.** Alt+1 reads the newest message, Alt+2 the one before it,
and so on to Alt+0 for the tenth newest. The keys only *read*: nothing moves,
the message box keeps focus and anything half-typed stays. With fewer
messages than the key asks for, the sentence says how many there are rather
than staying silent, because silence after a key press sounds like a broken
key. Prior art: chat clients built for screen-reader users have long given
the digit row this job; QUILL's windows never bound Alt with a digit, so the
keys are free in both (``tests/unit/ui/test_ai_conversation_tools.py``
checks that against every access key in both windows).

**Headings inside a reply.** Each message is shown under a level-2 heading
naming its speaker. A reply that starts with its own ``# Title`` would then
put a level-1 heading *inside* a level-2 one, and a screen reader's heading
list would show the reply's title as a sibling of the conversation rather
than part of one message. :func:`nest_reply_headings` moves a reply's
headings down so its shallowest becomes level 3, keeping their relative
depth, so heading navigation (H, and 1 to 6 by level) walks the conversation
and the reply's own sections in the order they nest. Fenced code is left
alone, because a ``#`` there is a comment, not a heading.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = [
    "RECENT_COUNT",
    "ChatMessage",
    "message_view_html",
    "nest_reply_headings",
    "number_messages",
    "recent_key_label",
    "recent_message",
    "recent_message_sentence",
    "row_label",
]

#: How many of the newest messages have a key of their own (Alt+1 .. Alt+0).
RECENT_COUNT = 10

_HEADING = re.compile(r"^(#{1,6})(\s+.*)$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_ROW_WORDS = 80


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One message, with where it sits in the conversation."""

    number: int  # 1 is the first message ever said
    total: int
    speaker: str
    text: str

    @property
    def position(self) -> str:
        """ "Message 3 of 12, AI": who said it and where it sits."""
        return f"Message {self.number} of {self.total}, {self.speaker}"


def number_messages(pairs: Iterable[tuple[str, str]]) -> list[ChatMessage]:
    """Number ``(speaker, text)`` turns from the first, oldest, message."""
    turns = [(str(speaker or "").strip() or "Unknown", str(text or "")) for speaker, text in pairs]
    total = len(turns)
    return [
        ChatMessage(index + 1, total, speaker, text) for index, (speaker, text) in enumerate(turns)
    ]


def row_label(message: ChatMessage) -> str:
    """A list row: the position, then the message's opening words on one line."""
    flat = " ".join(message.text.split())
    if len(flat) > _ROW_WORDS:
        flat = flat[:_ROW_WORDS].rstrip() + "..."
    return f"{message.position}: {flat}" if flat else f"{message.position}: (empty)"


def recent_key_label(n: int) -> str:
    """The key that reads the *n*-th newest message: Alt+1 .. Alt+9, then Alt+0."""
    if not 1 <= n <= RECENT_COUNT:
        raise ValueError(f"no key reads message {n} back")
    return f"Alt+{n % 10}"


def recent_message(messages: Sequence[ChatMessage], n: int) -> ChatMessage | None:
    """The *n*-th newest message (1 is the newest), or ``None`` past the oldest."""
    if n < 1 or n > len(messages):
        return None
    return messages[len(messages) - n]


def recent_message_sentence(messages: Sequence[ChatMessage], n: int) -> str:
    """What Alt+*n* says: the message, words not Markdown, with its position.

    The newest is introduced as "Newest" so the first key's answer is never
    ambiguous; with fewer messages than asked for, how many there are, and
    which key reads the oldest.
    """
    from quill.core.ai.spoken_answer import speakable_line

    if not messages:
        return "No messages yet."
    message = recent_message(messages, n)
    if message is None:
        count = len(messages)
        noun = "message" if count == 1 else "messages"
        return (
            f"There {'is' if count == 1 else 'are'} only {count} {noun} so far. "
            f"{recent_key_label(min(count, RECENT_COUNT))} reads the oldest."
        )
    spoken = speakable_line(message.text) or "(empty)"
    lead = "Newest, " if n == 1 else ""
    return f"{lead}{message.position}: {spoken}"


def nest_reply_headings(markdown: str, base_level: int = 3) -> str:
    """Move *markdown*'s headings down so the shallowest is *base_level*.

    Relative depth is kept (a reply's ``#`` and ``##`` become ``###`` and
    ``####``), nothing goes deeper than level 6, and lines inside fenced code
    are untouched. Text with no headings, or whose headings are already deep
    enough, comes back unchanged.
    """
    lines = (markdown or "").split("\n")
    shallowest = 7
    in_fence = False
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            match = _HEADING.match(line)
            if match:
                shallowest = min(shallowest, len(match.group(1)))
    shift = base_level - shallowest
    if shallowest == 7 or shift <= 0:
        return markdown or ""
    out: list[str] = []
    in_fence = False
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        match = None if in_fence else _HEADING.match(line)
        if match:
            level = min(6, len(match.group(1)) + shift)
            out.append("#" * level + match.group(2))
        else:
            out.append(line)
    return "\n".join(out)


def message_view_html(message: ChatMessage) -> str:
    """One message as HTML for the message viewer: a heading naming it, then
    the message rendered with its own headings nested beneath that one, and
    its tables as real tables a screen reader can move through by cell."""
    from html import escape

    from quill.core.browser_preview import _render_markdown

    body = _render_markdown(nest_reply_headings(message.text, 3))
    return f"<h2>{escape(message.position)}</h2>\n{body}"
