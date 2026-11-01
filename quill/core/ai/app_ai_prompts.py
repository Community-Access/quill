"""Each app's first single-request feature, as a prompt built from local data (codex.md 10E).

Pure builders: the app gathers what it already has, these turn it into the one
request, and the connection layer sends it (with the family's text-only line,
:mod:`quill.core.ai.text_only`). Where something can be answered on this
computer, it is, first: Studio's verdict comes from the pre-flight rules,
Inkwell's candidates from a local count, a saved screenshot's words from OCR.

Every builder goes through :func:`quill.core.ai.app_ask_context.filter_facts`,
so nothing on the never-without-a-yes list (10C.3) gets into a prompt here.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.core.ai.app_ask_context import (
    beacon_context,
    cast_context,
    converter_context,
    facts_text,
    filter_facts,
    scrub,
    studio_context,
    weather_context,
)

if TYPE_CHECKING:
    from quill.core.audio.media_probe import MediaInfo
    from quill.core.demo_recording import Finding
    from quill.core.weather.models import WeatherReport

__all__ = [
    "AbbreviationIdea",
    "abbreviation_prompt",
    "beacon_describe_prompt",
    "beacon_summarise_prompt",
    "cast_missed_prompt",
    "player_recap_prompt",
    "setup_ready_local",
    "setup_ready_prompt",
    "should_i_go_out_prompt",
    "suggest_abbreviations",
    "transcript_action_items_prompt",
    "transcript_summary_prompt",
    "will_it_play_prompt",
]


def _with(instruction: str, facts: str) -> str:
    return f"{instruction}\n\n{facts}".strip() if facts else instruction


# -- Weather: "Should I go out?" (10E.9, decision 22) --------------------------- #


def should_i_go_out_prompt(report: WeatherReport, *, when: str = "", plans: str = "") -> str:
    """From the text forecast only. An active alert is never reworded by the model."""
    asked = "Should I go out"
    asked += f" {when.strip()}" if when.strip() else " in the next few hours"
    asked += f" to {plans.strip()}?" if plans.strip() else "?"
    instruction = (
        f"{asked} Answer yes, no or it depends in the first sentence, then say why in at most "
        "three short sentences: what to wear or bring, and the best time to go. Use only the "
        "forecast below. If an alert is listed, do not restate, summarise or reword it; say "
        "only that there is an active alert and that QUILL Weather reads it in full."
    )
    return _with(instruction, facts_text(filter_facts(weather_context(report))))


# -- Converter: "Will this play on my device?" (10E.7) -------------------------- #


def will_it_play_prompt(files: Sequence[MediaInfo], *, device: str = "") -> str:
    """From the probe text: formats, codecs, sizes. The model never hears the audio."""
    target = device.strip() or "a phone, a car stereo and a smart speaker"
    instruction = (
        f"Will these files play on {target}? For each device say yes, no or probably, and "
        "why, from the container, codec, sample rate and channels below. When one will not "
        "play, name the format to convert it to."
    )
    return _with(instruction, facts_text(filter_facts(converter_context(files))))


# -- Inkwell: suggest abbreviations (10E.10, 6.12) ----------------------------- #

_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
_COMMON = frozenset(
    "a an the and or but of to in on at for with by is it as be are was this that i you we "
    "they he she my our your their from not have has had do".split()
)


@dataclass(frozen=True, slots=True)
class AbbreviationIdea:
    """A phrase typed often enough to earn an abbreviation, counted on this computer."""

    phrase: str
    count: int
    abbreviation: str

    @property
    def saving(self) -> int:
        """Characters saved across the document."""
        return self.count * (len(self.phrase) - len(self.abbreviation))


def _initials(words: Sequence[str]) -> str:
    if len(words) == 1:
        word = words[0].lower()
        consonants = word[0] + "".join(c for c in word[1:] if c not in "aeiou'-")
        return consonants[:4]
    return "".join(w[0] for w in words).lower()


def suggest_abbreviations(
    text: str,
    *,
    existing: Iterable[tuple[str, str]] = (),
    limit: int = 10,
    min_count: int = 3,
    max_words: int = 5,
) -> list[AbbreviationIdea]:
    """Phrases of two to five words, or long single words, that recur in *text*.

    *existing* is ``(abbreviation, expansion)`` pairs already in the library:
    their expansions are not suggested again and their abbreviations are not
    reused. Nothing is sent: this is the local half of the feature.
    """
    taken = {a.lower() for a, _e in existing}
    known = {" ".join(e.lower().split()) for _a, e in existing}
    words = _WORD.findall(text)
    lowered = [w.lower() for w in words]
    counts: Counter[str] = Counter()
    for size in range(2, max_words + 1):
        for start in range(len(lowered) - size + 1):
            gram = lowered[start : start + size]
            if gram[0] in _COMMON or gram[-1] in _COMMON:
                continue
            counts[" ".join(gram)] += 1
    for word in lowered:
        if len(word) >= 10:
            counts[word] += 1
    ideas: list[AbbreviationIdea] = []
    for phrase, count in counts.items():
        if count < min_count or phrase in known:
            continue
        abbreviation = _initials(phrase.split())
        if len(abbreviation) < 2 or abbreviation in _COMMON:
            continue
        ideas.append(AbbreviationIdea(phrase, count, abbreviation))
    ideas.sort(key=lambda i: (-i.saving, i.phrase))
    chosen: list[AbbreviationIdea] = []
    for idea in ideas:
        if any(idea.phrase in c.phrase for c in chosen):
            continue  # a shorter piece of a phrase already chosen
        abbreviation = idea.abbreviation
        suffix = 2
        while abbreviation in taken:
            abbreviation = f"{idea.abbreviation}{suffix}"
            suffix += 1
        taken.add(abbreviation)
        chosen.append(AbbreviationIdea(idea.phrase, idea.count, abbreviation))
        if len(chosen) >= limit:
            break
    return chosen


def abbreviation_prompt(ideas: Sequence[AbbreviationIdea]) -> str:
    """Only the candidate phrases and counts go, never the document they came from."""
    rows = "\n".join(
        f"{i.phrase} (typed {i.count} times; proposed {i.abbreviation})" for i in ideas
    )
    instruction = (
        "These phrases recur in a document I wrote. For each, suggest a short abbreviation "
        "that is easy to remember and is not a real word I would type by accident, or say to "
        "skip it. One line each: phrase, abbreviation, a few words why."
    )
    return _with(instruction, f"Phrases:\n{scrub(rows)}" if rows else "")


# -- Player: chapter recap (10E.8) --------------------------------------------- #


def player_recap_prompt(
    kind: str, *, book: str = "", chapter_title: str = "", transcript: str = ""
) -> str:
    """``chapter`` or ``recap`` (welcome back), from the local transcript of at
    most five minutes, through the media recap's own wording."""
    from quill.core.media.recap import recap_prompt

    head = "\n".join(
        line
        for line in (
            f"Book: {book}" if book else "",
            f"Chapter: {chapter_title}" if chapter_title else "",
        )
        if line
    )
    body = (
        f"{head}\n\nTranscript of the last minutes:\n{transcript.strip()}" if head else transcript
    )
    return recap_prompt(kind, body)


