"""Formats, stages, settings and the server's shapes (PRD 3.2, 3.3, 3.5).

Read from Pneuma's client library (``scribe-api-client`` v0.3.1,
``crates/scribe-client/src/model.rs``), which is the only description of the
protocol. Parsing is forgiving: a field a newer or older server leaves out
gets the library's default rather than an exception, because a missing field
must never cost somebody their converted document.

wx-free, no I/O.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

# ------------------------------------------------------------------ formats


@dataclass(frozen=True, slots=True)
class Format:
    """One output format: its API identifier, its name for people, its file kind."""

    id: str
    label: str
    extension: str
    #: True for the audio formats, which need the voice settings.
    audio: bool = False


#: Every format a person can ask for, in the order the dialog lists them (7.3).
#: ``html_stream`` is the free preview the server starts on its own; it is
#: never asked for and never listed.
FORMATS: tuple[Format, ...] = (
    Format("html", "Accessible HTML", ".html"),
    Format("docx", "Word", ".docx"),
    Format("pdf", "Tagged PDF", ".pdf"),
    Format("epub", "EPUB", ".epub"),
    Format("mobi", "Kindle (MOBI)", ".mobi"),
    Format("daisy", "DAISY (text and audio)", ".zip", audio=True),
    Format("mp3", "MP3 audio", ".mp3", audio=True),
    Format("brf", "Braille (BRF)", ".brf"),
    Format("offline_html", "Web page for offline reading", ".zip"),
)
FORMAT_IDS: tuple[str, ...] = tuple(item.id for item in FORMATS)
PREVIEW_FORMAT = "html_stream"
_BY_ID = {item.id: item for item in FORMATS}

#: Scribe makes most formats from ``html``, and ``daisy`` from ``mp3`` (3.2),
#: so a job converts in this order: one conversion per document at a time.
DEPENDENCY_ORDER: tuple[str, ...] = (
    "html",
    "docx",
    "pdf",
    "epub",
    "mobi",
    "offline_html",
    "brf",
    "mp3",
    "daisy",
)


def format_by_id(format_id: str) -> Format | None:
    return _BY_ID.get(format_id)


def format_label(format_id: str) -> str:
    found = _BY_ID.get(format_id)
    return found.label if found else format_id


def valid_formats(format_ids: Any) -> list[str]:
    """Only known format ids, each once, in the dialog's order."""
    wanted = {str(item) for item in (format_ids or ())}
    return [item for item in FORMAT_IDS if item in wanted]


def ordered_for_conversion(format_ids: Any) -> list[str]:
    """*format_ids* in Scribe's dependency order: html first, mp3 before daisy."""
    wanted = set(valid_formats(format_ids))
    return [item for item in DEPENDENCY_ORDER if item in wanted]


def formats_phrase(format_ids: Any) -> str:
    """``"Word and Braille (BRF)"`` -- the formats, for a sentence."""
    labels = [format_label(item) for item in valid_formats(format_ids)]
    if not labels:
        return "nothing"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]


# --------------------------------------------------------- settings groups

#: The dialog's setting groups and the formats that show each (7.3). ``None``
#: means always shown: the language and the pictures matter to every format.
GROUPS: tuple[tuple[str, str, frozenset[str] | None], ...] = (
    ("language", "Language and voice", None),
    ("braille", "Braille", frozenset({"brf"})),
    ("print", "Print", frozenset({"pdf", "docx"})),
    ("pictures", "Pictures and maths", None),
)


def visible_groups(format_ids: Any) -> list[str]:
    """The group keys to show for the chosen formats, in display order."""
    chosen = set(valid_formats(format_ids))
    return [key for key, _label, shown_by in GROUPS if shown_by is None or chosen & shown_by]


def settings_summary(format_ids: Any) -> str:
    """The silent line under the formats: ``"Settings below: Language and voice, Braille"``."""
    labels = dict((key, label) for key, label, _shown in GROUPS)
    names = [labels[key] for key in visible_groups(format_ids)]
    return "Settings below: " + ", ".join(names) if names else "No settings for these formats."


