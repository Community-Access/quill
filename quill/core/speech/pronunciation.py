"""Pronunciation dictionaries for all QUILL speech (batch + live Read Aloud).

wx-free, strict-typed. A *dictionary* is a named, ordered set of *entries*, each
mapping a term to how it should be spoken. Scope is two-dimensional
(``batch-document-to-speech-plan.md`` §4.7.1):

* **location** — ``global`` (under ``app_data_dir()/speech/pronunciation/``,
  available everywhere) or ``project`` (under ``<project>/.quill/pronunciation/``,
  active only while that folder of files is open and travelling with it);
* **engine** — ``None`` (all engines, applied as pre-synthesis text substitution)
  or one synthesizer id (applied only when that engine is active).

:func:`apply_pronunciations` is the single substitution stage both the batch and
live paths call, so a fix made once is heard everywhere. Conflict precedence,
most specific first: project+engine > project+all > global+engine > global+all.

Respelling substitution is fully implemented. On SSML-capable engines (SAPI 5,
eSpeak-NG) an ``ssml`` entry renders its markup natively: the utterance becomes a
validated ``<speak>`` with surrounding text XML-escaped (:func:`apply_pronunciations`
sets ``is_ssml``). On other engines (Kokoro/Piper/DECtalk) ``ssml``/``phoneme``
entries degrade to their ``plain_fallback``; raw markup is never read aloud.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

ENGINES: frozenset[str] = frozenset({"sapi5", "dectalk", "piper", "kokoro", "espeak"})
_MODES: frozenset[str] = frozenset({"respelling", "phoneme", "ssml"})
_SCOPES: frozenset[str] = frozenset({"global", "project"})


def _base_language(language: str) -> str:
    """Normalize a language tag to its lowercase base subtag (``es-ES`` -> ``es``)."""
    return language.strip().lower().replace("_", "-").split("-", 1)[0]


@dataclass(slots=True)
class PronunciationEntry:
    """One term → spoken-form mapping (§4.7.2)."""

    term: str = ""
    replacement: str = ""
    mode: str = "respelling"  # respelling | phoneme | ssml
    plain_fallback: str = ""  # used when the engine cannot honour mode (required for ssml/phoneme)
    whole_word: bool = True
    case_sensitive: bool = False
    regex: bool = False
    enabled: bool = True
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "replacement": self.replacement,
            "mode": self.mode if self.mode in _MODES else "respelling",
            "plain_fallback": self.plain_fallback,
            "whole_word": self.whole_word,
            "case_sensitive": self.case_sensitive,
            "regex": self.regex,
            "enabled": self.enabled,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Any) -> PronunciationEntry:
        if not isinstance(data, dict):
            return cls()
        mode = str(data.get("mode", "respelling"))
        return cls(
            term=str(data.get("term", "")),
            replacement=str(data.get("replacement", "")),
            mode=mode if mode in _MODES else "respelling",
            plain_fallback=str(data.get("plain_fallback", "")),
            whole_word=bool(data.get("whole_word", True)),
            case_sensitive=bool(data.get("case_sensitive", False)),
            regex=bool(data.get("regex", False)),
            enabled=bool(data.get("enabled", True)),
            note=str(data.get("note", "")),
        )


@dataclass(slots=True)
class PronunciationDictionary:
    """A named, scoped collection of entries (§4.7.1)."""

    id: str
    name: str = ""
    scope: str = "global"  # global | project (the storage location)
    engine: str | None = None  # None = all engines; else a synthesizer id
    enabled: bool = True
    # Language scope (ISO 639-1, e.g. "es"): "" = applies to every language; else
    # only when synthesizing that language (e.g. a Spanish-only dictionary for the
    # translated-audio-export path). The base language is compared, so "es" matches
    # "es", "es-ES", and "es-419".
    language: str = ""
    entries: list[PronunciationEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scope": self.scope if self.scope in _SCOPES else "global",
            "engine": self.engine if self.engine in ENGINES else None,
            "enabled": self.enabled,
            "language": self.language,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Any) -> PronunciationDictionary:
        if not isinstance(data, dict):
            return cls(id="")
        scope = str(data.get("scope", "global"))
        engine = data.get("engine")
        raw_entries = data.get("entries")
        entries = (
            [PronunciationEntry.from_dict(item) for item in raw_entries]
            if isinstance(raw_entries, list)
            else []
        )
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            scope=scope if scope in _SCOPES else "global",
            engine=engine if engine in ENGINES else None,
            enabled=bool(data.get("enabled", True)),
            language=_base_language(str(data.get("language", ""))),
            entries=entries,
        )

    def applies_to_language(self, language: str) -> bool:
        """True when this dictionary applies for synthesizing *language*.

        An all-language dictionary (``language == ""``) always applies; a
        language-scoped one applies only when the base languages match.
        """
        if not self.language:
            return True
        return _base_language(language) == self.language

    def specificity(self) -> int:
        """Higher = more specific (project+engine 3 … global+all 0)."""
        return (2 if self.scope == "project" else 0) + (1 if self.engine is not None else 0)


@dataclass(slots=True)
class PronunciationResult:
    """Output of :func:`apply_pronunciations`."""

    text: str
    is_ssml: bool = False
    applied: dict[str, int] = field(default_factory=dict)  # entry term → times fired

    @property
    def total_applied(self) -> int:
        return sum(self.applied.values())


# ----------------------------------------------------------------------------
# Storage
# ----------------------------------------------------------------------------


def global_dir() -> Path:
    return app_data_dir() / "speech" / "pronunciation"


def project_dir_for(project_dir: Path) -> Path:
    return Path(project_dir) / ".quill" / "pronunciation"


def _load_from(folder: Path, scope: str) -> list[PronunciationDictionary]:
    out: list[PronunciationDictionary] = []
    try:
        paths = sorted(folder.glob("*.json"))
    except OSError:
        return out
    for path in paths:
        try:
            data = read_json(path, None)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        dictionary = PronunciationDictionary.from_dict(data)
        dictionary.scope = scope  # the location it was found in is authoritative
        if not dictionary.id:
            dictionary.id = path.stem
        out.append(dictionary)
    return out


def load_dictionaries(project_dir: Path | None = None) -> list[PronunciationDictionary]:
    """All stored dictionaries: globals always, plus the project's when given."""
    dictionaries = _load_from(global_dir(), "global")
    if project_dir is not None:
        dictionaries.extend(_load_from(project_dir_for(project_dir), "project"))
    return dictionaries