# -- Beacon: describe and summarise (10E.11) ----------------------------------- #


def beacon_summarise_prompt(title: str, text: str, *, tags: Sequence[str] = ()) -> str:
    instruction = (
        "Summarise this saved note in three sentences, most important first, then list any "
        "dates, names or numbers in it."
    )
    facts = beacon_context(note_title=title, note_text=text, tags=tags)
    return _with(instruction, facts_text(filter_facts(facts)))


def beacon_describe_prompt(title: str, *, ocr_text: str = "") -> str:
    """For a saved screenshot sent as a picture: OCR's words go beside it, so the
    model describes what OCR could not read rather than repeating it."""
    instruction = (
        "Describe this saved screenshot for someone who cannot see it: what kind of screen "
        "it is, what it shows, and anything that needs attention. Keep it to a short "
        "paragraph."
    )
    lines = [f"Saved as: {scrub(title)}"] if title else []
    if ocr_text.strip():
        lines.append("Words already read on this computer:\n" + scrub(ocr_text.strip())[:4000])
    return _with(instruction, "\n".join(lines))


# -- Studio: "Is my setup ready?" (10E.5) -------------------------------------- #


def setup_ready_local(findings: Sequence[Finding]) -> str:
    """The pre-flight rules' own verdict, said before any model is asked."""
    stops = [f for f in findings if f.severity == "Stop"]
    warns = [f for f in findings if f.severity != "Stop"]
    if stops:
        n = len(stops)
        things = "1 thing stops" if n == 1 else f"{n} things stop"
        return f"Not ready: {things} the recording."
    if warns:
        n = len(warns)
        return f"Ready, with {n} thing{'' if n == 1 else 's'} worth a look."
    return "Ready to record."


def setup_ready_prompt(
    *,
    plan_summary: str,
    findings: Sequence[Finding] = (),
    capture: dict[str, str] | None = None,
) -> str:
    instruction = (
        f"{setup_ready_local(findings)} Is my recording setup ready? Explain each problem "
        "below in plain words and say what to do about it, most serious first. Do not invent "
        "problems that are not listed."
    )
    facts = studio_context(plan_summary=plan_summary, findings=findings, capture=capture)
    return _with(instruction, facts_text(filter_facts(facts)))


# -- Cast: "What did I miss?" (10E.4) ------------------------------------------ #


def cast_missed_prompt(
    show: str,
    episode: str,
    *,
    notes: str = "",
    chapters: Sequence[tuple[str, float]] = (),
    position_s: float | None = None,
    transcript: str = "",
) -> str:
    """From the show notes, chapters and the cached transcript; never the audio."""
    instruction = (
        "What did I miss in this episode before where I am now? Cover only what comes "
        "before my position, in a few sentences, and say which chapter I am in."
    )
    facts = facts_text(
        filter_facts(
            cast_context(show, episode, notes=notes, chapters=chapters, position_s=position_s)
        )
    )
    if transcript.strip():
        facts += "\n\nTranscript so far:\n" + transcript.strip()[-8000:]
    return _with(instruction, facts)


# -- Transcribe: summary and action items (10E.6) ------------------------------ #


def _transcript_prompt(action_id: str, transcript: str, extra: str) -> str:
    from quill.core.ai.transcript_actions import find_action

    action = find_action(action_id)
    if action is None:  # pragma: no cover - the ids are the builtins'
        raise KeyError(action_id)
    return action.build_prompt(transcript, extra_instruction=extra)


def transcript_summary_prompt(transcript: str, *, extra: str = "") -> str:
    """The existing Executive Summary action, unchanged (10D.1)."""
    return _transcript_prompt("executive-summary", transcript, extra)


def transcript_action_items_prompt(transcript: str, *, extra: str = "") -> str:
    """The existing Action Items action, unchanged (10D.1)."""
    return _transcript_prompt("action-items", transcript, extra)
