"""Pluggable dictionary and thesaurus services (DICT-1).

A small, UI-agnostic lexical service layer with a common provider interface so
definitions, synonyms, antonyms, rhymes, and related words can come from
selectable backends. The offline provider (the bundled MyThes thesaurus data)
is always available and is the default. Two free, key-less online providers are
available behind an explicit per-feature consent gate that the caller controls
by passing ``online=True``: the Free Dictionary API for definitions and Datamuse
for synonyms, antonyms, rhymes, and related ("means-like") words.

All HTTPS goes through the verified TLS context (SEC-5). Online lookups are
cached and error-tolerant: when a provider is unavailable the result gracefully
falls back to the offline answer. No provider requires an API key.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from quill.core import thesaurus
from quill.core.net import verified_ssl_context

logger = logging.getLogger(__name__)

FREE_DICTIONARY_HOST = "https://freedictionaryapi.com"
DATAMUSE_HOST = "https://api.datamuse.com"
WIKIPEDIA_HOST = "https://{lang}.wikipedia.org"

_DEFAULT_TIMEOUT = 8.0
_MAX_ITEMS = 40


@dataclass(frozen=True, slots=True)
class Definition:
    """One sense of a word: its part of speech, gloss, and optional example."""

    part_of_speech: str
    text: str
    example: str = ""


@dataclass(frozen=True, slots=True)
class EncyclopediaEntry:
    """One encyclopedia summary (#897): a title, a short extract, and its URL."""

    title: str
    summary: str
    url: str


@dataclass(frozen=True, slots=True)
class LexicalResult:
    """Normalized lexical data for one word, regardless of source."""

    word: str
    definitions: tuple[Definition, ...] = ()
    synonyms: tuple[str, ...] = ()
    antonyms: tuple[str, ...] = ()
    rhymes: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    encyclopedia: tuple[EncyclopediaEntry, ...] = ()
    sources: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (
            self.definitions
            or self.synonyms
            or self.antonyms
            or self.rhymes
            or self.related
            or self.encyclopedia
        )


def _dedupe(values: object, *, limit: int = _MAX_ITEMS) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(text)
        if len(ordered) >= limit:
            break
    return tuple(ordered)


class LexicalProvider(ABC):
    """A source of lexical data for a word."""

    name: str = "lexical"
    online: bool = False

    @abstractmethod
    def lookup(self, word: str) -> LexicalResult | None:
        """Return normalized data for ``word``, or ``None`` if not found."""


class OfflineLexicalProvider(LexicalProvider):
    """The bundled MyThes thesaurus: synonyms grouped by part of speech."""

    name = "offline"
    online = False

    def lookup(self, word: str) -> LexicalResult | None:
        entry = thesaurus.lookup(word)
        if entry is None:
            return None
        return LexicalResult(
            word=entry.word or word,
            synonyms=_dedupe(list(entry.all_synonyms)),
            sources=("offline",),
        )


def _http_get_json(url: str, *, timeout: float = _DEFAULT_TIMEOUT) -> object | None:
    """GET a URL and return parsed JSON, or None on any network/parse failure.

    Shared by the consented online lexical providers (Free Dictionary and
    Datamuse). Only ever called when the caller has enabled online lookups, and
    always over HTTPS with a verified TLS context.
    """
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout, context=verified_ssl_context()) as response:
            parsed: object = json.loads(response.read().decode("utf-8", errors="replace"))
            return parsed
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


class FreeDictionaryProvider(LexicalProvider):
    """Definitions (with examples), synonyms, and antonyms from Free Dictionary."""

    name = "Free Dictionary"
    online = True

    def __init__(self, host: str = FREE_DICTIONARY_HOST, *, language: str = "en") -> None:
        self._host = host.rstrip("/")
        self._language = language

    def lookup(self, word: str) -> LexicalResult | None:
        url = f"{self._host}/api/v1/entries/{self._language}/{quote(word)}"
        payload = _http_get_json(url)
        return normalize_free_dictionary(word, payload)


