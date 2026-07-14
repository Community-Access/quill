"""Lightweight, deterministic source-language detection (#181 follow-up).

A wx-free content classifier that guesses which programming/markup language a
buffer is written in — so QUILL can suggest (or auto-apply) a Document Language
when you paste code into a plain ``.txt``/untitled file.

Design goals, borrowed from VS Code's detector (``languageDetectionWebWorker``)
but **without** its TensorFlow model:

- **No ML, no dependencies.** QUILL only needs to tell apart the ~16 languages it
  has profiles for, which structural heuristics handle well and instantly.
- **Confidence discipline.** Every candidate gets a score from weighted signals;
  the winner must clear an absolute floor *and* a relative margin over the runner
  up, or we report "no idea" (``language=None``) rather than guess.
- **Ambiguity penalties.** Simple, easily-confused grammars (YAML, TOML, SQL,
  INI-like) are penalised so plain prose or a stray ``key: value`` doesn't trip a
  false positive — the single biggest source of bad guesses.
- **History bias.** Callers may pass a ``bias`` map (languages used this session)
  to nudge ties toward what the user actually edits.
- **Hysteresis.** :func:`should_switch` requires a higher bar to *change* an
  already-detected language than to set the first, so detection doesn't flip-flop
  while you type.

The result maps to a :class:`~quill.core.language_profile.LanguageProfile` name,
so a detection feeds straight into ``set_document_language``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Profile names this detector can return (must match language_profile names).
HTML = "HTML"
MARKDOWN = "Markdown"
JSON_ = "JSON"
YAML = "YAML"
TOML = "TOML"
PYTHON = "Python"
JAVASCRIPT = "JavaScript"
TYPESCRIPT = "TypeScript"
CSS = "CSS"
GO = "Go"
C = "C"
CPP = "C++"
RUST = "Rust"
KOTLIN = "Kotlin"
SHELL = "Shell"
SQL = "SQL"
CSHARP = "C#"
PHP = "PHP"

# Languages VS Code (and experience) finds reliable vs. easily confused. Applied
# as multipliers after scoring so a weak signal in an ambiguous language loses to
# a comparable signal in a distinctive one.
_BOOST = {HTML, MARKDOWN, PYTHON, JAVASCRIPT, TYPESCRIPT, JSON_, CSS, CSHARP, PHP}
_PENALTY = {YAML, TOML, SQL}
_BOOST_FACTOR = 1.15
_PENALTY_FACTOR = 0.6

_DEFAULT_SAMPLE_LIMIT = 10_000
_DEFAULT_MIN_CONFIDENCE = 0.35
_RELATIVE_MARGIN = 0.12  # winner must beat runner-up share by this much
_ABSOLUTE_FLOOR = 2.5  # minimum raw score; below this the text is "plain"


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Outcome of a detection pass."""

    language: str | None
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)
    runner_up: str | None = None
    sampled_chars: int = 0

    @property
    def is_confident(self) -> bool:
        return self.language is not None


@dataclass(frozen=True, slots=True)
class _Rule:
    """One weighted signal: count regex hits (capped) and add to ``lang``'s score."""

    lang: str
    weight: float
    pattern: re.Pattern[str]
    per_line: bool = False  # count matching lines rather than total matches
    cap: int = 6  # cap the count so one giant file can't saturate a signal


def _c(pattern: str, flags: int = 0) -> re.Pattern[str]:
    return re.compile(pattern, flags)


