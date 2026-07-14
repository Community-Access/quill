"""Configurable text cleanup/normalization for TTS (batch-document-to-speech §4.9).

wx-free, strict-typed. Real-world documents are full of typography that makes TTS
engines stumble — curly quotes, em/en dashes, ellipses, invisible spaces, soft
hyphens, ligatures, bullets, symbols, fractions, emoji, control characters — and
of structured tokens (phone numbers, emails, URLs) that must be spoken clearly.
``normalize_for_tts`` cleans the text deterministically before synthesis, with
excellent defaults and rich per-pass options, and is the first stage of the
shared live + batch pipeline (so the same clean voice is heard everywhere).

Pauses are represented as plain comma/period approximations here (works on every
engine); exact SSML ``<break>`` rendering is the plan's Phase 6.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, fields
from typing import Any

# --- static maps ----------------------------------------------------------- #

_LIGATURES = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",
    "ﬆ": "st",
}
_FRACTIONS = {
    "½": "one half",
    "⅓": "one third",
    "⅔": "two thirds",
    "¼": "one quarter",
    "¾": "three quarters",
    "⅕": "one fifth",
    "⅛": "one eighth",
}
_SYMBOLS = {
    "©": " copyright ",
    "®": " registered ",
    "™": " trademark ",
    "°": " degrees ",
    "×": " times ",
    "÷": " divided by ",
    "§": " section ",
    "¶": " paragraph ",
    "†": " dagger ",
    "‡": " double dagger ",
    "%": " percent ",
    "&": " and ",
    "=": " equals ",
    "≤": " less than or equal to ",
    "≥": " greater than or equal to ",
    "≠": " not equal to ",
    "±": " plus or minus ",
    "≈": " approximately ",
    "∞": " infinity ",
    "→": " to ",
    "•": " ",
    "◦": " ",
    "▪": " ",
    "‣": " ",
    "⁃": " ",
    "●": " ",
    "○": " ",
    "■": " ",
    "▶": " ",
    "★": " ",
    "☆": " ",
    "✓": " check ",
    "✗": " x ",
}
_CURRENCY = [
    (re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)"), r"\1 dollars"),
    (re.compile(r"€\s?(\d[\d,]*(?:\.\d+)?)"), r"\1 euros"),
    (re.compile(r"£\s?(\d[\d,]*(?:\.\d+)?)"), r"\1 pounds"),
    (re.compile(r"¥\s?(\d[\d,]*(?:\.\d+)?)"), r"\1 yen"),
]
_BULLET_LINE = re.compile(r"^[ \t]*[•◦▪‣⁃●○■▶\-\*]+[ \t]+")
_INVISIBLE_REMOVE = re.compile(r"[​‌‍­﻿⁠‎‏‪-‮]")
_EXOTIC_SPACE = re.compile(r"[  -   　]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_EMOJI = re.compile("[\U0001f000-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff←-⇿⬀-⯿]")
_EM_DASH = re.compile(r"\s*—\s*")
_EN_DASH = re.compile(r"(?<=\w)–(?=\w)")
_RANGE = re.compile(r"(\w+)\s*–\s*(\w+)")
_ELLIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")
_REPEAT_PUNCT = re.compile(r"([!?])\1{1,}")
_RULE_LINE = re.compile(r"(?m)^[ \t]*([-*=_])\1{2,}[ \t]*$")
_CITATION = re.compile(r"\[\d+\]")
_ALL_CAPS = re.compile(r"\b[A-Z]{2,5}\b")
_PHONE = re.compile(
    r"(?<!\w)(\+?\d{1,3}[ .-]?)?(\(?\d{3}\)?[ .-]?)?\d{3}[ .-]\d{4}(?:\s?(?:x|ext\.?)\s?\d+)?(?!\w)"
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>()]+", re.IGNORECASE)
_ACRONYMS_THAT_ARE_WORDS = {"NASA", "RADAR", "LASER", "SCUBA", "NATO", "PIN", "ZIP"}


@dataclass(slots=True)
class TextNormalizationOptions:
    """Per-pass configuration with the recommended defaults (§4.9.2/§4.9.3)."""

    quotes: bool = True
    dashes: bool = True
    dash_mode: str = "comma_pause"  # comma_pause | hyphen | spoken | remove
    smart_ranges: bool = True
    ellipsis: bool = True
    invisibles: bool = True
    ligatures: bool = True
    bullets: bool = True
    symbols: str = "speak"  # speak | strip | keep
    fractions: bool = True
    emoji: str = "strip"  # strip | keep
    repeated_punctuation: bool = True
    control_chars: bool = True
    nfkc: bool = False
    # Publication shorthand and resolution numbers (from the ACB pipeline): say
    # "Vol." as "Volume", "No." as "Number", and "2025-02" as "2025 dash 2".
    publications: bool = True
    resolution_numbers: bool = True
    # magical opt-in
    phone_numbers: bool = False
    citations: bool = False
    acronyms: bool = False
    # emails / urls (§4.9.7)
    addresses: bool = True
    address_mode: str = "speak_then_repeat"  # announce | speak | speak_then_repeat
    address_long_url_threshold: int = 60
    # escape hatch (applied last)
    extra_replacements: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in fields(self):
            out[f.name] = getattr(self, f.name)
        return out

    @classmethod
    def from_dict(cls, data: Any) -> TextNormalizationOptions:
        opts = cls()
        if not isinstance(data, dict):
            return opts
        for f in fields(cls):
            if f.name not in data:
                continue
            raw = data[f.name]
            current = getattr(opts, f.name)
            if isinstance(current, bool):
                setattr(opts, f.name, bool(raw))
            elif isinstance(current, int):
                try:
                    setattr(opts, f.name, int(raw))
                except (TypeError, ValueError):
                    pass
            elif isinstance(current, str):
                setattr(opts, f.name, str(raw))
            elif isinstance(current, dict) and isinstance(raw, dict):
                setattr(opts, f.name, {str(k): str(v) for k, v in raw.items()})
        return opts


# Publication shorthand and resolution numbers (ACB pipeline learnings).
_VOL = re.compile(r"\bVol\.\s*(\d+)")
_NO = re.compile(r"\bNo\.\s*(\d+)")
# A 4-digit year, a dash, then 1-3 digits (e.g. resolution "2025-02"). The number's
# leading zero is dropped so it speaks as "2025 dash 2", not "2025 dash zero two".
_RESOLUTION = re.compile(r"\b(20\d{2})-(\d{1,3})\b")


def _resolution_repl(match: re.Match[str]) -> str:
    return f"{match.group(1)} dash {int(match.group(2))}"


# --- structured-token passes (run first; claim their punctuation) ---------- #


def _speak_digits(digits: str) -> str:
    """Speak a run of digits grouped in threes with pauses ('five five five, …')."""
    names = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
    }
    spoken = [names.get(ch, ch) for ch in digits if ch.isdigit()]
    return " ".join(spoken)


def _normalize_phone(match: re.Match[str]) -> str:
    raw = match.group(0)
    groups = re.findall(r"\d+", raw)
    spoken = ", ".join(_speak_digits(g) for g in groups)
    return f" {spoken} "


def _spell_address(token: str) -> str:
    """Turn an email/URL into a spoken form: punctuation → words, paced by commas."""
    words = {
        "@": " at ",
        ".": " dot ",
        "/": " slash ",
        ":": " colon ",
        "-": " dash ",
        "_": " underscore ",
        "~": " tilde ",
        "?": " question mark ",
        "&": " and ",
        "=": " equals ",
        "#": " hash ",
        "+": " plus ",
    }
    out: list[str] = []
    for ch in token:
        out.append(words.get(ch, ch))
    spoken = "".join(out)
    spoken = re.sub(r"\s{2,}", " ", spoken).strip()
    return spoken


def _normalize_address(token: str, opts: TextNormalizationOptions) -> str:
    if opts.address_mode == "announce":
        return " email address " if "@" in token else " link "
    if len(token) > max(0, opts.address_long_url_threshold) and "@" not in token:
        return " link "
    spoken = _spell_address(token)
    if opts.address_mode == "speak_then_repeat":
        # say it, pause, repeat, then a trailing pause (comma/period approximations).
        return f" {spoken}, {spoken}. "
    return f" {spoken}. "


# --- main ------------------------------------------------------------------ #


def normalize_for_tts(text: str, options: TextNormalizationOptions | None = None) -> str:
    """Clean ``text`` for speech per ``options`` (defaults when omitted)."""
    if not text:
        return text
    opts = options if options is not None else TextNormalizationOptions()
    result = text

    if opts.nfkc:
        result = unicodedata.normalize("NFKC", result)

    # Structured tokens first, so their . - / @ are claimed before generic passes.
    if opts.phone_numbers:
        result = _PHONE.sub(_normalize_phone, result)
    if opts.addresses:
        result = _EMAIL.sub(lambda m: _normalize_address(m.group(0), opts), result)
        result = _URL.sub(lambda m: _normalize_address(m.group(0), opts), result)

    if opts.invisibles:
        result = _INVISIBLE_REMOVE.sub("", result)
        result = _EXOTIC_SPACE.sub(" ", result)
    if opts.control_chars:
        result = _CONTROL.sub("", result)
    if opts.quotes:
        result = result.translate({
            0x201C: '"',
            0x201D: '"',
            0x201E: '"',
            0x2018: "'",
            0x2019: "'",
            0x201A: "'",
            0x02BC: "'",
            0x2032: "'",
            0x00B4: "'",
            0x0060: "'",
        })
    if opts.ligatures:
        for src, dst in _LIGATURES.items():
            result = result.replace(src, dst)
    if opts.dashes:
        if opts.smart_ranges:
            result = _RANGE.sub(r"\1 to \2", result)
        result = _EN_DASH.sub("-", result)
        if opts.dash_mode == "comma_pause":
            result = _EM_DASH.sub(", ", result)
        elif opts.dash_mode == "hyphen":
            result = _EM_DASH.sub(" - ", result)
        elif opts.dash_mode == "spoken":
            result = _EM_DASH.sub(" em dash ", result)
        else:  # remove
            result = _EM_DASH.sub(" ", result)
    if opts.ellipsis:
        result = _ELLIPSIS.sub(", ", result)
    if opts.fractions:
        for src, dst in _FRACTIONS.items():
            result = result.replace(src, f" {dst} ")
    if opts.symbols == "speak":
        for pattern, word in _CURRENCY:
            result = pattern.sub(word, result)
        result = result.translate({ord(k): v for k, v in _SYMBOLS.items()})
    elif opts.symbols == "strip":
        result = result.translate({ord(k): " " for k in _SYMBOLS})
    if opts.bullets:
        result = "\n".join(_BULLET_LINE.sub("", line) for line in result.split("\n"))
    if opts.emoji == "strip":
        result = _EMOJI.sub("", result)
    if opts.repeated_punctuation:
        result = _REPEAT_PUNCT.sub(r"\1", result)
        result = _RULE_LINE.sub("", result)
    if opts.citations:
        result = _CITATION.sub("", result)
    if opts.acronyms:
        result = _ALL_CAPS.sub(_spell_acronym, result)
    if opts.publications:
        result = _VOL.sub(r"Volume \1", result)
        result = _NO.sub(r"Number \1", result)
    if opts.resolution_numbers:
        result = _RESOLUTION.sub(_resolution_repl, result)

    for src, dst in opts.extra_replacements.items():
        if src:
            result = result.replace(src, dst)

    # Tidy whitespace the passes may have introduced.
    result = "\n".join(re.sub(r"[ \t]{2,}", " ", line).strip() for line in result.split("\n"))
    return result


def _spell_acronym(match: re.Match[str]) -> str:
    token = match.group(0)
    if token in _ACRONYMS_THAT_ARE_WORDS:
        return token
    return " ".join(token)