def normalize_free_dictionary(word: str, payload: object) -> LexicalResult | None:
    """Normalize a Free Dictionary response into a LexicalResult (pure)."""
    entries = _free_dictionary_entries(payload)
    if not entries:
        return None
    definitions: list[Definition] = []
    synonyms: list[str] = []
    antonyms: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pos = str(entry.get("partOfSpeech", "")).strip()
        for sense in _as_list(entry.get("senses")) + _as_list(entry.get("definitions")):
            if not isinstance(sense, dict):
                continue
            gloss = str(sense.get("definition", "")).strip()
            if not gloss:
                continue
            examples = _as_list(sense.get("examples"))
            example = str(examples[0]).strip() if examples else ""
            definitions.append(Definition(part_of_speech=pos, text=gloss, example=example))
            synonyms.extend(str(s) for s in _as_list(sense.get("synonyms")))
            antonyms.extend(str(a) for a in _as_list(sense.get("antonyms")))
        synonyms.extend(str(s) for s in _as_list(entry.get("synonyms")))
        antonyms.extend(str(a) for a in _as_list(entry.get("antonyms")))
    if not definitions and not synonyms and not antonyms:
        return None
    return LexicalResult(
        word=word,
        definitions=tuple(definitions[:_MAX_ITEMS]),
        synonyms=_dedupe(synonyms),
        antonyms=_dedupe(antonyms),
        sources=("Free Dictionary",),
    )


def _free_dictionary_entries(payload: object) -> list[object]:
    if isinstance(payload, dict):
        return _as_list(payload.get("entries"))
    if isinstance(payload, list):
        # Some deployments return a list of word objects.
        entries: list[object] = []
        for item in payload:
            if isinstance(item, dict):
                entries.extend(_as_list(item.get("entries")) or [item])
        return entries
    return []


def _as_list(value: object) -> list[object]:
    return list(value) if isinstance(value, (list, tuple)) else []


class DatamuseProvider(LexicalProvider):
    """Synonyms, antonyms, rhymes, and related words from Datamuse."""

    name = "Datamuse"
    online = True
    # Datamuse relation codes -> LexicalResult field.
    _RELATIONS = (
        ("rel_syn", "synonyms"),
        ("rel_ant", "antonyms"),
        ("rel_rhy", "rhymes"),
        ("ml", "related"),
    )

    def __init__(self, host: str = DATAMUSE_HOST) -> None:
        self._host = host.rstrip("/")

    def lookup(self, word: str) -> LexicalResult | None:
        fields: dict[str, tuple[str, ...]] = {}
        for code, field_name in self._RELATIONS:
            query = urlencode({code: word, "max": _MAX_ITEMS})
            payload = _http_get_json(f"{self._host}/words?{query}")
            fields[field_name] = normalize_datamuse(payload)
        if not any(fields.values()):
            return None
        return LexicalResult(
            word=word,
            synonyms=fields.get("synonyms", ()),
            antonyms=fields.get("antonyms", ()),
            rhymes=fields.get("rhymes", ()),
            related=fields.get("related", ()),
            sources=("Datamuse",),
        )


def normalize_datamuse(payload: object) -> tuple[str, ...]:
    """Normalize a Datamuse word list into ordered, de-duplicated words (pure)."""
    if not isinstance(payload, list):
        return ()
    words = [item.get("word") for item in payload if isinstance(item, dict) and item.get("word")]
    return _dedupe(words)


class WikipediaProvider(LexicalProvider):
    """A keyless encyclopedia summary from the Wikipedia REST API (#897)."""

    name = "Wikipedia"
    online = True

    def __init__(self, host: str = WIKIPEDIA_HOST, *, language: str = "en") -> None:
        self._host = host.format(lang=language)
        self._language = language

    def lookup(self, word: str) -> LexicalResult | None:
        url = f"{self._host}/api/rest_v1/page/summary/{quote(word)}"
        payload = _http_get_json(url)
        return normalize_wikipedia(word, payload)


def normalize_wikipedia(word: str, payload: object) -> LexicalResult | None:
    """Normalize a Wikipedia page-summary response into a LexicalResult (pure).

    A disambiguation page or a missing extract is treated as "no entry" --
    #897 asks for a summary, not a disambiguation list to sort through.
    """
    if not isinstance(payload, dict):
        return None
    if str(payload.get("type", "")) == "disambiguation":
        return None
    title = str(payload.get("title", "")).strip()
    summary = str(payload.get("extract", "")).strip()
    if not title or not summary:
        return None
    content_urls = payload.get("content_urls")
    url = ""
    if isinstance(content_urls, dict):
        desktop = content_urls.get("desktop")
        if isinstance(desktop, dict):
            url = str(desktop.get("page", "")).strip()
    return LexicalResult(
        word=word,
        encyclopedia=(EncyclopediaEntry(title=title, summary=summary, url=url),),
        sources=("Wikipedia",),
    )