# Signal table. Kept declarative so languages are easy to tune/extend. Weights are
# relative; distinctive signals (shebangs, doctype, fenced code) weigh more than
# generic ones (a brace, a colon).
_RULES: tuple[_Rule, ...] = (
    # --- HTML --------------------------------------------------------------
    _Rule(HTML, 6.0, _c(r"<!doctype html", re.IGNORECASE), cap=1),
    _Rule(HTML, 2.0, _c(r"</[a-zA-Z][\w-]*>")),
    _Rule(HTML, 1.2, _c(r"<[a-zA-Z][\w-]*(\s[^<>]*)?>")),
    _Rule(HTML, 2.5, _c(r"<(html|head|body|div|span|section|article|nav|footer)\b", re.I)),
    # --- Markdown ----------------------------------------------------------
    _Rule(MARKDOWN, 2.5, _c(r"^\s{0,3}#{1,6}\s+\S", re.M), per_line=True),
    _Rule(MARKDOWN, 3.0, _c(r"^\s*```", re.M), per_line=True),
    _Rule(MARKDOWN, 1.5, _c(r"^\s{0,3}[-*+]\s+\S", re.M), per_line=True),
    _Rule(MARKDOWN, 2.0, _c(r"\[[^\]]+\]\([^)]+\)")),
    _Rule(MARKDOWN, 1.2, _c(r"^\s*>\s+\S", re.M), per_line=True),
    _Rule(MARKDOWN, 1.5, _c(r"\*\*[^*]+\*\*|__[^_]+__")),
    # --- YAML --------------------------------------------------------------
    _Rule(YAML, 3.0, _c(r"^---\s*$", re.M), per_line=True, cap=2),
    _Rule(YAML, 1.0, _c(r"^[A-Za-z_][\w-]*:\s+\S", re.M), per_line=True),
    _Rule(YAML, 0.8, _c(r"^\s*-\s+\S", re.M), per_line=True),
    # --- TOML --------------------------------------------------------------
    _Rule(TOML, 3.0, _c(r"^\[[\w.\-\"]+\]\s*$", re.M), per_line=True),
    _Rule(TOML, 1.2, _c(r"^[A-Za-z_][\w-]*\s*=\s*\S", re.M), per_line=True),
    # --- Python ------------------------------------------------------------
    _Rule(PYTHON, 6.0, _c(r"^#!.*\bpython", re.M), cap=1),
    _Rule(PYTHON, 2.5, _c(r"^\s*def\s+\w+\s*\(", re.M), per_line=True),
    _Rule(PYTHON, 2.5, _c(r"^\s*class\s+\w+", re.M), per_line=True),
    _Rule(PYTHON, 1.8, _c(r"^\s*(from\s+[\w.]+\s+)?import\s+\w", re.M), per_line=True),
    _Rule(
        PYTHON,
        1.5,
        _c(r"^\s*(if|for|while|with|elif|else|try|except)\b.*:\s*$", re.M),
        per_line=True,
    ),
    _Rule(PYTHON, 1.0, _c(r"\bself\b|\bprint\s*\(|\bNone\b|\bTrue\b|\bFalse\b")),
    # --- JavaScript --------------------------------------------------------
    _Rule(JAVASCRIPT, 2.0, _c(r"\b(const|let|var)\s+\w+\s*=")),
    _Rule(JAVASCRIPT, 2.0, _c(r"\bfunction\s*\*?\s*\w*\s*\(")),
    _Rule(JAVASCRIPT, 1.5, _c(r"=>")),
    _Rule(JAVASCRIPT, 2.0, _c(r"\b(console\.log|require\s*\(|module\.exports)")),
    _Rule(JAVASCRIPT, 1.5, _c(r"\bimport\s+.*\bfrom\s+['\"]")),
    # --- TypeScript (JS-ish plus types) ------------------------------------
    _Rule(TYPESCRIPT, 3.0, _c(r"\b(interface|enum|type)\s+\w+")),
    _Rule(TYPESCRIPT, 2.0, _c(r":\s*(string|number|boolean|any|void|unknown)\b")),
    _Rule(TYPESCRIPT, 2.0, _c(r"\b(public|private|readonly)\s+\w+\s*:")),
    _Rule(TYPESCRIPT, 1.5, _c(r"\bas\s+\w+|<[A-Z]\w*>")),
    # --- CSS ---------------------------------------------------------------
    _Rule(CSS, 2.5, _c(r"[.#]?[\w-]+\s*\{[^}]*\}", re.S)),
    _Rule(CSS, 1.5, _c(r"^[\s]*[\w-]+\s*:\s*[^;{}]+;", re.M), per_line=True),
    _Rule(CSS, 3.0, _c(r"@(media|import|keyframes|font-face)\b")),
    # --- Go ----------------------------------------------------------------
    _Rule(GO, 6.0, _c(r"^package\s+\w+", re.M), cap=1),
    _Rule(GO, 2.5, _c(r"\bfunc\s+\w*\s*\(")),
    _Rule(GO, 2.0, _c(r":=")),
    _Rule(GO, 2.0, _c(r"\bfmt\.\w+|\bimport\s*\(")),
    # --- Rust --------------------------------------------------------------
    _Rule(RUST, 3.0, _c(r"\bfn\s+\w+\s*\(")),
    _Rule(RUST, 2.5, _c(r"\blet\s+mut\b|\bpub\s+fn\b|\bimpl\b|\buse\s+\w+::")),
    _Rule(RUST, 1.5, _c(r"->\s*\w+|::\w+|\bmatch\s+\w")),
    _Rule(RUST, 2.5, _c(r"println!\s*\(|\bResult<|\bOption<")),
    # --- C / C++ -----------------------------------------------------------
    _Rule(C, 3.0, _c(r"^#include\s*[<\"]", re.M), per_line=True),
    _Rule(C, 2.0, _c(r"\bint\s+main\s*\(")),
    _Rule(C, 1.2, _c(r"\b(printf|scanf|malloc|sizeof)\s*\(")),
    _Rule(CPP, 4.0, _c(r"#include\s*<(iostream|vector|string|map)>")),
    _Rule(CPP, 3.0, _c(r"\bstd::\w+|\b(cout|cin)\b|template\s*<")),
    _Rule(CPP, 2.0, _c(r"\bnamespace\s+\w+|\bclass\s+\w+")),
    # --- Kotlin ------------------------------------------------------------
    _Rule(KOTLIN, 3.0, _c(r"\bfun\s+\w+\s*\(")),
    _Rule(KOTLIN, 2.0, _c(r"\b(val|var)\s+\w+\s*(:\s*\w+)?\s*=")),
    _Rule(KOTLIN, 2.0, _c(r"\bwhen\s*\(|println\s*\(|\.kt\b")),
    # --- Shell -------------------------------------------------------------
    _Rule(SHELL, 6.0, _c(r"^#!.*\b(bash|sh|zsh)\b", re.M), cap=1),
    _Rule(SHELL, 2.0, _c(r"^\s*(if|for|while)\b.*;\s*then\b", re.M), per_line=True),
    _Rule(SHELL, 2.0, _c(r"\b(fi|esac|done)\b")),
    _Rule(SHELL, 1.5, _c(r"\$\{?\w+\}?|\becho\s+")),
    # --- C# ----------------------------------------------------------------
    _Rule(CSHARP, 3.0, _c(r"\busing\s+System\b|\bnamespace\s+\w+")),
    _Rule(
        CSHARP, 2.5, _c(r"\b(public|private|protected|internal)\s+(static\s+)?(class|void|async)\b")
    ),
    _Rule(CSHARP, 2.0, _c(r"\bConsole\.(Write|WriteLine)\s*\(|\bvar\s+\w+\s*=")),
    _Rule(CSHARP, 1.5, _c(r"\b(get;|set;)|\bstring\[\]\s+args")),
    # --- PHP ---------------------------------------------------------------
    _Rule(PHP, 6.0, _c(r"<\?php\b"), cap=2),
    _Rule(PHP, 2.5, _c(r"\$\w+\s*=|\$this->|\becho\s+")),
    _Rule(PHP, 2.0, _c(r"\bfunction\s+\w+\s*\(.*\)\s*\{|->\w+\s*\(")),
    _Rule(PHP, 1.5, _c(r"\b(namespace|use|require|include)\b\s|\bpublic\s+function\b")),
    # --- SQL ---------------------------------------------------------------
    _Rule(
        SQL,
        2.0,
        _c(r"\b(select|insert\s+into|update|delete\s+from|create\s+table|alter\s+table)\b", re.I),
    ),
    _Rule(SQL, 1.5, _c(r"\b(from|where|join|group\s+by|order\s+by|having)\b", re.I)),
)


