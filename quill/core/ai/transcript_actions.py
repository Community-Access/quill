"""Transcript Actions — what QUILL can make of a finished transcript.

The Listening Companion's first magic: after audio is transcribed, QUILL offers a
small, context-aware set of *actions* that turn the raw transcript into a finished,
structured document — Meeting Minutes, Action Items, Study Notes, a clean draft, and
more. Each action is a named, plain-language instruction (ported and adapted from
BITS Whisperer's AI Action presets) plus a prompt builder, so running one is a single
provider call whose result opens as a new document.

This module is wx-free and fully unit-testable. The UI presents
:func:`recommend_actions` (ordered for the current transcript) and runs the chosen
action's :meth:`TranscriptAction.build_prompt`. The same actions seed the guided
Action Builder and the bundled Transcript Skills (later phases), so there is one
source of truth for "what QUILL can make of this."
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "TranscriptAction",
    "BUILTIN_TRANSCRIPT_ACTIONS",
    "all_actions",
    "find_action",
    "recommend_actions",
    "transcript_has_speakers",
    "action_to_skill_source",
    "generate_action_text",
    "run_action_by_id",
]


def generate_action_text(
    action: TranscriptAction, transcript: str, backend: object
) -> tuple[str | None, str | None]:
    """Run one action over the transcript via ``backend``. Returns (text, error).

    ``backend`` is anything with a ``respond(prompt) -> str`` method (e.g.
    :class:`~quill.core.ai.provider_backend.ProviderChatBackend`). Errors are
    returned, never raised, so callers (UI dialog, watch worker) stay alive.
    """
    try:
        text = backend.respond(action.build_prompt(transcript))  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 - surface a clean message, never crash
        return None, str(exc)
    return (text or ""), None


def run_action_by_id(
    transcript: str, action_id: str, backend: object
) -> tuple[str | None, str | None]:
    """Find an action by id and run it over the transcript. Returns (text, error)."""
    action = find_action(action_id)
    if action is None:
        return None, f"Unknown transcript action: {action_id!r}."
    return generate_action_text(action, transcript, backend)


def action_to_skill_source(
    name: str, instruction: str, *, description: str = "", reference_text: str = ""
) -> str:
    """Wrap a plain-language action as a saved one-step ``.sqp`` skill source.

    This is what the guided Action Builder saves: a user's own action becomes a
    runnable, shareable, Promotable Skill that applies its instruction to the open
    document. The body frames the document as a transcript and carries the
    ``{document}`` placeholder the skill runner fills at run time, so the saved action
    works on whatever the user is looking at — a transcript they just made, or any text.

    ``reference_text`` is an optional grounding document (an agenda, a house style, a
    prior good example) baked into the action so its output matches *your* template —
    "make minutes that look like last month's". It is included as a reference block the
    model is told to follow.
    """
    from quill.core.ai.library import prompt_to_skill_source

    parts = [instruction.strip()]
    ref = reference_text.strip()
    if ref:
        parts.append(
            "Use the following reference as the template/example to match in style, "
            "structure, and terminology:\n\nREFERENCE:\n" + ref
        )
    parts.append("TRANSCRIPT:\n{document}")
    body = "\n\n".join(parts)
    return prompt_to_skill_source(name, body, description=description)


@dataclass(frozen=True, slots=True)
class TranscriptAction:
    """One thing QUILL can make of a transcript: a name + plain-language instruction."""

    id: str
    name: str
    description: str
    instruction: str

    def build_prompt(self, transcript: str, *, extra_instruction: str = "") -> str:
        """Assemble the full provider prompt for this action over ``transcript``.

        ``extra_instruction`` is the user's own plain-language adjustment ("focus on
        the budget decisions", "keep it under one page"), appended so the same action
        is adjustable without editing the builtin.
        """
        guidance = self.instruction.strip()
        extra = extra_instruction.strip()
        if extra:
            guidance = f"{guidance}\n\nAdditional instructions from the user:\n{extra}"
        return f"{guidance}\n\nTRANSCRIPT:\n{transcript.strip()}\n"


BUILTIN_TRANSCRIPT_ACTIONS: tuple[TranscriptAction, ...] = (
    TranscriptAction(
        id="meeting-minutes",
        name="Meeting Minutes",
        description="Structured minutes: attendees, decisions, action items, follow-ups.",
        instruction=(
            "You are a professional meeting minutes writer. Given the transcript below, "
            "produce well-structured meeting minutes that include:\n"
            "- Date/time and attendees (if identifiable)\n"
            "- Agenda items discussed\n"
            "- Key decisions made\n"
            "- Action items with owners and deadlines (if mentioned)\n"
            "- Follow-up items\n\n"
            "Use clear headings, bullet points, and concise language suitable for sharing "
            "with team members who were not present."
        ),
    ),
    TranscriptAction(
        id="action-items",
        name="Action Items",
        description="Every task, commitment, and follow-up as an actionable list.",
        instruction=(
            "You are a task extraction specialist. Analyze this transcript and extract "
            "every action item, task, commitment, follow-up, and to-do mentioned. For "
            "each item include:\n"
            "- What needs to be done\n"
            "- Who is responsible (if mentioned)\n"
            "- Deadline or timeline (if mentioned)\n"
            "- Priority level (high/medium/low, inferred from context)\n\n"
            "Present them as a numbered, actionable list."
        ),
    ),
    TranscriptAction(
        id="executive-summary",
        name="Executive Summary",
        description="A concise briefing for senior leadership.",
        instruction=(
            "You are an executive briefing specialist. Produce a concise executive "
            "summary of this transcript suitable for senior leadership. Include:\n"
            "- One-paragraph overview (3-4 sentences)\n"
            "- Key takeaways (bullet points)\n"
            "- Strategic implications or concerns\n"
            "- Recommended next steps\n\n"
            "Keep the tone professional and focus on what matters most."
        ),
    ),
    TranscriptAction(
        id="interview-notes",
        name="Interview Notes",
        description="Questions, responses, strengths, concerns, and an assessment.",
        instruction=(
            "You are an interview analysis expert. Create detailed interview notes from "
            "this transcript, including:\n"
            "- Candidate/interviewee information\n"
            "- Key questions asked and responses\n"
            "- Notable strengths and areas of concern\n"
            "- Relevant quotes\n"
            "- Overall assessment and recommendation\n\n"
            "Maintain objectivity and support observations with evidence from the "
            "transcript."
        ),
    ),
    TranscriptAction(
        id="study-notes",
        name="Study Notes",
        description="Lecture or talk turned into organized study notes.",
        instruction=(
            "You are a study notes specialist. Transform this lecture/presentation "
            "transcript into well-organized study notes that include:\n"
            "- Main topics and subtopics with clear headings\n"
            "- Key concepts and definitions\n"
            "- Important examples and explanations\n"
            "- Formulas, processes, or frameworks mentioned\n"
            "- Questions raised and any answers given\n"
            "- Summary of key takeaways\n\n"
            "Use bullet points, numbered lists, and formatting for easy review."
        ),
    ),
    TranscriptAction(
        id="qa-extraction",
        name="Q&A Extraction",
        description="Every question and its answer in clean Q&A format.",
        instruction=(
            "You are a Q&A extraction specialist. Identify every question asked in this "
            "transcript and its corresponding answer. Present them as a clean Q&A "
            "format:\n\n"
            "Q: [question]\n"
            "A: [answer]\n\n"
            "If a question was not answered, note it as 'Unanswered'. Include the speaker "
            "name if identifiable."
        ),
    ),
    TranscriptAction(
        id="clean-draft",
        name="Clean Up & Draft",
        description="Turn spoken rambling into a clean, readable written draft.",
        instruction=(
            "You are a careful editor. Turn this spoken transcript into a clean, readable "
            "written draft:\n"
            "- Remove filler words, false starts, and repetition\n"
            "- Fix grammar and punctuation\n"
            "- Organize into clear paragraphs, with headings where the content naturally "
            "divides\n"
            "- Preserve the speaker's meaning, voice, and all substantive content\n\n"
            "Do not add information, opinions, or facts that are not present in the "
            "transcript."
        ),
    ),
    TranscriptAction(
        id="follow-up-email",
        name="Follow-Up Email",
        description="A ready-to-send email recapping the discussion and next steps.",
        instruction=(
            "You are an assistant drafting a follow-up email after this conversation. "
            "Write a warm, concise, ready-to-send email that includes:\n"
            "- A one-line thank-you / opener\n"
            "- A short recap of what was discussed and decided\n"
            "- A clear list of next steps with owners (if mentioned)\n"
            "- A friendly closing line\n\n"
            "Keep it professional and brief. Use only what is in the transcript; mark "
            "anything you are unsure of as a placeholder in [brackets]."
        ),
    ),
    TranscriptAction(
        id="key-quotes",
        name="Key Quotes",
        description="The most notable verbatim quotes, with who said them.",
        instruction=(
            "You are a careful editor pulling the most notable, quotable lines from this "
            "transcript. List 5-10 verbatim quotes that best capture the key points, "
            "decisions, or memorable moments. For each, give the exact words in quotation "
            "marks and the speaker's name if identifiable. Do not paraphrase or invent "
            "quotes — use the transcript's exact wording."
        ),
    ),
    TranscriptAction(
        id="decisions-log",
        name="Decisions Log",
        description="Just the decisions made, each with its rationale and owner.",
        instruction=(
            "You are a decision tracker. From this transcript, list every decision that "
            "was actually made (not just discussed). For each decision include:\n"
            "- The decision, stated clearly\n"
            "- The reason or rationale given (if any)\n"
            "- Who made or owns it (if identifiable)\n\n"
            "Present them as a numbered list. If no firm decisions were made, say so "
            "plainly."
        ),
    ),
)


def all_actions() -> tuple[TranscriptAction, ...]:
    """Every builtin transcript action, in their canonical order."""
    return BUILTIN_TRANSCRIPT_ACTIONS


def find_action(action_id: str) -> TranscriptAction | None:
    """The action with this id, or ``None``."""
    target = action_id.strip().lower()
    return next((a for a in BUILTIN_TRANSCRIPT_ACTIONS if a.id == target), None)


# A diarized transcript labels each turn like "Speaker 0:", "Alex:", "[Speaker 1]".
# Capture the whole label (including its number/name) so distinct speakers count as
# distinct — "Speaker 0" and "Speaker 1" are two speakers, not one "speaker".
_SPEAKER_LINE = re.compile(r"^[ \t]*(\[?[A-Za-z][\w .'\-]{0,30}\]?)\s*:", re.MULTILINE)


def transcript_has_speakers(transcript: str) -> bool:
    """True when the transcript looks diarized (>=2 distinct speaker labels)."""
    labels = {m.group(1).strip().lower() for m in _SPEAKER_LINE.finditer(transcript)}
    return len(labels) >= 2


def recommend_actions(
    transcript: str, *, has_speakers: bool | None = None, limit: int | None = None
) -> list[TranscriptAction]:
    """Return the builtin actions ordered by relevance to this transcript.

    Every action stays available (the user is never boxed in); the order just puts the
    most useful first for *this* recording — multi-speaker audio leads with Minutes and
    Action Items, question-dense audio with Q&A and Interview Notes, and a single voice
    with Clean Up & Draft. ``has_speakers`` overrides the heuristic when the caller
    already knows (e.g. diarization was on).
    """
    if has_speakers is None:
        has_speakers = transcript_has_speakers(transcript)
    questions = transcript.count("?")
    words = max(1, len(transcript.split()))
    question_dense = questions >= 3 and (questions / words) > 0.01

    if has_speakers and question_dense:
        lead = ["interview-notes", "key-quotes", "qa-extraction", "meeting-minutes"]
    elif has_speakers:
        lead = ["meeting-minutes", "action-items", "decisions-log", "follow-up-email"]
    elif question_dense:
        lead = ["qa-extraction", "study-notes", "key-quotes", "clean-draft"]
    else:
        lead = ["clean-draft", "study-notes", "executive-summary"]

    order = {action_id: i for i, action_id in enumerate(lead)}
    ranked = sorted(
        BUILTIN_TRANSCRIPT_ACTIONS,
        key=lambda a: (order.get(a.id, len(lead) + BUILTIN_TRANSCRIPT_ACTIONS.index(a)),),
    )
    return ranked if limit is None else ranked[:limit]
