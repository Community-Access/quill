"""The two profiles, every conversion in them, and what they may cost.

**What is varied.** A setting is varied only against the formats it can
change (``RELEVANT``): large print against Word and the tagged PDF, the
braille table, cells, lines and pages against BRF, the voice and speed
against MP3 and DAISY, and the settings that shape the HTML Scribe builds
everything from (mathematics, picture descriptions, language) against every
format. A run tests QUILL, not Scribe (scribe-test-plan.md): each setting is
there to prove QUILL sent it and collected what came back, never to grade it.

**Uploads.** Scribe fixes the HTML-shaping settings at upload, and a format
is made once per document, so each combination is its own upload. Settings
that change different formats share one upload (a 32-cell BRF and a
large-print PDF come from the same document), and a combination already
made for that source in that format is never made twice.

**Credit.** Scribe charges pages once per uploaded document; Jeff's company
credit is counted in documents. Which one a conversion uses is not certain,
so the plan says both: uploads (documents) and conversions (formats made),
with the pages the uploads come to.

wx-free, no network.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Any

from quill.core.scribe.model import FORMAT_IDS, format_label
from quill.tools.scribe_live.sources import CONVERTS, REFUSED_HERE, Found, Source

QUICK = "quick"
FULL = "full"
PROFILES = (QUICK, FULL)

#: What every upload sends before a variant's changes: Scribe's account
#: defaults on the day Pneuma made their corpus (their README), so outputs
#: compare with theirs, and Scribe's own email off (F8). Never the account's
#: current defaults, which would make two runs differ for no reason.
BASE_SETTINGS: dict[str, Any] = {
    "language": "",
    "tts_gender": "",
    "tts_rate": 1.0,
    "braille_translation_table": "en-us-g2.ctb",
    "braille_cells_per_line": 40,
    "braille_lines_per_page": 25,
    "braille_split_into_pages": True,
    "large_print": False,
    "add_image_descriptions": True,
    "math": False,
    "notify_when_complete": False,
}

_SHAPING = ("language", "math", "add_image_descriptions")
_BRAILLE = (
    "braille_translation_table",
    "braille_cells_per_line",
    "braille_lines_per_page",
    "braille_split_into_pages",
)
_VOICE = ("tts_gender", "tts_rate")
#: The settings that can change each format's output.
RELEVANT: dict[str, tuple[str, ...]] = {
    "html": _SHAPING,
    "offline_html": _SHAPING,
    "epub": _SHAPING,
    "mobi": _SHAPING,
    "docx": (*_SHAPING, "large_print"),
    "pdf": (*_SHAPING, "large_print"),
    "brf": (*_SHAPING, *_BRAILLE),
    "mp3": (*_SHAPING, *_VOICE),
    "daisy": (*_SHAPING, *_VOICE),
}
GENERAL = ("html", "offline_html", "epub", "mobi")
PRINT = ("docx", "pdf")
AUDIO = ("mp3", "daisy")

#: The grids of the full profile.
SHAPING_GRID: tuple[dict[str, Any], ...] = (
    {},
    {"math": True},
    {"add_image_descriptions": False},
    {"math": True, "add_image_descriptions": False},
)
PRINT_GRID: tuple[dict[str, Any], ...] = ({}, {"large_print": True})
BRAILLE_GRID: tuple[dict[str, Any], ...] = tuple(
    {
        "braille_translation_table": table,
        "braille_cells_per_line": cells,
        "braille_split_into_pages": split,
        "braille_lines_per_page": lines,
    }
    for table, cells, (split, lines) in itertools.product(
        ("en-us-g2.ctb", "en-ueb-g2.ctb"), (40, 32), ((True, 25), (True, 20), (False, 25))
    )
)
VOICE_GRID: tuple[dict[str, Any], ...] = tuple(
    {"tts_gender": gender, "tts_rate": rate}
    for gender, rate in itertools.product(("", "female", "male"), (1.0, 2.0))
)

#: Scribe allows 10 actions a minute; QUILL's family keeps to 8 (queue.py).
ACTIONS_PER_MINUTE = 8


def relevant_key(format_id: str, settings: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    """What makes this format's output differ: its relevant settings' values.
    Lines per page mean nothing when braille is not split into pages."""
    names = RELEVANT[format_id]
    if format_id == "brf" and not settings.get("braille_split_into_pages", True):
        names = tuple(n for n in names if n != "braille_lines_per_page")
    return tuple((name, settings.get(name, BASE_SETTINGS[name])) for name in names)


def label_for(format_id: str, settings: dict[str, Any]) -> str:
    """The file-name label for the relevant settings that differ from the base:
    ``"math-on-large-print"``, ``"brf-en-ueb-g2-32x20"``, ``"female-2x"``."""
    values = dict(relevant_key(format_id, settings))
    parts: list[str] = []
    if values.get("language"):
        parts.append(f"lang-{values['language']}")
    if values.get("math"):
        parts.append("math-on")
    if values.get("add_image_descriptions") is False:
        parts.append("no-descriptions")
    if values.get("large_print"):
        parts.append("large-print")
    if format_id == "brf" and any(values[n] != BASE_SETTINGS[n] for n in _BRAILLE if n in values):
        table = str(values["braille_translation_table"]).removesuffix(".ctb")
        cells = values["braille_cells_per_line"]
        if values["braille_split_into_pages"]:
            parts.append(f"brf-{table}-{cells}x{values['braille_lines_per_page']}")
        else:
            parts.append(f"brf-{table}-{cells}-no-pages")
    if format_id in AUDIO:
        if values.get("tts_gender"):
            parts.append(str(values["tts_gender"]))
        if float(values.get("tts_rate", 1.0)) != 1.0:
            parts.append(f"{float(values['tts_rate']):g}x")
    return "-".join(parts)


_SHORT = {"brf": "Braille", "mp3": "MP3 audio", "daisy": "DAISY", "offline_html": "offline page"}
_TABLES = {"en-us-g2": "US grade 2", "en-ueb-g2": "UEB grade 2", "en-ueb-g1": "UEB grade 1"}


def spoken_for(format_id: str, settings: dict[str, Any]) -> str:
    """The relevant settings that differ from the base, in words:
    ``"math on, UEB grade 2, 32 by 20"``, ``"female voice, double speed"``."""
    values = dict(relevant_key(format_id, settings))
    words: list[str] = []
    if values.get("language"):
        words.append({"es": "Spanish"}.get(str(values["language"]), str(values["language"])))
    if values.get("math"):
        words.append("math on")
    if values.get("add_image_descriptions") is False:
        words.append("no image descriptions")
    if values.get("large_print"):
        words.append("large print")
    if format_id == "brf" and any(values[n] != BASE_SETTINGS[n] for n in _BRAILLE if n in values):
        table = str(values["braille_translation_table"]).removesuffix(".ctb")
        text = f"{_TABLES.get(table, table)}, {values['braille_cells_per_line']} cells"
        if values["braille_split_into_pages"]:
            text += f" by {values['braille_lines_per_page']} lines"
        else:
            text += ", no page breaks"
        words.append(text)
    if format_id in AUDIO:
        if values.get("tts_gender"):
            words.append(f"{values['tts_gender']} voice")
        rate = float(values.get("tts_rate", 1.0))
        if rate != 1.0:
            words.append(
                {2.0: "double speed", 0.5: "half speed"}.get(rate, f"{rate:g} times speed")
            )
    return ", ".join(words)


@dataclass(frozen=True, slots=True)
class Conversion:
    format: str
    label: str  # "" for the base settings

    def file_stem(self, source_stem: str) -> str:
        return f"{source_stem}-{self.label}" if self.label else source_stem


@dataclass(slots=True)
class Upload:
    """One document sent to Scribe, and the formats asked of it."""

    source: Source
    settings: dict[str, Any]
    conversions: list[Conversion]
    run_id: str = ""
    name: str = ""  # unique in the run; the job's title

    @property
    def formats(self) -> list[str]:
        return [c.format for c in self.conversions]

    @property
    def costs(self) -> bool:
        return self.source.costs

    def describe(self) -> str:
        """The settings that differ from the base, in words, or ``"the base settings"``."""
        labels = sorted({c.label for c in self.conversions if c.label})
        return ", ".join(labels) if labels else "the base settings"

    def spoken(self) -> str:
        """``"all 9 formats"``, or each format with its settings in words."""
        if len(self.conversions) == len(FORMAT_IDS) and not any(c.label for c in self.conversions):
            return f"all {len(FORMAT_IDS)} formats"
        parts = []
        for c in self.conversions:
            words = spoken_for(c.format, self.settings)
            parts.append(f"{_SHORT.get(c.format, format_label(c.format))}"
                         + (f" with {words}" if words else ""))  # fmt: skip
        return "; ".join(parts)


@dataclass(slots=True)
class Plan:
    profile: str
    uploads: list[Upload] = field(default_factory=list)
    left_out: list[Upload] = field(default_factory=list)  # by the cap
    cap: int | None = None

    @property
    def costly(self) -> list[Upload]:
        return [u for u in self.uploads if u.costs]

    @property
    def upload_count(self) -> int:
        return len(self.costly)

    @property
    def conversion_count(self) -> int:
        return sum(len(u.conversions) for u in self.costly)

    @property
    def pages(self) -> int:
        return sum(u.source.pages for u in self.costly)

    @property
    def minimum_minutes(self) -> int:
        """Scribe's pace alone: every upload and every conversion is an action."""
        return math.ceil((self.upload_count + self.conversion_count) / ACTIONS_PER_MINUTE)

    def by_format(self) -> dict[str, int]:
        counts = dict.fromkeys(FORMAT_IDS, 0)
        for upload in self.costly:
            for conversion in upload.conversions:
                counts[conversion.format] += 1
        return counts


