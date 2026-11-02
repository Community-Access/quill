"""The words of each small app's first single AI request (codex.md Phase 3, 10E).

One function per request, wx-free, so the prompt a person's words go out in is
testable without a window and written once:

* **Quill Weather, Should I Go Out?** (6.9, decision 22): plain words over the
  forecast text, never a radar or a map. An alert is never paraphrased by a
  model: the prompt forbids it, and the app puts each alert's own words in
  front of the answer (:func:`alerts_preface`).
* **Quill Converter, Will This Play on My Device?** (10E.7): the model reasons
  over probe text, never over the audio.
* **Quill Inkwell, Suggest Abbreviations** (6.12): entries proposed from a
  document the person picked; each is added only on a yes, and nothing typed
  anywhere else is ever read (:func:`parse_suggestions` is strict about shape).
* **QuillBeacon, Describe a Saved Picture** (10B.5): what this computer's OCR
  read goes with the picture, so the description can lean on it.

Quill Media Player's two recaps keep their own words
(:func:`quill.core.media.recap.recap_prompt`).

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

__all__ = [
    "INKWELL_DOCUMENT_CHARS",
    "TEXT_ONLY",
    "alerts_preface",
    "beacon_picture_question",
    "go_out_prompt",
    "inkwell_suggest_prompt",
    "parse_suggestions",
    "will_play_prompt",
]

#: Every request here ends with the family's text-only rule (decision 13).
TEXT_ONLY = "Answer in sentences or a short list. Never draw a chart, a table or a diagram."

#: The most of a picked document Suggest Abbreviations sends.
INKWELL_DOCUMENT_CHARS = 12000


# -- Weather ------------------------------------------------------------------ #


def go_out_prompt(facts: str) -> str:
    """Should I go out? over the facts block ``weather_context`` made."""
    return (
        "Should I go out? Using only the weather below, answer in plain words in three "
        "or four sentences: whether the next few hours are a good time to be outside, "
        "what to wear or bring, and the best time if one is better than now. Do not "
        "reword, summarise or play down any weather alert: if there is one, say only "
        "that an alert is active and should be read as the Weather Service wrote it. "
        f"{TEXT_ONLY}\n\n{facts.strip()}"
    )


def alerts_preface(alerts: Iterable[tuple[str, str]]) -> str:
    """Each active alert in the Weather Service's own words, before any answer.

    *alerts* are ``(event, headline)`` pairs. "" when there are none.
    """
    lines = [
        f"{event.strip()}" + (f": {headline.strip()}" if headline.strip() else "")
        for event, headline in alerts
        if event.strip()
    ]
    if not lines:
        return ""
    noun = "alert" if len(lines) == 1 else "alerts"
    return f"Active {noun}, as the Weather Service wrote it: " + "; ".join(lines) + "."


# -- Converter ---------------------------------------------------------------- #


def will_play_prompt(facts: str, device: str = "") -> str:
    """Will these files play on *device* (or on the usual devices when blank)?"""
    device = device.strip()
    target = (
        f"on this device: {device}"
        if device
        else "on a phone, on a car stereo from a USB stick, and on a smart speaker"
    )
    return (
        f"Will these files play {target}? Answer from the file details below only. "
        "For each kind of file, say yes or no and why in one sentence, and when the "
        "answer is no, name the format and settings in Quill Converter's Convert to "
        f"list that would play. {TEXT_ONLY}\n\n{facts.strip()}"
    )


# -- Inkwell ------------------------------------------------------------------ #


def inkwell_suggest_prompt(document: str, existing: Sequence[str], *, limit: int = 10) -> str:
    """Propose up to *limit* abbreviations for phrases *document* repeats."""
    text = document.strip()
    if len(text) > INKWELL_DOCUMENT_CHARS:
        text = text[:INKWELL_DOCUMENT_CHARS].rstrip()
    taken = ", ".join(sorted({a.strip() for a in existing if a.strip()}, key=str.lower))
    avoid = f" These abbreviations already exist, so do not reuse them: {taken}." if taken else ""
    return (
        f"Suggest up to {limit} text-expansion abbreviations for long words or phrases "
        "this document repeats, so they can be typed faster. Each abbreviation is two to "
        "six lower-case letters or digits, is not an ordinary English word, and "
        f"expands to the exact phrase from the document.{avoid} Write one per line, "
        "exactly as: abbreviation -> expansion. Write nothing else.\n\n"
        f"Document:\n{text}"
    )


_SUGGESTION = re.compile(r"^\s*(?:[-*\d.)]+\s*)?`?([A-Za-z0-9]{2,12})`?\s*(?:->|=>|:)\s*(.+?)\s*$")


def parse_suggestions(answer: str, existing: Iterable[str] = ()) -> list[tuple[str, str]]:
    """``(abbreviation, expansion)`` pairs from *answer*; anything else is dropped.

    An abbreviation that already exists, repeats, or expands to itself is left
    out, so nothing proposed can overwrite an entry the person made.
    """
    taken = {a.strip().lower() for a in existing}
    found: list[tuple[str, str]] = []
    for line in answer.splitlines():
        match = _SUGGESTION.match(line)
        if match is None:
            continue
        abbreviation = match.group(1).lower()
        expansion = match.group(2).strip().strip('"').strip()
        if not expansion or abbreviation in taken or expansion.lower() == abbreviation:
            continue
        taken.add(abbreviation)
        found.append((abbreviation, expansion))
    return found


# -- Beacon ------------------------------------------------------------------- #


def beacon_picture_question(ocr_text: str = "") -> str:
    """What Describe a Saved Picture asks, with the words OCR read on this computer."""
    question = (
        "Describe this saved picture in a few sentences: what it shows, any words in it, "
        f"and what it seems to be for. {TEXT_ONLY}"
    )
    read = ocr_text.strip()
    if read:
        question += (
            "\n\nText this computer already read from the picture (it may have errors):\n"
            + read[:4000]
        )
    return question