def save_dictionary(dictionary: PronunciationDictionary, project_dir: Path | None = None) -> Path:
    """Write ``dictionary`` to its scope's location and return the path."""
    if dictionary.scope == "project":
        if project_dir is None:
            raise ValueError("a project-scoped dictionary needs a project_dir to save")
        folder = project_dir_for(project_dir)
    else:
        folder = global_dir()
    path = folder / f"{dictionary.id}.json"
    write_json_atomic(path, dictionary.to_dict())
    return path


def delete_dictionary(dictionary: PronunciationDictionary, project_dir: Path | None = None) -> None:
    folder = (
        project_dir_for(project_dir)
        if dictionary.scope == "project" and project_dir is not None
        else global_dir()
    )
    (folder / f"{dictionary.id}.json").unlink(missing_ok=True)


STARTER_DICTIONARY_ID = "starter"


def starter_dictionary() -> PronunciationDictionary:
    """A small bundled global dictionary of commonly-mangled terms (§4.7.6).

    A starting point users can enable, edit, or remove. Respellings are
    engine-agnostic so they work on every synthesizer.
    """
    pairs = [
        ("QUILL", "kwill", "product name"),
        ("GIF", "jiff", ""),
        ("SQL", "sequel", ""),
        ("GUI", "gooey", ""),
        ("PyPI", "pie pee eye", ""),
        ("GitHub", "git hub", ""),
        ("NVDA", "N V D A", "screen reader"),
        ("JAWS", "jaws", "screen reader"),
        ("API", "A P I", ""),
        ("URL", "U R L", ""),
        ("JSON", "jay son", ""),
        ("OAuth", "oh auth", ""),
        ("cache", "cash", ""),
    ]
    return PronunciationDictionary(
        id=STARTER_DICTIONARY_ID,
        name="QUILL starter pronunciations",
        scope="global",
        engine=None,
        enabled=True,
        entries=[
            PronunciationEntry(term=term, replacement=say, note=note) for term, say, note in pairs
        ],
    )