def _union_results(base: LexicalResult, other: LexicalResult) -> LexicalResult:
    """Combine two results, preferring base order and unioning each list."""
    return LexicalResult(
        word=base.word or other.word,
        definitions=tuple(list(base.definitions) + list(other.definitions))[:_MAX_ITEMS],
        synonyms=_dedupe(list(base.synonyms) + list(other.synonyms)),
        antonyms=_dedupe(list(base.antonyms) + list(other.antonyms)),
        rhymes=_dedupe(list(base.rhymes) + list(other.rhymes)),
        related=_dedupe(list(base.related) + list(other.related)),
        encyclopedia=tuple(list(base.encyclopedia) + list(other.encyclopedia))[:_MAX_ITEMS],
        sources=_dedupe(list(base.sources) + list(other.sources)),
    )


class LexicalService:
    """Offline-first lexical lookups with optional consented online providers."""

    def __init__(
        self,
        offline: LexicalProvider | None = None,
        online: list[LexicalProvider] | None = None,
    ) -> None:
        self._offline = offline if offline is not None else OfflineLexicalProvider()
        self._online = list(online) if online is not None else []
        self._cache: dict[tuple[str, bool], LexicalResult] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def lookup(self, word: str, *, online: bool = False) -> LexicalResult:
        """Look up ``word``. Online providers are only queried when ``online``.

        Always returns a result (possibly empty); never raises for a provider
        failure. Results are cached per ``(word, online)``.
        """
        normalized = (word or "").strip()
        if not normalized:
            return LexicalResult(word="")
        key = (normalized.lower(), online)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self._offline.lookup(normalized) or LexicalResult(word=normalized)
        if online:
            for provider in self._online:
                try:
                    online_result = provider.lookup(normalized)
                except Exception as error:  # noqa: BLE001 - a provider failure must not break lookup
                    logger.debug("Lexical provider %s failed: %s", provider.name, error)
                    online_result = None
                if online_result is not None:
                    result = _union_results(result, online_result)
        self._cache[key] = result
        return result


def default_service(*, include_online: bool = True) -> LexicalService:
    """Build the default service: offline always, online providers optional."""
    online: list[LexicalProvider] = []
    if include_online:
        online = [FreeDictionaryProvider(), DatamuseProvider(), WikipediaProvider()]
    return LexicalService(online=online)


# --- Source mode and merge-and-compare (DICT-3) ----------------------------
#
# Per lexical kind the user chooses which source to trust: offline only (fast,
# always available), online only (richer, consent-gated), or both combined. In
# combined mode the offline and online term lists are merged into one
# de-duplicated, provenance-tagged, agreement-ranked set: a term both sources
# agree on ranks first, and each entry records where it came from.

SOURCE_OFFLINE = "offline"
SOURCE_ONLINE = "online"
SOURCE_BOTH = "both"
SOURCE_MODES = (SOURCE_OFFLINE, SOURCE_ONLINE, SOURCE_BOTH)


def normalize_source_mode(mode: object) -> str:
    """Coerce an arbitrary value to a valid source mode (default: offline)."""
    text = str(mode).strip().lower()
    return text if text in SOURCE_MODES else SOURCE_OFFLINE


@dataclass(frozen=True, slots=True)
class MergedTerm:
    """A merged term with the source labels that supplied it."""

    value: str
    sources: tuple[str, ...]

    @property
    def provenance(self) -> str:
        """A short label: a single source name, or "both" when more than one."""
        if len(self.sources) > 1:
            return SOURCE_BOTH
        return self.sources[0] if self.sources else ""


def merge_terms(sourced: list[tuple[str, object]]) -> tuple[MergedTerm, ...]:
    """Merge per-source term lists into one ranked, provenance-tagged set (pure).

    ``sourced`` is an ordered list of ``(source_label, terms)`` pairs. Terms are
    case-folded for de-duplication but the first-seen spelling is kept. The
    result is ordered so terms more sources agree on rank first (agreement
    weight), with ties broken by first-seen order, so the union degrades to the
    leading source's order when only one source supplies a term.
    """
    order: list[str] = []
    canonical: dict[str, str] = {}
    sources_for: dict[str, list[str]] = {}
    for label, terms in sourced:
        if not isinstance(terms, (list, tuple)):
            continue
        for term in terms:
            text = str(term).strip()
            if not text:
                continue
            key = text.lower()
            if key not in canonical:
                canonical[key] = text
                sources_for[key] = []
                order.append(key)
            if label not in sources_for[key]:
                sources_for[key].append(label)
    ranked = sorted(order, key=lambda key: (-len(sources_for[key]), order.index(key)))
    return tuple(MergedTerm(canonical[key], tuple(sources_for[key])) for key in ranked)