class _Builder:
    def __init__(self) -> None:
        self.uploads: list[Upload] = []
        self._made: set[tuple[str, str, tuple[tuple[str, Any], ...]]] = set()
        self._names: set[str] = set()
        self._serial = 0

    def add(
        self,
        source: Source,
        changes: dict[str, Any],
        formats: tuple[str, ...] | list[str],
        *,
        run_id: str = "",
        label: str | None = None,
    ) -> Upload | None:
        """Plan one upload; formats already made with the same relevant settings
        are dropped, and an upload left with none is not planned at all."""
        settings = {**BASE_SETTINGS, **changes}
        conversions: list[Conversion] = []
        for format_id in formats:
            key = (source.stem, format_id, relevant_key(format_id, settings))
            if key in self._made:
                continue
            self._made.add(key)
            text = label if label is not None else label_for(format_id, settings)
            conversions.append(Conversion(format_id, text))
        if not conversions:
            return None
        self._serial += 1
        name = source.stem
        if name in self._names:
            name = f"{source.stem}--{self._serial:04d}"
        self._names.add(name)
        upload = Upload(source, settings, conversions, run_id or f"u{self._serial:04d}", name)
        self.uploads.append(upload)
        return upload


#: The quick profile's extra checks: (source stem, settings, formats).
QUICK_EXTRAS: tuple[tuple[str, dict[str, Any], tuple[str, ...]], ...] = (
    ("q26-spanish", {}, ("html", "mp3")),
    ("q27-math", {}, ("html", "docx")),
    ("q24-long-report", {}, ("html",)),
    ("q03-page", {}, ("html",)),
    (
        "q01-structured",
        {
            "braille_translation_table": "en-ueb-g2.ctb",
            "braille_cells_per_line": 32,
            "braille_lines_per_page": 20,
        },
        ("brf",),
    ),
    ("q28-locked", {}, ("html",)),
    ("q29-web-page", {}, ("html",)),
    ("q30-not-a-pdf", {}, ("html",)),
)