def install_starter_dictionary(*, overwrite: bool = False) -> bool:
    """Write the starter dictionary to the global store. Return True if written.

    Skips writing when a ``starter.json`` already exists (so a user's edits or
    deliberate removal are respected) unless ``overwrite`` is set. Safe to call
    from onboarding or a "restore starter pronunciations" action.
    """
    path = global_dir() / f"{STARTER_DICTIONARY_ID}.json"
    if path.exists() and not overwrite:
        return False
    save_dictionary(starter_dictionary())
    return True


def active_dictionaries(
    engine: str,
    *,
    project_dir: Path | None = None,
    enabled_ids: set[str] | None = None,
    language: str | None = None,
) -> list[PronunciationDictionary]:
    """Enabled, in-scope dictionaries for ``(engine, project)``, most specific first.

    A dictionary participates when its engine is ``None`` or matches ``engine``,
    and when it is enabled. ``enabled_ids`` (the per-user selection from settings)
    is authoritative when given; otherwise the dictionary's own ``enabled`` flag
    is used. When ``language`` is given (the translated-export path), a
    language-scoped dictionary participates only if it applies to that language;
    ``None`` (the default) applies no language filter, preserving prior behavior.
    """
    out: list[PronunciationDictionary] = []
    for dictionary in load_dictionaries(project_dir):
        if dictionary.engine is not None and dictionary.engine != engine:
            continue
        if language is not None and not dictionary.applies_to_language(language):
            continue
        is_on = (dictionary.id in enabled_ids) if enabled_ids is not None else dictionary.enabled
        if not is_on:
            continue
        out.append(dictionary)
    out.sort(key=lambda d: d.specificity(), reverse=True)
    return out


# ----------------------------------------------------------------------------
# Substitution
# ----------------------------------------------------------------------------


def _spoken_form(entry: PronunciationEntry) -> str | None:
    """The text to substitute, or None to skip (e.g. markup with no fallback).

    Respelling substitutes its replacement directly. Phoneme/SSML entries degrade
    to ``plain_fallback`` so raw markup is never read aloud (native rendering is
    Phase 6); without a fallback they are skipped rather than spoken literally.
    """
    if entry.mode == "respelling":
        return entry.replacement
    return entry.plain_fallback or None


def _compile(entry: PronunciationEntry) -> re.Pattern[str] | None:
    flags = 0 if entry.case_sensitive else re.IGNORECASE
    pattern = entry.term if entry.regex else re.escape(entry.term)
    if entry.whole_word and not entry.regex:
        pattern = rf"\b{pattern}\b"
    try:
        return re.compile(pattern, flags)
    except re.error:
        return None