def _looks_like_json(sample: str) -> float:
    """A strong, near-unambiguous JSON signal: the sample parses as JSON."""
    stripped = sample.strip()
    if not stripped or stripped[0] not in "{[":
        return 0.0
    try:
        json.loads(stripped)
    except (ValueError, RecursionError):
        # Partial paste: still reward object/array + quoted keys.
        if re.search(r'"[^"]+"\s*:', stripped) and stripped[0] in "{[":
            return 4.0
        return 0.0
    return 10.0


def _raw_scores(sample: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for rule in _RULES:
        if rule.per_line:
            count = sum(1 for _ in rule.pattern.finditer(sample))
        else:
            count = len(rule.pattern.findall(sample))
        if count:
            scores[rule.lang] = scores.get(rule.lang, 0.0) + rule.weight * min(count, rule.cap)
    json_score = _looks_like_json(sample)
    if json_score:
        scores[JSON_] = scores.get(JSON_, 0.0) + json_score
    return scores


def detect_language(
    text: str,
    *,
    bias: dict[str, float] | None = None,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
    sample_limit: int = _DEFAULT_SAMPLE_LIMIT,
) -> DetectionResult:
    """Guess the language of ``text``.

    Returns a :class:`DetectionResult`; ``language`` is None when nothing clears
    the confidence bar (treat as plain text). ``bias`` optionally adds a small
    per-language nudge (e.g. languages used this session).
    """
    sample = text[:sample_limit]
    scores = _raw_scores(sample)
    if bias:
        for lang, amount in bias.items():
            if lang in scores:
                scores[lang] += max(0.0, amount)
    # Confidence corrections: lift distinctive languages, damp ambiguous ones.
    for lang in list(scores):
        if lang in _BOOST:
            scores[lang] *= _BOOST_FACTOR
        elif lang in _PENALTY:
            scores[lang] *= _PENALTY_FACTOR

    if not scores:
        return DetectionResult(None, 0.0, {}, None, len(sample))

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_lang, top_raw = ranked[0]
    runner_up, runner_raw = ranked[1] if len(ranked) > 1 else (None, 0.0)
    total = sum(scores.values())
    confidence = top_raw / total if total > 0 else 0.0
    runner_share = runner_raw / total if total > 0 else 0.0

    # Normalised scores for callers/telemetry.
    normalised = {lang: raw / total for lang, raw in scores.items()} if total else {}

    decided = (
        top_raw >= _ABSOLUTE_FLOOR
        and confidence >= min_confidence
        and (confidence - runner_share) >= _RELATIVE_MARGIN
    )
    return DetectionResult(
        language=top_lang if decided else None,
        confidence=confidence,
        scores=normalised,
        runner_up=runner_up,
        sampled_chars=len(sample),
    )


def should_switch(
    current: str | None,
    result: DetectionResult,
    *,
    change_margin: float = 0.15,
) -> bool:
    """Hysteresis gate: should a live editor adopt ``result``?

    Setting a language for the first time only needs ``result.is_confident``.
    *Changing* an already-detected language additionally requires the new
    confidence to clear ``min_confidence + change_margin``, so detection does not
    oscillate while the user types or pastes incrementally.
    """
    if not result.is_confident or result.language is None:
        return False
    if current is None or current == "Plain text":
        return True
    if result.language == current:
        return False
    return result.confidence >= (_DEFAULT_MIN_CONFIDENCE + change_margin)