def _core(builder: _Builder, found: Found) -> None:
    """The four core sources in all nine formats, then Pneuma's two variants
    under Pneuma's names (``-large-print``: large print and 32 cells for PDF,
    Word and BRF; ``-math-on``: mathematics for HTML, the offline page, Word
    and EPUB), so the replay tests read this run as they read their corpus."""
    core = found.core
    for index, source in enumerate(core):
        builder.add(source, {}, FORMAT_IDS, run_id=f"s{index + 1}")
    if core:
        builder.add(
            core[0],
            {"large_print": True, "braille_cells_per_line": 32},
            ("pdf", "docx", "brf"),
            run_id="v1",
            label="large-print",
        )
    if len(core) >= 4:
        builder.add(
            core[3],
            {"math": True},
            ("html", "offline_html", "docx", "epub"),
            run_id="v2",
            label="math-on",
        )


def _grid(builder: _Builder, source: Source, shaping: dict[str, Any], full_grid: bool) -> None:
    """One shaping combination: the general formats once, and the print,
    braille and voice grids packed side by side into as few uploads as they need."""
    slots: list[tuple[tuple[str, ...], tuple[dict[str, Any], ...]]] = [
        (GENERAL, ({},)),
        (PRINT, PRINT_GRID),
        (("brf",), BRAILLE_GRID if full_grid else ({},)),
        (AUDIO, VOICE_GRID if full_grid else ({},)),
    ]
    rounds = max(len(options) for _formats, options in slots)
    for index in range(rounds):
        changes = dict(shaping)
        formats: list[str] = []
        for slot_formats, options in slots:
            if index < len(options):
                changes.update(options[index])
                formats.extend(slot_formats)
        builder.add(source, changes, formats)


