"""One station's facts, how call signs and frequencies are read, and the merge.

Pure and wx-free. Three jobs:

- :class:`StationFacts` -- the record a source yields and a pack carries. Every
  field is plain text so a pack is readable JSON; ``provenance`` says which
  source supplied each field, because a fact without its origin cannot be
  aged out or credited (the program plan: "each fact is stored with where it
  came from and when it was last confirmed").
- :func:`call_sign_in` / :func:`frequency_in` -- the official identity a
  station's own name often carries ("KUOW 94.9", "WNYC-FM"). Read
  conservatively: a call sign needs a band suffix or a frequency beside it,
  and common words that happen to look like one ("KISS FM") are refused, so a
  near miss stays empty rather than filled in wrong -- RadioTrail's rule.
- :func:`merge` -- many sources into one record per station, field by field,
  the earlier (more trusted) source winning, and a record from a second source
  folded into the first only when both its stream URL *and* its name agree
  (:func:`~quill.core.radio.catalog.keys.same_station`), never on URL alone.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields, replace

from quill.core.radio.catalog.keys import normalize_stream_url, same_station

#: The text fields a record carries, in the order a details pane shows them.
TEXT_FIELDS: tuple[str, ...] = (
    "name",
    "call_sign",
    "frequency",
    "slogan",
    "description",
    "genre",
    "tags",
    "city",
    "state",
    "country",
    "language",
    "owner",
    "homepage",
    "summary",
)


@dataclass(frozen=True, slots=True)
class StationFacts:
    """Everything a pack knows about one station. Empty string means unknown."""

    key: str
    name: str = ""
    stream_url: str = ""
    call_sign: str = ""
    frequency: str = ""
    slogan: str = ""
    description: str = ""
    genre: str = ""
    tags: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    language: str = ""
    owner: str = ""
    homepage: str = ""
    summary: str = ""
    #: The credit line a licence requires for this record's text, if any.
    attribution: str = ""
    #: The day these facts were last confirmed by their source (YYYY-MM-DD).
    confirmed: str = ""
    #: field name -> the id of the source that supplied it.
    provenance: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """The pack's JSON shape: empty fields left out, provenance sorted."""
        out: dict[str, object] = {"key": self.key}
        for spec in fields(self):
            if spec.name in ("key", "provenance"):
                continue
            value = getattr(self, spec.name)
            if value:
                out[spec.name] = value
        if self.provenance:
            out["provenance"] = dict(sorted(self.provenance.items()))
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> StationFacts:
        """Read one pack record. Unknown keys are ignored (packs may grow)."""
        known = {spec.name for spec in fields(cls)} - {"provenance"}
        values = {
            name: str(data.get(name) or "").strip()
            for name in known
            if isinstance(data.get(name, ""), (str, int, float))
        }
        raw = data.get("provenance")
        provenance = (
            {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}
            if isinstance(raw, Mapping)
            else {}
        )
        return cls(**values, provenance=provenance)  # type: ignore[arg-type]


# -- call signs and frequencies ---------------------------------------------

#: North American call signs: K/W (United States), CF/CH/CI/CJ/CK (Canada).
_CALL_RE = re.compile(r"\b([KW][A-Z]{2,3}|C[FHIJK][A-Z]{2})(?:-(FM|AM|LP|HD\d|DB))?\b")
#: Four-letter words that look like call signs and are station *names*.
_NOT_CALL_SIGNS = frozenset({
    "KISS",
    "KOOL",
    "KICK",
    "KIND",
    "KING",
    "KIDS",
    "WAVE",
    "WILD",
    "WORD",
    "WEST",
    "WARM",
    "WOLF",
    "WISH",
    "WIRE",
    "WALK",
    "WIND",
    "WOOD",
    "WINE",
    "WEEK",
    "WORK",
    "WOMAN",
    "WORLD",
    "WAKE",
    "WHAT",
    "WHEN",
    "WITH",
    "WEB",
    "WOW",
    "KEY",
    "CHILL",
    "CJAZZ",
})
_FM_RE = re.compile(r"(?<![\d.])(8[89]|9\d|10[0-7])[.,](\d)(?![\d])(\s*FM\b)?", re.IGNORECASE)
_AM_RE = re.compile(r"(?<![\d.])(5[3-9]\d|[6-9]\d\d|1[0-6]\d\d|170\d)\s*AM\b", re.IGNORECASE)


def frequency_in(text: str) -> str:
    """The broadcast frequency a name or line carries, as "98.5 FM" / "1090 AM"."""
    am = _AM_RE.search(text or "")
    if am:
        return f"{am.group(1)} AM"
    fm = _FM_RE.search(text or "")
    if fm:
        return f"{fm.group(1)}.{fm.group(2)} FM"
    return ""


def call_sign_in(text: str) -> str:
    """The call sign a station's name carries, or "" when it is not certain.

    Accepted only with a band suffix ("WNYC-FM") or with a frequency in the
    same text ("KUOW 94.9"), and never one of the words in the refusal list:
    "KISS FM" is a name, not a call sign.
    """
    source = text or ""
    has_frequency = bool(frequency_in(source))
    for match in _CALL_RE.finditer(source):
        letters = match.group(1)
        if letters in _NOT_CALL_SIGNS:
            continue
        if match.group(2) or has_frequency:
            return letters + (f"-{match.group(2)}" if match.group(2) else "")
    return ""