# ------------------------------------------------------------------ stages

STAGES: dict[str, str] = {
    "queue": "waiting in Scribe's queue",
    "start": "starting",
    "convert": "converting",
    "add_image_descriptions": "adding image descriptions",
    "complete": "complete",
}


def stage_words(stage: str) -> str:
    return STAGES.get(stage, stage.replace("_", " "))


# ---------------------------------------------------------------- settings

#: Speech speeds the website offers (Pneuma, 2026-11-21), with their labels.
#: 3x and 4x may come out no faster than 2x until Pneuma confirms they do.
TTS_RATES: tuple[tuple[float, str], ...] = (
    (0.5, "0.5 times"),
    (0.75, "0.75 times"),
    (1.0, "Normal"),
    (1.5, "1.5 times"),
    (2.0, "2 times"),
    (3.0, "3 times (may not be faster than 2 times)"),
    (4.0, "4 times (may not be faster than 2 times)"),
)
#: Braille ranges the website offers; the server does not check them yet.
BRAILLE_CELLS_RANGE = (20, 42)
BRAILLE_LINES_RANGE = (20, 30)

#: Settings that shape the HTML, which Scribe starts as soon as the upload
#: lands: they go in with the upload and are fixed for that document (3.3).
HTML_SHAPING: tuple[tuple[str, str], ...] = (
    ("language", "language"),
    ("add_image_descriptions", "picture descriptions"),
    ("math", "mathematics"),
    ("large_print", "large print"),
)
HTML_SHAPING_FIELDS: frozenset[str] = frozenset(key for key, _words in HTML_SHAPING)


def nearest_rate(value: Any, default: float = 1.0) -> float:
    """*value* as one of :data:`TTS_RATES` (the nearest), or *default*."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min((rate for rate, _label in TTS_RATES), key=lambda rate: abs(rate - number))


def _form_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


TTS_GENDERS: tuple[tuple[str, str], ...] = (
    ("", "No preference"),
    ("female", "Female"),
    ("male", "Male"),
    ("neutral", "Neutral"),
)


@dataclass(slots=True)
class ScribeSettings:
    """A document's conversion settings (3.3); every field Scribe has.

    ``dialects`` maps a language code to a dialect locale, ``voices`` a locale
    to a voice's short name. The server does not check ranges yet, so values
    read from it or from options are clamped to the website's (3.3).
    """

    language: str = ""
    dialects: dict[str, str] = field(default_factory=dict)
    voices: dict[str, str] = field(default_factory=dict)
    tts_gender: str = ""
    tts_rate: float = 1.0
    braille_translation_table: str = ""
    braille_cells_per_line: int = 40
    braille_split_into_pages: bool = True
    braille_lines_per_page: int = 25
    large_print: bool = False
    add_image_descriptions: bool = True
    math: bool = False
    notify_when_complete: bool = False

    def to_update(self, *, leave_out: frozenset[str] = frozenset()) -> dict[str, Any]:
        """The body of ``PATCH .../settings``: ``dialects`` and ``voices`` as JSON
        strings, as the server takes them; an empty language or table is left out
        so the server keeps detecting or its own default. *leave_out* names
        fields not to send (the HTML-shaping ones, for a document already in
        the account)."""
        body: dict[str, Any] = {
            "tts_rate": float(self.tts_rate),
            "braille_cells_per_line": int(self.braille_cells_per_line),
            "braille_split_into_pages": bool(self.braille_split_into_pages),
            "braille_lines_per_page": int(self.braille_lines_per_page),
            "large_print": bool(self.large_print),
            "add_image_descriptions": bool(self.add_image_descriptions),
            "math": bool(self.math),
            "notify_when_complete": bool(self.notify_when_complete),
        }
        if self.language:
            body["language"] = self.language
        if self.dialects:
            body["dialects"] = json.dumps(self.dialects)
        if self.voices:
            body["voices"] = json.dumps(self.voices)
        if self.tts_gender:
            body["tts_gender"] = self.tts_gender
        if self.braille_translation_table:
            body["braille_translation_table"] = self.braille_translation_table
        return {key: value for key, value in body.items() if key not in leave_out}

    def to_upload_fields(self) -> list[tuple[str, str]]:
        """The full set as ``document[settings][field]`` form fields for the
        upload (3.3): a field left out would get Scribe's built-in default,
        not the person's."""
        return [
            (f"document[settings][{key}]", _form_value(value))
            for key, value in self.to_update().items()
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Any) -> ScribeSettings:
        """From the server's settings object or a stored dict; bad values are defaults."""
        if not isinstance(data, dict):
            return cls()
        base = cls()
        return cls(
            language=str(data.get("language") or ""),
            dialects=_str_map(data.get("dialects")),
            voices=_str_map(data.get("voices")),
            tts_gender=str(data.get("tts_gender") or ""),
            tts_rate=nearest_rate(data.get("tts_rate"), base.tts_rate),
            braille_translation_table=str(data.get("braille_translation_table") or ""),
            braille_cells_per_line=_clamp_int(
                data.get("braille_cells_per_line"), 40, *BRAILLE_CELLS_RANGE
            ),
            braille_split_into_pages=bool(data.get("braille_split_into_pages", True)),
            braille_lines_per_page=_clamp_int(
                data.get("braille_lines_per_page"), 25, *BRAILLE_LINES_RANGE
            ),
            large_print=bool(data.get("large_print", False)),
            add_image_descriptions=bool(data.get("add_image_descriptions", True)),
            math=bool(data.get("math", False)),
            notify_when_complete=bool(data.get("notify_when_complete", False)),
        )


