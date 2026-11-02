"""Speakers, Sections and Summary: QUILL Transcribe's agent task (codex.md 6.6).

The person presses Ctrl+F3 (AI > Speakers, Sections and Summary...) and an
agent engine -- My GitHub Copilot or Codex -- reads the transcript as text,
names the speakers from what they say, adds section headings, and writes a
summary and an action list. Speech to text stays on this computer, or with the
speech provider the person chose: the model only ever sees words.

* ``transcribe.read_transcript`` -- a read, so it runs without a question: the
  words in Review Dictation when it is open, else the transcript last reviewed,
  else this session's dictated phrases; with the speaker labels a diarized
  transcript carries ("Speaker 1 [00:01:05]: ...").
* ``transcribe.write_sections`` -- a write: the whole new text is shown first
  (decision 13), and only an Apply puts it in Review Dictation, as one change
  its Undo Change takes back. A closed review opens on the transcript first,
  so Undo Change returns to the words as they were.

Handlers run on a worker thread; every touch of the window goes through
``ctx.on_ui``. Nothing here announces: the agent window says each step and the
closing summary once (GATE-13).
"""

from __future__ import annotations

import re
from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "INSTRUCTION_HELP",
    "SPEAKERS_AND_SECTIONS",
    "STARTER",
    "TranscribeAiFeaturesMixin",
    "speaker_labels",
    "transcribe_task_facts",
    "transcribe_task_tools",
]

APP = "transcribe"
#: What Review Dictation's list of changes calls this one.
CHANGE_LABEL = "Speakers, sections and summary"
#: The most of a transcript one read hands the model.
_READ_LIMIT = 120_000

SPEAKERS_AND_SECTIONS = AppTaskSpec(
    app=APP,
    agent_id="transcribe-speakers-sections",
    title="Speakers, Sections and Summary",
    instructions=(
        "You help someone who uses a screen reader with QUILL Transcribe, which "
        "turns speech into text on their computer. Read the transcript with "
        "transcribe_read_transcript. Then write it back once with "
        "transcribe_write_sections: the whole transcript, with each speaker named "
        "where the words make the name clear (keep labels like Speaker 1 where "
        "they do not, and never invent a name), short section headings where the "
        "subject changes, then a Summary section of a few sentences and an "
        "Actions section listing who does what by when, as a plain list. Keep "
        "every spoken word; change only names, headings and those two sections. "
        "Use plain text with headings as lines that start with #."
    ),
    done_words={f"{APP}.write_sections": "Wrote speakers, sections and a summary"},
)

STARTER = (
    "Name the speakers, add section headings, and finish with a summary and a list of actions."
)

INSTRUCTION_HELP = (
    "Say what you want done with the transcript, then press Enter; the words "
    "already here name the speakers, add headings, a summary and an action list. "
    "Only text goes to your AI, never your voice. The new text is shown to you in "
    "full before it goes into Review Dictation. While a task runs, what you type "
    "here goes to it as a follow-up."
)

# "Speaker 1 [00:01:05]: words" or "Speaker 1: words" (diarization.format_diarization),
# and the same with a name the person gave a speaker.
_TIMED_LABEL = re.compile(r"^(?P<label>[^\n:\[\]]{1,40}?) \[\d{2}:\d{2}:\d{2}\]: ", re.MULTILINE)
_PLAIN_LABEL = re.compile(r"^(?P<label>Speaker \d+|SPEAKER_\d+): ", re.MULTILINE)


def speaker_labels(text: str) -> list[str]:
    """The diarization speaker labels in *text*, in the order they first speak."""
    found: list[tuple[int, str]] = [
        (match.start(), match.group("label").strip())
        for pattern in (_TIMED_LABEL, _PLAIN_LABEL)
        for match in pattern.finditer(text)
    ]
    seen: list[str] = []
    for _at, label in sorted(found):
        if label and label not in seen:
            seen.append(label)
    return seen


def _review_frame(host: Any) -> Any:
    """Review Dictation's window when it is open with its words, else None."""
    desk = getattr(host, "_review", None)
    frame = getattr(desk, "frame", None) if desk is not None else None
    if frame and getattr(frame, "conversation", None) is not None:
        return frame
    return None


def current_transcript(host: Any) -> tuple[str, str]:
    """``(where it is from, the words)``: the open review, the transcript, or phrases."""
    frame = _review_frame(host)
    if frame is not None:
        return "the words in Review Dictation", str(frame.conversation.session.current)
    title, text = getattr(host, "_last_transcript", None) or ("", "")
    if str(text).strip():
        return f"the transcript {title}" if title else "the transcript", str(text)
    controller = getattr(host, "_dictation", None)
    phrases = list(getattr(controller, "recent", []) or []) if controller else []
    words = "\n".join(reversed([str(p) for p in phrases]))
    return ("this session's dictation", words) if words.strip() else ("", "")