def frequency_tokens(frequency: str) -> str:
    """The index tokens for a frequency: "98.5 FM" -> "fm985 freq985".

    FTS5's tokenizer splits "98.5" at the dot, so the index carries a joined
    form instead and :func:`query_terms` rewrites a query the same way --
    which is what makes "98.5", "98.5 FM" and "985" land on one station.
    """
    text = (frequency or "").strip()
    am = _AM_RE.search(text)
    if am:
        digits = am.group(1)
        return f"am{digits} freq{digits}"
    fm = _FM_RE.search(text)
    if fm:
        digits = fm.group(1) + fm.group(2)
        return f"fm{digits} freq{digits}"
    return ""


def call_sign_tokens(call_sign: str) -> str:
    """The index tokens for a call sign: "KIRO-FM" -> "kiro kirofm"."""
    text = (call_sign or "").strip().lower()
    if not text:
        return ""
    base = text.split("-", 1)[0]
    joined = text.replace("-", "")
    return base if joined == base else f"{base} {joined}"


_WORD_RE = re.compile(r"[\w]+(?:[.,]\d)?", re.UNICODE)


def query_terms(query: str) -> list[str]:
    """A listener's query as index terms, frequencies and call signs normalized.

    "98.5 FM" -> ["fm985"], "98.5" -> ["freq985"], "1090 AM" -> ["am1090"],
    "KIRO-FM" -> ["kiro"], "jazz Seattle" -> ["jazz", "seattle"].
    """
    text = " ".join((query or "").split())
    terms: list[str] = []
    for regex, prefix in ((_AM_RE, "am"), (_FM_RE, "fm")):
        while True:
            match = regex.search(text)
            if match is None:
                break
            if prefix == "am":
                terms.append(f"am{match.group(1)}")
            else:
                digits = match.group(1) + match.group(2)
                terms.append(f"fm{digits}" if match.group(3) else f"freq{digits}")
            text = text[: match.start()] + " " + text[match.end() :]
    for word in _WORD_RE.findall(text):
        lowered = word.lower()
        call = _CALL_RE.fullmatch(word.upper().replace(" ", ""))
        if call and call.group(2):
            lowered = call.group(1).lower()
        if lowered in ("fm", "am"):
            continue  # a band on its own is in nearly every name; it narrows nothing
        terms.append(lowered)
    return terms


# -- the merge ---------------------------------------------------------------


def with_derived_identity(facts: StationFacts, source_id: str) -> StationFacts:
    """Fill call sign and frequency from the station's own name when absent."""
    changes: dict[str, str] = {}
    provenance = dict(facts.provenance)
    if not facts.call_sign:
        call = call_sign_in(facts.name)
        if call:
            changes["call_sign"] = call
            provenance["call_sign"] = source_id
    if not facts.frequency:
        frequency = frequency_in(facts.name)
        if frequency:
            changes["frequency"] = frequency
            provenance["frequency"] = source_id
    if not changes:
        return facts
    return replace(facts, **changes, provenance=provenance)


def _stamp(facts: StationFacts, source_id: str) -> StationFacts:
    """Mark every field this record supplies as coming from *source_id*."""
    provenance = dict(facts.provenance)
    for name in TEXT_FIELDS:
        if getattr(facts, name) and name not in provenance:
            provenance[name] = source_id
    return replace(facts, provenance=provenance)


def _fold(base: StationFacts, extra: StationFacts) -> StationFacts:
    """*base* with every field it lacks taken from *extra*, provenance kept."""
    changes: dict[str, str] = {}
    provenance = dict(base.provenance)
    for name in (*TEXT_FIELDS, "stream_url", "attribution", "confirmed"):
        if not getattr(base, name) and getattr(extra, name):
            changes[name] = getattr(extra, name)
            if name in extra.provenance:
                provenance[name] = extra.provenance[name]
    if base.attribution and extra.attribution and extra.attribution not in base.attribution:
        changes["attribution"] = f"{base.attribution} {extra.attribution}"
    if extra.confirmed > (changes.get("confirmed") or base.confirmed):
        changes["confirmed"] = extra.confirmed
    if not changes and provenance == base.provenance:
        return base
    return replace(base, **changes, provenance=provenance)


def merge(batches: Iterable[tuple[str, Iterable[StationFacts]]]) -> list[StationFacts]:
    """One record per station from ``(source id, records)`` batches, in trust order.

    The first batch is the most trusted: a later source only fills fields the
    earlier ones left empty. A later record joins an earlier one by key, or by
    stream URL **and** name together; a shared URL alone keeps two records.
    """
    by_key: dict[str, StationFacts] = {}
    by_url: dict[str, list[str]] = {}
    for source_id, records in batches:
        for raw in records:
            if not raw.key:
                continue
            record = with_derived_identity(_stamp(raw, source_id), source_id)
            target = record.key if record.key in by_key else ""
            if not target and record.stream_url:
                url = normalize_stream_url(record.stream_url)
                for candidate in by_url.get(url, []):
                    existing = by_key[candidate]
                    if same_station(existing.name, existing.stream_url, record.name, url):
                        target = candidate
                        break
            if target:
                by_key[target] = _fold(by_key[target], record)
                continue
            by_key[record.key] = record
            if record.stream_url:
                by_url.setdefault(normalize_stream_url(record.stream_url), []).append(record.key)
    return [by_key[key] for key in sorted(by_key)]


__all__ = [
    "TEXT_FIELDS",
    "StationFacts",
    "call_sign_in",
    "call_sign_tokens",
    "frequency_in",
    "frequency_tokens",
    "merge",
    "query_terms",
    "with_derived_identity",
]