def _str_map(value: Any) -> dict[str, str]:
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else {}
        except ValueError:
            return {}
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items() if v is not None}


def _clamp_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _clamp_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


# ---------------------------------------------------------- server shapes


@dataclass(frozen=True, slots=True)
class Output:
    """One row of a document's outputs."""

    format: str
    stage: str
    progress: float = 0.0
    estimated_time_remaining: int | None = None
    is_preview: bool = False
    downloadable: bool = True

    @property
    def is_complete(self) -> bool:
        return self.stage == "complete"

    @classmethod
    def from_mapping(cls, data: Any) -> Output | None:
        if not isinstance(data, dict) or not data.get("format"):
            return None
        eta = data.get("estimated_time_remaining")
        return cls(
            format=str(data.get("format")),
            stage=str(data.get("stage") or ""),
            progress=_clamp_float(data.get("progress"), 0.0, 0.0, 1.0),
            estimated_time_remaining=int(eta) if isinstance(eta, (int, float)) else None,
            is_preview=bool(data.get("is_preview", False)),
            downloadable=bool(data.get("downloadable", True)),
        )


def parse_outputs(items: Any) -> list[Output]:
    parsed = [Output.from_mapping(item) for item in (items or [])]
    return [item for item in parsed if item is not None]


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    """One document in the person's Scribe account (7.5)."""

    id: str
    title: str = ""
    page_count: int | None = None
    inserted_at: str = ""
    is_password_needed: bool = False
    outputs: tuple[Output, ...] = ()
    #: Trash view only.
    trashed_at: str = ""
    permanently_delete_at: str = ""

    @property
    def ready_formats(self) -> list[str]:
        """Formats made and downloadable, in the dialog's order."""
        done = {o.format for o in self.outputs if o.is_complete and o.downloadable}
        return [item for item in FORMAT_IDS if item in done]

    @property
    def display_title(self) -> str:
        return self.title or "Untitled document"

    @property
    def charged(self) -> bool:
        """True once a full conversion is made: pages are charged once per
        document, so every further format uses no pages (3.6)."""
        return any(
            o.is_complete and not o.is_preview and o.format != PREVIEW_FORMAT for o in self.outputs
        )

    @classmethod
    def from_mapping(cls, data: Any) -> DocumentSummary | None:
        if not isinstance(data, dict) or not data.get("id"):
            return None
        pages = data.get("page_count")
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or ""),
            page_count=int(pages) if isinstance(pages, (int, float)) else None,
            inserted_at=str(data.get("inserted_at") or ""),
            is_password_needed=bool(data.get("is_password_needed", False)),
            outputs=tuple(parse_outputs(data.get("outputs"))),
            trashed_at=str(data.get("trashed_at") or ""),
            permanently_delete_at=str(data.get("permanently_delete_at") or ""),
        )


