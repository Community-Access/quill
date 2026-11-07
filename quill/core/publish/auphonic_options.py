"""Quill Converter's Auphonic options beyond the MVP: custom processing, metadata,
cover art, chapter marks, a second output format, and a transcript.

The post-MVP half of Process with Auphonic
(``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``, section 14).
The MVP sent a preset as it is or Quick cleanup's three switches, one format,
and whatever tags the source file carried. This module adds, in the order the
PRD's section 8 lists the later work:

* **Custom processing** -- a loudness target, a true-peak limit, leveling and
  filtering on or off, and noise reduction with a strength and a method
  (speech isolation among them). The words a person reads are plain ("Podcast
  loudness, -16 LUFS"); the numbers go only into the request.
* **Metadata and cover art** -- an artist and an album that replace the
  source's own, edited chapter marks for a single production, and a JPEG or
  PNG cover uploaded with each production.
* **More results** -- one more output format beside the first, and a
  transcript with captions made by Auphonic's own speech recognition.

Everything here is pure: no network, no wx. The JSON field names come from
Auphonic's published API pages; they were written against recorded fakes, not
a live account, and section 14 of the PRD lists them for a live check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.publish.auphonic import OUTPUT_FORMATS

#: Loudness targets offered, in LUFS, with the words a person reads.
LOUDNESS_TARGETS: tuple[tuple[int, str], ...] = (
    (-16, "Podcast loudness, -16 LUFS (the usual choice)"),
    (-14, "Music streaming loudness, -14 LUFS"),
    (-18, "Quieter podcast, -18 LUFS"),
    (-19, "Mono podcast, -19 LUFS"),
    (-20, "Audiobook loudness, -20 LUFS"),
    (-23, "European broadcast, -23 LUFS"),
    (-24, "American broadcast, -24 LUFS"),
)
#: True-peak ceilings offered, in dBTP.
PEAK_LIMITS: tuple[tuple[float, str], ...] = (
    (-1.0, "Peaks no louder than -1 dB (the usual choice)"),
    (-2.0, "Peaks no louder than -2 dB, safer for MP3 and AAC"),
    (-3.0, "Peaks no louder than -3 dB, for audiobook stores"),
)
#: Noise reduction strengths, in dB; 0 lets Auphonic decide; -1 is off.
NOISE_OFF = -1
NOISE_AMOUNTS: tuple[tuple[int, str], ...] = (
    (NOISE_OFF, "Off"),
    (0, "Automatic: Auphonic decides how much"),
    (6, "Light"),
    (12, "Medium"),
    (18, "Strong"),
    (100, "As much as possible"),
)
#: Noise reduction methods, by Auphonic's name.
NOISE_METHODS: tuple[tuple[str, str], ...] = (
    ("", "Auphonic's usual method"),
    ("static", "Steady noise only, such as hum and hiss"),
    ("dynamic", "Changing noise too, such as traffic and voices"),
    ("speech_isolation", "Keep only the speech, removing everything else"),
)
#: Transcript languages offered, by Auphonic's language code.
TRANSCRIPT_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("de", "German"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("it", "Italian"),
    ("nl", "Dutch"),
    ("pt", "Portuguese"),
)
#: The result files a transcript adds: captions and a plain-text transcript.
TRANSCRIPT_OUTPUTS: tuple[dict[str, str], ...] = (
    {"format": "subtitle", "ending": "srt"},
    {"format": "transcript", "ending": "txt"},
)
#: Cover images Auphonic takes, and the largest Quill Converter will send.
COVER_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})
COVER_MAX_BYTES = 10 * 1024 * 1024
#: The upload form field a cover image travels in.
COVER_FIELD = "image"


@dataclass(frozen=True, slots=True)
class CustomProcessing:
    """Custom processing's choices, every one a value from the tables above."""

    leveler: bool = True
    filtering: bool = True
    loudness: int = -16
    max_peak: float = -1.0
    noise: int = NOISE_OFF
    noise_method: str = ""

    def algorithms(self, *, multitrack: bool) -> tuple[dict[str, object], dict[str, object]]:
        """``(production, per_track)`` algorithm settings.

        A multitrack production levels and normalizes the mix and filters and
        denoises each track, the split Quick cleanup already uses.
        """
        master: dict[str, object] = {
            "leveler": self.leveler,
            "normloudness": True,
            "loudnesstarget": self.loudness,
            "maxpeak": self.max_peak,
        }
        track: dict[str, object] = {"filtering": self.filtering, "denoise": self.noise != NOISE_OFF}
        if self.noise != NOISE_OFF:
            track["denoiseamount"] = self.noise
            if self.noise_method:
                track["denoisemethod"] = self.noise_method
        if multitrack:
            return master, track
        return {**track, **master}, {}

    def describe(self) -> str:
        """The custom choices in one plain sentence, for the confirmation."""
        loud = _label(LOUDNESS_TARGETS, self.loudness, f"{self.loudness} LUFS")
        peak = _label(PEAK_LIMITS, self.max_peak, f"{self.max_peak:g} dB")
        parts = [
            "filtering on" if self.filtering else "filtering off",
            "even levels" if self.leveler else "levels left as they are",
            loud.split(" (")[0],
            peak.split(" (")[0].replace("Peaks", "peaks"),
        ]
        if self.noise == NOISE_OFF:
            parts.append("no noise reduction")
        else:
            amount = _label(NOISE_AMOUNTS, self.noise, str(self.noise)).split(":")[0]
            method = _label(NOISE_METHODS, self.noise_method, self.noise_method)
            parts.append(f"noise reduction {amount.lower()}, {method[0].lower()}{method[1:]}")
        return "Custom processing, which replaces the preset's own: " + ", ".join(parts)

    def problem(self) -> str:
        """Why these values cannot be sent; ``""`` when they can."""
        if self.loudness not in {value for value, _l in LOUDNESS_TARGETS}:
            return "Choose a loudness target from the list."
        if self.max_peak not in {value for value, _l in PEAK_LIMITS}:
            return "Choose a peak limit from the list."
        if self.noise not in {value for value, _l in NOISE_AMOUNTS}:
            return "Choose a noise reduction strength from the list."
        if self.noise_method not in {value for value, _l in NOISE_METHODS}:
            return "Choose a noise reduction method from the list."
        return ""


