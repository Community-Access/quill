"""The prompts every app's Ask offers, and each app's quick prompts (codex.md 10D.2, 10E).

Data, not behaviour: the UI lists these in the Ask window's quick list beside
an app's existing ones (Radio's eight stay where they are,
:mod:`quill.core.radio.assistant_prompt`). The basic prompts of 10D.1 are not
here and are not touched.

A prompt declares what it **needs** (``pictures``, ``tools``), and the gating
rule labels it from :func:`quill.core.ai.connection_caps.needs_label`, so
"Describe the chart in this picture" reads "(needs a connection that sees)" on
the free AI. One shared prompt is answered on this computer:
"What can I do here?" comes from the app's own F1 catalogue
(:func:`what_can_i_do_here`), never from a model's guess about the app.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from quill.core.ai.connection_caps import AGENT_TOOLS, PICTURES, needs_label
from quill.core.control_help import compose_control_body

__all__ = [
    "APP_QUICK_PROMPTS",
    "FAMILY_APPS",
    "FAMILY_PROMPTS",
    "NEED_CAPABILITY",
    "NEED_PICTURES",
    "NEED_TOOLS",
    "QuickPrompt",
    "labelled",
    "quick_prompts_for",
    "what_can_i_do_here",
]

NEED_PICTURES = "pictures"
NEED_TOOLS = "tools"
#: A prompt's ``needs`` word -> the capability the connection must have.
NEED_CAPABILITY: dict[str, str] = {NEED_PICTURES: PICTURES, NEED_TOOLS: AGENT_TOOLS}

FAMILY_APPS: tuple[str, ...] = (
    "quill",
    "lite",
    "radio",
    "cast",
    "studio",
    "transcribe",
    "converter",
    "player",
    "weather",
    "inkwell",
    "beacon",
)


@dataclass(frozen=True, slots=True)
class QuickPrompt:
    """One prompt in an Ask quick list."""

    id: str
    label: str
    #: What is sent. ``{context}`` is the app's facts block; ``{selection}``
    #: and ``{document}`` are filled where the app has them.
    text: str
    needs: tuple[str, ...] = ()
    #: Answered on this computer; nothing is sent.
    local: bool = False


FAMILY_PROMPTS: tuple[QuickPrompt, ...] = (
    QuickPrompt(
        "family-explain-simply",
        "Explain this simply",
        "Explain this in plain words, as you would to someone new to it. Keep it short.\n\n"
        "{context}",
    ),
    QuickPrompt(
        "family-what-can-i-do",
        "What can I do here?",
        "",
        local=True,
    ),
    QuickPrompt(
        "family-summarise",
        "Summarise what is in front of me",
        "Summarise what is in front of me in three or four sentences, most important first.\n\n"
        "{context}",
    ),
)

APP_QUICK_PROMPTS: dict[str, tuple[QuickPrompt, ...]] = {
    "radio": (
        QuickPrompt(
            "radio-next", "What is on next?", "What is on next on this station?\n\n{context}"
        ),
        QuickPrompt(
            "radio-record-whenever",
            "Record this whenever it is on",
            "This programme is on now. When is it usually broadcast, so I can record it "
            "whenever it is on? Suggest times; I will set the recording myself.\n\n{context}",
        ),
    ),
    "cast": (
        QuickPrompt(
            "cast-missed",
            "What did I miss in this episode?",
            "What did I miss in this episode before where I am now?\n\n{context}",
        ),
        QuickPrompt(
            "cast-worth-it",
            "Is this episode worth my time?",
            "From the show notes, is this episode worth my time? Say who it suits and why, "
            "in a few sentences.\n\n{context}",
        ),
    ),
    "studio": (
        QuickPrompt(
            "studio-setup-ready", "Is my setup ready?", "Is my recording setup ready?\n\n{context}"
        ),
        QuickPrompt(
            "studio-recording-right",
            "Does this recording look right?",
            "The recording check ran on this computer. Does this recording look right, and "
            "what should I fix first?\n\n{context}",
        ),
    ),
    "transcribe": (
        QuickPrompt(
            "transcribe-who-said",
            "Who said what?",
            "Go through the transcript and say, speaker by speaker, what each one said.\n\n"
            "{context}",
        ),
        QuickPrompt(
            "transcribe-decided",
            "What was decided?",
            "List what was decided in this transcript, one decision per line.\n\n{context}",
        ),
    ),
    "converter": (
        QuickPrompt(
            "converter-will-play",
            "Will this play on my device?",
            "Will these files play on my device? Name the device if I have said it; "
            "otherwise answer for a phone, a car stereo and a smart speaker.\n\n{context}",
        ),
        QuickPrompt(
            "converter-in-my-car",
            "Will this play in my car?",
            "Will these files play on a typical car stereo from a USB stick?\n\n{context}",
        ),
        QuickPrompt(
            "converter-smaller",
            "Make this smaller without losing much",
            "Which settings would make these files smaller without losing much quality? "
            "Name the format and bit rate.\n\n{context}",
        ),
    ),
    "player": (
        QuickPrompt(
            "player-who-is",
            "Remind me who this character is",
            "Remind me who this character is, using only what the book has said up to where "
            "I am. No spoilers past my place.\n\n{context}",
        ),
    ),
    "weather": (
        QuickPrompt(
            "weather-coat-at-5",
            "Do I need a coat at 5?",
            "Do I need a coat at 5 this evening?\n\n{context}",
        ),
        QuickPrompt(
            "weather-rain-when",
            "When is the rain coming?",
            "When is the rain coming, and how long will it last?\n\n{context}",
        ),
    ),
    "inkwell": (
        QuickPrompt(
            "inkwell-type-most",
            "What do I type most?",
            "From these abbreviations and how often each is used, what do I type most, and "
            "is there a pattern worth another abbreviation?\n\n{context}",
        ),
    ),
    "beacon": (
        QuickPrompt(
            "beacon-saved-about",
            "What did I save about this?",
            "What did I save about this? Answer only from the notes below.\n\n{context}",
        ),
    ),
}


def quick_prompts_for(app: str) -> tuple[QuickPrompt, ...]:
    """The family prompts, then *app*'s own, in the order the list shows them."""
    return FAMILY_PROMPTS + APP_QUICK_PROMPTS.get(app, ())


