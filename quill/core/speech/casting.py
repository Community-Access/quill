"""Voice casting: explicit per-section voice assignment for narration runs.

Round-robin rotation voices sections blindly (section *i* gets voice *i mod
N*). Casting makes the assignment explicit: an ordered list of rules, each a
pattern matched against the section's number or heading title, naming the
voice that reads every matching section. The first matching rule wins;
unmatched sections fall through to the rotation (or the single voice), so
casting layers on top of the existing behavior instead of replacing it.

Patterns, matched case-insensitively:

- ``#N`` — exactly section number *N* (1-based), e.g. ``#1`` for the opener.
- anything else — an ``fnmatch`` glob against the section's heading title,
  e.g. ``Chapter *``, ``*interview*``, or an exact title.

wx-free, strict-typed, pure (the synthesizer wiring lives in
``document_speech``).
"""

from __future__ import annotations

from fnmatch import fnmatchcase

#: One rule: (pattern, voice id). Ordered; first match wins.
CastingRule = tuple[str, str]


def normalize_rules(rules: list[CastingRule] | tuple[CastingRule, ...] | None) -> list[CastingRule]:
    """Drop empty patterns/voices and surrounding whitespace; keep order."""
    cleaned: list[CastingRule] = []
    for pattern, voice in rules or []:
        p, v = pattern.strip(), voice.strip()
        if p and v:
            cleaned.append((p, v))
    return cleaned


def voice_for_section(rules: list[CastingRule], number: int, title: str) -> str:
    """The cast voice for section *number* (1-based) titled *title*; '' = none."""
    folded = title.strip().casefold()
    for pattern, voice in rules:
        if pattern.startswith("#"):
            digits = pattern[1:].strip()
            if digits.isdigit() and int(digits) == number:
                return voice
            continue
        if fnmatchcase(folded, pattern.casefold()):
            return voice
    return ""


def cast_voices(rules: list[CastingRule]) -> list[str]:
    """The distinct voices the rules can assign, in first-use order."""
    seen: list[str] = []
    for _pattern, voice in rules:
        if voice not in seen:
            seen.append(voice)
    return seen