def _label(table: tuple[tuple[object, str], ...], value: object, fallback: str) -> str:
    return next((label for key, label in table if key == value), fallback)


# -- chapter marks ------------------------------------------------------------------


_CHAPTER_LINE = re.compile(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)\s+(.+?)\s*$")


def format_chapters(chapters: tuple[tuple[float, str], ...]) -> str:
    """One ``H:MM:SS Title`` line per chapter, the form :func:`parse_chapters` reads."""
    lines = []
    for start, title in chapters:
        whole = int(max(0.0, start))
        hours, rest = divmod(whole, 3600)
        minutes, seconds = divmod(rest, 60)
        lines.append(f"{hours}:{minutes:02d}:{seconds:02d} {title}")
    return "\n".join(lines)


def parse_chapters(text: str) -> tuple[tuple[tuple[float, str], ...], str]:
    """``(chapters, problem)``: one ``H:MM:SS Title`` or ``MM:SS Title`` per line.

    Blank lines are skipped. A line that cannot be read, or a start earlier
    than the line before it, is the problem, named by its line number.
    """
    chapters: list[tuple[float, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = _CHAPTER_LINE.match(line)
        if match is None:
            return (), (
                f"Chapter line {number} needs a start time and a title, such as 0:05:30 Interview."
            )
        hours, minutes, seconds, title = match.groups()
        start = int(hours or 0) * 3600 + int(minutes) * 60 + float(seconds)
        if (hours is not None and int(minutes) > 59) or float(seconds) >= 60:
            return (), f"Chapter line {number} has a time that cannot be right."
        if chapters and start < chapters[-1][0]:
            return (), f"Chapter line {number} starts before the chapter above it."
        chapters.append((start, title))
    return tuple(chapters), ""


# -- cover art ------------------------------------------------------------------------


def cover_problem(cover: str) -> str:
    """Why *cover* cannot be sent as cover art; ``""`` when it can (or there is none)."""
    if not cover:
        return ""
    path = Path(cover)
    if path.suffix.lower() not in COVER_EXTENSIONS:
        return "The cover image must be a JPEG or PNG file."
    try:
        size = path.stat().st_size
    except OSError:
        return f"The cover image {path.name} is no longer there."
    if size == 0:
        return f"The cover image {path.name} is empty."
    if size > COVER_MAX_BYTES:
        return f"The cover image {path.name} is larger than 10 MB; choose a smaller one."
    return ""


# -- the request ------------------------------------------------------------------------


def outputs(primary: str, second: str, transcript: bool) -> list[dict[str, str]]:
    """The ``output_files`` list: the chosen format, the second one, and the transcript's."""
    files: list[dict[str, str]] = []
    for name in (primary, second):
        if name and {"format": name} not in files:
            files.append({"format": name})
    if transcript:
        files += [dict(item) for item in TRANSCRIPT_OUTPUTS]
    return files


def speech_recognition(language: str) -> dict[str, str]:
    """The request's speech-recognition block: Auphonic's own, in *language*."""
    return {"type": "auphonic", "language": language or "en"}


def extras_problem(
    *,
    output_format: str,
    second_format: str,
    transcript: bool,
    language: str,
    cover: str,
    chapters_edited: bool,
    productions: int,
) -> str:
    """Why the extra choices cannot be sent, in words; ``""`` when they can."""
    if (second_format or transcript) and not output_format:
        return (
            "A second format or a transcript needs an output format chosen too, because "
            "asking for extra files replaces the preset's own outputs."
        )
    if second_format and second_format not in OUTPUT_FORMATS:
        return "Choose the second format from the list."
    if second_format and second_format == output_format:
        return "The second format is the same as the first; choose a different one or none."
    if transcript and language not in {code for code, _l in TRANSCRIPT_LANGUAGES}:
        return "Choose the transcript's language from the list."
    if chapters_edited and productions > 1:
        return (
            "Edited chapter marks belong to one production, and this sends "
            f"{productions}. Send one file, or clear the chapter marks."
        )
    return cover_problem(cover)


def language_label(code: str) -> str:
    return _label(TRANSCRIPT_LANGUAGES, code, code)