def labelled(label: str, needs: Iterable[str], capabilities: Iterable[str]) -> str:
    """*label* with "(needs ...)" when the connection in use lacks something it needs.

    *capabilities* are what the connection can do now (connection_caps names).
    """
    have = set(capabilities)
    for need in needs:
        capability = NEED_CAPABILITY.get(need, need)
        if capability not in have:
            return f"{label} {needs_label(capability)}"
    return label


def what_can_i_do_here(
    purpose: str,
    *,
    accessible_name: str = "",
    help_text: str = "",
    usage: str = "",
    commands: Sequence[tuple[str, str]] = (),
    limit: int = 12,
) -> str:
    """The local answer to "What can I do here?", from the app's own F1 catalogue.

    *purpose* is the window's authored purpose; the control fields are what
    F1 already says about the focused control; *commands* are ``(label,
    chord)`` pairs from the app's menus. Nothing here is sent anywhere.
    """
    parts = [purpose.strip()] if purpose.strip() else []
    control = compose_control_body(
        accessible_name=accessible_name, help_text=help_text, usage=usage
    ).strip()
    if accessible_name or help_text or usage:
        parts.append(control)
    rows = [f"- {label}, {chord}" if chord else f"- {label}" for label, chord in commands[:limit]]
    if rows:
        parts.append("Things you can do from here:\n" + "\n".join(rows))
    if not parts:
        parts.append(control)
    return "\n\n".join(parts)