def parse_documents(items: Any) -> list[DocumentSummary]:
    parsed = [DocumentSummary.from_mapping(item) for item in (items or [])]
    return [item for item in parsed if item is not None]


@dataclass(frozen=True, slots=True)
class Account:
    """Who is signed in, and how many pages they have left (3.4)."""

    first_name: str = ""
    last_name: str = ""
    email: str = ""
    organization_name: str = ""
    pages_remaining: int | None = None

    @property
    def name(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email or "your Scribe account"

    def pages_phrase(self) -> str:
        """``"1,240 pages left, using credits from Acme."`` -- for an organization
        member the count is the organization's shared pool (3.4)."""
        if self.pages_remaining is None:
            return "Pages left unknown."
        return pages_left_phrase(self.pages_remaining, self.organization_name) + "."

    @classmethod
    def from_mappings(cls, info: Any, billing: Any) -> Account:
        info = info if isinstance(info, dict) else {}
        billing = billing if isinstance(billing, dict) else {}
        pages = billing.get("pages_remaining")
        return cls(
            first_name=str(info.get("first_name") or ""),
            last_name=str(info.get("last_name") or ""),
            email=str(info.get("email") or ""),
            organization_name=str(info.get("organization_name") or ""),
            pages_remaining=int(pages) if isinstance(pages, (int, float)) else None,
        )


def pages_left_phrase(count: int, organization: str = "") -> str:
    """``"1,240 pages left"``, with ``", using credits from <organization>"``."""
    text = f"{count:,} page left" if count == 1 else f"{count:,} pages left"
    return f"{text}, using credits from {organization}" if organization else text


def parse_pairs(items: Any) -> list[tuple[str, str]]:
    """``[[name, id], ...]`` lists (languages, dialects, braille tables)."""
    pairs: list[tuple[str, str]] = []
    for item in items or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            pairs.append((str(item[0]), str(item[1])))
    return pairs


def parse_voices(items: Any) -> list[tuple[str, str, bool]]:
    """``[[name, short_name, has_sample], ...]``."""
    voices: list[tuple[str, str, bool]] = []
    for item in items or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            sample = bool(item[2]) if len(item) > 2 else False
            voices.append((str(item[0]), str(item[1]), sample))
    return voices


__all__ = [
    "BRAILLE_CELLS_RANGE",
    "BRAILLE_LINES_RANGE",
    "DEPENDENCY_ORDER",
    "FORMATS",
    "FORMAT_IDS",
    "GROUPS",
    "HTML_SHAPING",
    "HTML_SHAPING_FIELDS",
    "PREVIEW_FORMAT",
    "STAGES",
    "TTS_GENDERS",
    "TTS_RATES",
    "Account",
    "DocumentSummary",
    "Format",
    "Output",
    "ScribeSettings",
    "format_by_id",
    "format_label",
    "nearest_rate",
    "pages_left_phrase",
    "formats_phrase",
    "ordered_for_conversion",
    "parse_documents",
    "parse_outputs",
    "parse_pairs",
    "parse_voices",
    "settings_summary",
    "stage_words",
    "valid_formats",
    "visible_groups",
]