def apply_pronunciations(
    text: str, engine: str, dictionaries: list[PronunciationDictionary]
) -> PronunciationResult:
    """Apply ``dictionaries`` (active set) to ``text`` for ``engine`` (§4.7.3).

    ``dictionaries`` should be the resolved active set (e.g. from
    :func:`active_dictionaries`); it is treated as ordered most-specific-first.
    On a term conflict the most specific dictionary wins; ties keep earlier
    entries. Matching is longest-term-first so a longer phrase wins over a
    shorter contained one.
    """
    if not text:
        return PronunciationResult(text=text)

    # Collect enabled entries, deduping by (case-folded) term so the most specific
    # dictionary's entry for a term wins. ``dictionaries`` is most-specific-first.
    chosen: dict[str, PronunciationEntry] = {}
    for dictionary in dictionaries:
        for entry in dictionary.entries:
            if not entry.enabled or not entry.term.strip():
                continue
            key = entry.term if entry.case_sensitive else entry.term.casefold()
            chosen.setdefault(key, entry)

    # Collect every match span against the ORIGINAL text (never re-scanning a
    # substituted replacement — that is the "New York" → "noo york" → "noo yorrk"
    # trap), then resolve overlaps greedily left-to-right, longest match first at a
    # tie. This yields longest-term-first semantics deterministically.
    #
    # Each match carries both a *plain* payload (spoken on any engine) and an
    # optional raw *ssml* fragment (only when the engine speaks SSML), so the same
    # match set renders either way (§4.7.8).
    ssml_capable = engine_supports_ssml(engine)
    matches: list[tuple[int, int, str, str | None, str]] = []  # start,end,plain,ssml,term
    for entry in chosen.values():
        plain = _spoken_form(entry)
        ssml = entry.replacement if (entry.mode == "ssml" and ssml_capable) else None
        if plain is None and ssml is None:
            continue
        pattern = _compile(entry)
        if pattern is None:
            continue
        for found in pattern.finditer(text):
            if found.end() > found.start():  # skip zero-width matches
                matches.append((found.start(), found.end(), plain or "", ssml, entry.term))

    matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))
    selected: list[tuple[int, int, str, str | None, str]] = []
    applied: dict[str, int] = {}
    cursor = 0
    for match in matches:
        start, end, _plain, _ssml, term = match
        if start < cursor:
            continue  # overlaps an already-applied match
        selected.append(match)
        applied[term] = applied.get(term, 0) + 1
        cursor = end

    use_ssml = ssml_capable and any(ssml for _s, _e, _p, ssml, _t in selected)
    if use_ssml:
        inner: list[str] = []
        cursor = 0
        for start, end, plain, ssml, _term in selected:
            inner.append(_xml_escape(text[cursor:start]))
            inner.append(ssml if ssml is not None else _xml_escape(plain or text[start:end]))
            cursor = end
        inner.append(_xml_escape(text[cursor:]))
        body = "".join(inner)
        if validate_ssml_fragment(body):
            return PronunciationResult(text=assemble_ssml(body), is_ssml=True, applied=applied)
        # Malformed assembly: fall through to plain rendering for this utterance.

    parts: list[str] = []
    cursor = 0
    for start, end, plain, _ssml, _term in selected:
        parts.append(text[cursor:start])
        parts.append(plain if plain else text[start:end])
        cursor = end
    parts.append(text[cursor:])
    return PronunciationResult(text="".join(parts), is_ssml=False, applied=applied)


# ----------------------------------------------------------------------------
# SSML authoring (§4.7.8-§4.7.9)
# ----------------------------------------------------------------------------

#: Engines that can speak SSML markup. Others use an entry's ``plain_fallback``.
SSML_CAPABLE_ENGINES: frozenset[str] = frozenset({"sapi5", "espeak"})


def engine_supports_ssml(engine: str) -> bool:
    return engine.strip().lower() in SSML_CAPABLE_ENGINES


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def validate_ssml_fragment(fragment: str) -> bool:
    """True when *fragment* is well-formed XML (as the body of a ``<speak>``).

    Wraps the fragment so a bare ``<phoneme .../>`` or text-with-tags validates.
    Rejects empty input and malformed markup. No external entities are expanded.
    """
    if not fragment.strip():
        return False
    from quill.core import safe_xml

    try:
        safe_xml.fromstring(f"<speak>{fragment}</speak>")
    except safe_xml.ParseError:
        return False
    return True


def assemble_ssml(fragment: str) -> str:
    """Wrap a (validated) fragment as a complete ``<speak>`` utterance."""
    return f"<speak>{fragment}</speak>"


def ssml_phoneme(term: str, ipa: str) -> str:
    """An IPA phoneme fragment: speak *term* using the *ipa* pronunciation."""
    return f'<phoneme alphabet="ipa" ph="{_xml_escape(ipa)}">{_xml_escape(term)}</phoneme>'


def ssml_sub(term: str, alias: str) -> str:
    """A substitution fragment: say *alias* in place of *term*."""
    return f'<sub alias="{_xml_escape(alias)}">{_xml_escape(term)}</sub>'


def ssml_say_as(term: str, interpret_as: str) -> str:
    """A say-as fragment (e.g. ``characters``, ``digits``, ``date``)."""
    return f'<say-as interpret-as="{_xml_escape(interpret_as)}">{_xml_escape(term)}</say-as>'


def ssml_break(milliseconds: int) -> str:
    """A pause fragment of *milliseconds*."""
    return f'<break time="{max(0, int(milliseconds))}ms"/>'


def ssml_prosody(term: str, *, rate: str = "", pitch: str = "") -> str:
    """A prosody fragment adjusting *rate* and/or *pitch* of *term*."""
    attrs = ""
    if rate:
        attrs += f' rate="{_xml_escape(rate)}"'
    if pitch:
        attrs += f' pitch="{_xml_escape(pitch)}"'
    return f"<prosody{attrs}>{_xml_escape(term)}</prosody>"
