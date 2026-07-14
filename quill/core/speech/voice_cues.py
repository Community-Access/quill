"""Spoken cue phrases for voice conversation mode (Hey QUILL refinement).

Pure, wx-free: generate the short, warm, varied spoken lines a hands-free
session uses — the welcome, the "go ahead" listening prompt, the acknowledgement
while working, and the follow-up nudge — personalized with an optional name and
aware of the time of day, exactly like the ADP Assistant's spoken personality
(app.js `welcomeText` / `followupText` / `searchAck`).

Kept deterministic-friendly for tests: pass a ``pick`` callable (defaults to
``random.choice``) and a ``now`` callable (defaults to ``datetime.now``) so the
chosen line and the greeting are both controllable. :func:`cue_pool` returns the
whole set worth pre-synthesizing so the UI can warm a TTS cache and have cues
play instantly.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

PickFn = Callable[[Sequence[str]], str]
NowFn = Callable[[], datetime]


def _default_pick(options: Sequence[str]) -> str:
    import random

    return random.choice(list(options))


def _time_of_day(now: NowFn) -> str:
    hour = now().hour
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


def _name(user_name: str) -> str:
    cleaned = (user_name or "").strip()
    return cleaned or "there"


def welcome(
    user_name: str = "",
    *,
    first: bool = True,
    pick: PickFn = _default_pick,
    now: NowFn = datetime.now,
) -> str:
    """The greeting when conversation mode starts (or re-arms after a lull)."""
    name = _name(user_name)
    if first:
        options = [
            f"Good {_time_of_day(now)}, {name}. What can I do?",
            f"Hi {name}. Ready when you are - what would you like?",
            f"Hey {name}. Conversation mode is on. Say a command.",
        ]
    else:
        options = [f"Yes, {name}?", f"I'm listening, {name}.", f"Go ahead, {name}.", "Mm-hm?"]
    return pick(options)


def listening(user_name: str = "", *, pick: PickFn = _default_pick) -> str:
    """The short "the mic is open" prompt."""
    name = _name(user_name)
    return pick([f"Listening, {name}.", "Go ahead.", "I'm listening.", f"Yes, {name}?"])


def acknowledge(user_name: str = "", *, pick: PickFn = _default_pick) -> str:
    """A brief acknowledgement while a command runs."""
    name = _name(user_name)
    return pick([f"On it, {name}.", "One moment.", "Doing that now.", "Got it."])


def followup(user_name: str = "", *, pick: PickFn = _default_pick) -> str:
    """The nudge that keeps a multi-turn thread going after an action."""
    name = _name(user_name)
    return pick([f"Anything else, {name}?", "What else?", "Anything more?", "Next command?"])


def cue_pool(user_name: str = "", *, now: NowFn = datetime.now) -> tuple[str, ...]:
    """Every cue worth pre-synthesizing, so a TTS cache can warm them once."""
    name = _name(user_name)
    return (
        f"Good {_time_of_day(now)}, {name}. What can I do?",
        f"Hi {name}. Ready when you are - what would you like?",
        f"Hey {name}. Conversation mode is on. Say a command.",
        f"Yes, {name}?",
        f"I'm listening, {name}.",
        f"Go ahead, {name}.",
        "Mm-hm?",
        f"On it, {name}.",
        "One moment.",
        f"Anything else, {name}?",
        "What else?",
    )


__all__ = ["acknowledge", "cue_pool", "followup", "listening", "welcome"]