def merged_terms_for_mode(
    offline_terms: object,
    online_sources: list[tuple[str, object]],
    *,
    mode: str,
) -> tuple[MergedTerm, ...]:
    """Apply the user's source mode to offline and online term lists (pure).

    ``offline_terms`` is the offline list; ``online_sources`` is an ordered list
    of ``(provider_name, terms)`` pairs. ``mode`` is one of :data:`SOURCE_MODES`.
    Offline-only and online-only return just that side; combined merges both.
    """
    normalized = normalize_source_mode(mode)
    offline_pair = (SOURCE_OFFLINE, offline_terms)
    if normalized == SOURCE_OFFLINE:
        return merge_terms([offline_pair])
    if normalized == SOURCE_ONLINE:
        return merge_terms(online_sources)
    return merge_terms([offline_pair, *online_sources])


# --- Accessible Look Up surface (DICT-2) -----------------------------------
#
# A screen-reader-pageable view of a LexicalResult plus a flat list of
# selectable items. Each item is either an "insert" (replace the looked-up word
# with this term) or a "pivot" (run a fresh lookup on this term). The view text
# and the item list are pure functions of the result, so the UI dialog is a thin
# presenter over them and the behavior is fully testable in core.

ACTION_INSERT = "insert"
ACTION_PIVOT = "pivot"

# Section kinds, in the order they are presented.
KIND_ENCYCLOPEDIA = "encyclopedia"
KIND_DEFINITION = "definition"
KIND_SYNONYM = "synonym"
KIND_ANTONYM = "antonym"
KIND_RHYME = "rhyme"
KIND_RELATED = "related"


@dataclass(frozen=True, slots=True)
class LookupItem:
    """One selectable entry in the Look Up surface."""

    kind: str
    label: str
    value: str
    action: str


def build_lookup_items(result: LexicalResult) -> tuple[LookupItem, ...]:
    """Flatten a result into selectable items (pure).

    Definitions are read-only context (no action); the word lists are pivotable
    *and* insertable — selecting a synonym replaces the word, which is the most
    common writer action, so synonyms/antonyms/related/rhymes use ``insert`` and
    definition example words are not actionable. Every item is reachable.
    """
    items: list[LookupItem] = []
    for entry in result.encyclopedia:
        label = f"{entry.title}: {entry.summary}"
        items.append(LookupItem(KIND_ENCYCLOPEDIA, label, entry.summary, ""))
    for definition in result.definitions:
        pos = f"{definition.part_of_speech}: " if definition.part_of_speech else ""
        items.append(LookupItem(KIND_DEFINITION, f"{pos}{definition.text}", definition.text, ""))
    for kind, values in (
        (KIND_SYNONYM, result.synonyms),
        (KIND_ANTONYM, result.antonyms),
        (KIND_RELATED, result.related),
        (KIND_RHYME, result.rhymes),
    ):
        for value in values:
            items.append(LookupItem(kind, value, value, ACTION_INSERT))
    return tuple(items)


def render_lookup(result: LexicalResult) -> str:
    """Render a result as screen-reader-pageable text (pure).

    Leads with the word and its sources, then one labelled section per kind that
    has entries (Definitions, Synonyms, Antonyms, Related, Rhymes). Definitions
    show part of speech and any example sentence. An empty result reads as a
    single clear "no entries" line so the surface is never silently blank.
    """
    word = result.word or ""
    header = f"Look up: {word}" if word else "Look up"
    if result.sources:
        header += f" — {', '.join(result.sources)}"
    lines: list[str] = [header]

    if result.is_empty:
        lines.append("No entries found.")
        return "\n".join(lines)

    if result.encyclopedia:
        lines.append("")
        lines.append("Encyclopedia:")
        for entry in result.encyclopedia:
            lines.append(f"{entry.title}: {entry.summary}")
            if entry.url:
                lines.append(f"   Source: {entry.url}")

    if result.definitions:
        lines.append("")
        lines.append("Definitions:")
        for index, definition in enumerate(result.definitions, start=1):
            pos = f"({definition.part_of_speech}) " if definition.part_of_speech else ""
            lines.append(f"{index}. {pos}{definition.text}")
            if definition.example:
                lines.append(f"   Example: {definition.example}")

    for title, values in (
        ("Synonyms", result.synonyms),
        ("Antonyms", result.antonyms),
        ("Related", result.related),
        ("Rhymes", result.rhymes),
    ):
        if values:
            lines.append("")
            lines.append(f"{title}: {', '.join(values)}")

    return "\n".join(lines)