def build_plan(found: Found, profile: str, *, cap: int | None = None) -> Plan:
    """Every upload of *profile* in the order it runs, then trimmed to *cap*
    conversions (whole uploads only, in order)."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}")
    builder = _Builder()
    _core(builder, found)
    by_stem = {s.stem: s for s in found.all}
    if profile == QUICK:
        for stem, changes, formats in QUICK_EXTRAS:
            if stem in by_stem:
                builder.add(by_stem[stem], changes, formats)
    else:
        converting = [s for s in found.all if s.expect == CONVERTS]
        for source in converting:  # every source, every format, base settings first
            builder.add(source, {}, FORMAT_IDS)
        for source in converting:  # then what the HTML is built with
            shapings = list(SHAPING_GRID[1:])
            if source.stem == "q26-spanish":
                shapings.append({"language": "es"})
            for shaping in shapings:
                _grid(builder, source, shaping, full_grid=False)
        for source in converting:  # then the format-only settings
            _grid(builder, source, {}, full_grid=True)
        for source in found.all:
            if source.expect != CONVERTS:
                builder.add(source, {}, ("html",))
    plan = Plan(profile, builder.uploads, cap=cap)
    if cap is not None:
        _apply_cap(plan, cap)
    return plan


def _apply_cap(plan: Plan, cap: int) -> None:
    kept: list[Upload] = []
    used = 0
    for upload in plan.uploads:
        size = len(upload.conversions) if upload.costs else 0
        if used + size <= cap and not plan.left_out:
            kept.append(upload)
            used += size
        else:
            plan.left_out.append(upload)
    plan.uploads = kept


def _number(count: int, singular: str, plural: str = "") -> str:
    return f"{count:,} {singular if count == 1 else plural or singular + 's'}"


def plan_sentences(plan: Plan, found: Found) -> list[str]:
    """The plan, as plain sentences for a screen reader: totals first."""
    lines = [
        f"The {plan.profile} profile plans {_number(plan.upload_count, 'upload')} "
        f"and {_number(plan.conversion_count, 'conversion')}.",
        f"It costs {plan.upload_count:,} if Scribe charges for each uploaded document, "
        f"or {plan.conversion_count:,} if Scribe charges for each format made.",
        f"The uploads come to about {_number(plan.pages, 'page')}. Scribe counts pages once "
        "per upload, so extra formats of the same upload cost no more pages.",
        f"It takes at least {_duration(plan.minimum_minutes)} at Scribe's pace, and longer "
        "with audio and DAISY, which often take several minutes each.",
    ]
    refused = [u for u in plan.uploads if u.source.expect == REFUSED_HERE]
    if refused:
        lines.append(
            f"{_number(len(refused), 'document')} will be refused by QUILL before "
            "anything is sent, which costs nothing."
        )
    if plan.left_out:
        left = sum(len(u.conversions) for u in plan.left_out if u.costs)
        lines.append(
            f"The cap of {_number(plan.cap or 0, 'conversion')} leaves out "
            f"{_number(len(plan.left_out), 'upload')} and {_number(left, 'conversion')}."
        )
    counts = plan.by_format()
    lines.append(
        "Conversions by format: "
        + "; ".join(f"{format_label(f)}, {counts[f]:,}" for f in FORMAT_IDS)
        + "."
    )
    origins = sorted({u.source.stem for u in plan.uploads})
    pneumas = len([s for s in found.pneuma if s.stem in origins])
    lines.append(f"It uses {_number(len(origins), 'source document')}, {pneumas} of them Pneuma's.")
    lines.extend(found.notes)
    return lines


def _duration(minutes: int) -> str:
    if minutes < 90:
        return _number(minutes, "minute")
    hours, rest = divmod(minutes - minutes % 5, 60)
    return _number(hours, "hour") + (f" {_number(rest, 'minute')}" if rest else "")


def plan_details(plan: Plan) -> list[str]:
    """One line per upload, for ``--list``."""
    lines: list[str] = []
    total = len(plan.uploads)
    for number, upload in enumerate(plan.uploads, 1):
        lines.append(f"Upload {number} of {total}: {upload.source.file}, {upload.spoken()}.")
    return lines


__all__ = [
    "BASE_SETTINGS",
    "BRAILLE_GRID",
    "FULL",
    "PROFILES",
    "QUICK",
    "RELEVANT",
    "VOICE_GRID",
    "Conversion",
    "Plan",
    "Upload",
    "build_plan",
    "label_for",
    "plan_details",
    "plan_sentences",
    "relevant_key",
]