def transcribe_task_facts(host: Any) -> str:
    """What is on hand, as text, sent with the first instruction."""
    where, text = current_transcript(host)
    if not text.strip():
        return "There is no transcript or dictation here yet."
    words = len(text.split())
    lines = [f"Transcript: {where}, {words} word{'s' if words != 1 else ''}."]
    labels = speaker_labels(text)
    if labels:
        lines.append("Speaker labels in it: " + ", ".join(labels) + ".")
    else:
        lines.append("It has no speaker labels.")
    return "\n".join(lines)


def transcribe_task_tools(host: Any, ctx: AppTaskHost) -> list[FamilyTool]:
    """QUILL Transcribe's tools for one task."""
    read_now: dict[str, str] = {}

    def read_transcript(_args: dict[str, Any]) -> str:
        where, text = ctx.on_ui(lambda: current_transcript(host), ("", "")) or ("", "")
        if not str(text).strip():
            raise ToolError(
                "There is no transcript here yet. Transcribe a recording, open one from "
                "Notifications, or dictate, then ask again."
            )
        read_now["text"] = text
        labels = speaker_labels(text)
        head = [f"From {where}."]
        head.append(
            "Speaker labels from diarization: " + ", ".join(labels) + "."
            if labels
            else "There are no speaker labels; tell speakers apart from what they say."
        )
        body = text
        if len(body) > _READ_LIMIT:
            body = body[:_READ_LIMIT].rstrip()
            head.append(f"Only the first {_READ_LIMIT} characters are given here.")
        return "\n".join([*head, "", body])

    def write_sections(args: dict[str, Any]) -> str:
        text = str(args.get("text", "") or "").strip()
        if not text:
            raise ToolError("Give the whole new text to write.")
        if not ctx.preview(f"{CHANGE_LABEL}, for Review Dictation", text):
            raise ToolError("The person did not apply it.")

        def put() -> str:
            frame = _review_frame(host)
            if frame is None:
                from quill.core.windows_dictation.review_session import load_rescue

                if load_rescue(host._review_rescue_path()) is not None:
                    return "kept"
                source = read_now.get("text") or current_transcript(host)[1]
                host._review_desk().open(source)
                frame = _review_frame(host)
                if frame is None:
                    return "closed"
            frame.conversation.apply(CHANGE_LABEL, text)
            return ""

        problem = ctx.on_ui(put, "stopped")
        if problem == "kept":
            raise ToolError(
                "Review Dictation is holding words kept from last time, so nothing was "
                "written. Open Review Dictation, insert or discard those words, then ask again."
            )
        if problem:
            raise ToolError("Review Dictation could not be opened, so nothing was written.")
        return (
            "Written into Review Dictation as one change; Undo Change there puts the "
            "words back as they were."
        )

    return [
        FamilyTool(
            name=f"{APP}.read_transcript",
            description=(
                "Read the transcript as text: the words in Review Dictation, the "
                "transcript last reviewed, or this session's dictation, with any "
                "speaker labels."
            ),
            handler=read_transcript,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.write_sections",
            description=(
                "Write the whole transcript back, with speakers named, section "
                "headings, a summary and an action list. The person sees it in full "
                "and chooses Apply first; it goes into Review Dictation as one change."
            ),
            handler=write_sections,
            parameters=_schema(
                {"text": {"type": "string", "description": "The whole new text."}}, ("text",)
            ),
            category=PermissionCategory.MODIFY_DOCUMENT,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=lambda _a: (
                "Write the transcript with speakers named, section headings, a summary "
                "and an action list into Review Dictation."
            ),
        ),
    ]


class TranscribeAiFeaturesMixin:
    """QUILL Transcribe's AI commands. Mixed in through ``TranscribeAiMixin``."""

    def cmd_ai_task(self) -> None:
        """Speakers, Sections and Summary (Ctrl+F3, codex.md 6.6): the transcript as
        text to an agent engine, and its speakers, headings, summary and actions back
        into Review Dictation after you have read them and chosen Apply."""
        self._open_app_task(  # type: ignore[attr-defined]
            SPEAKERS_AND_SECTIONS,
            lambda ctx: transcribe_task_tools(self, ctx),
            instruction_help=INSTRUCTION_HELP,
            starter=STARTER,
            context=lambda: transcribe_task_facts(self),
        )
