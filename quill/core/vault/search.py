"""Vault-wide search and the quick switcher (Accessible Vault, Phase 3).

wx-free, strict-typed core for two surfaces the UI dresses as accessible dialogs:

- :func:`search_vault` — full-text search across every note's raw text, returning an
  ordered list of :class:`SearchHit` (note title + relative path + 1-based line number
  + the matching line + a snippet). Supports plain / regex / whole-word matching and
  "search within results" (restrict to a set of paths). Results are ranked title-hits
  first, then by path, so the accessible results list reads most-relevant first.
- :func:`quick_switch_matches` — a forgiving fuzzy filter of note titles and aliases
  for the name-jump quick switcher, ordered best-match first.

The heavier `ripgrep`-backed scan is a UI-layer optimization for very large vaults; this
in-process implementation is the always-available, unit-tested foundation and the exact
behaviour the ripgrep path must match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.vault.vault import Vault


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One matching line in one note."""

    path: str
    title: str
    line_number: int  # 1-based, for "open at the matching line"
    line: str  # the full matching line (stripped of trailing newline)
    snippet: str  # a short, match-centered excerpt for the spoken results list
    start: int  # match start column within ``line`` (0-based)
    end: int  # match end column within ``line``

    def announce(self) -> str:
        """Screen-reader-friendly one-line summary of the hit."""
        return f"{self.title}, line {self.line_number}: {self.snippet}"


@dataclass(frozen=True, slots=True)
class SwitchMatch:
    """One note matched by the quick switcher, with its fuzzy score."""

    path: str
    title: str
    score: int  # higher is better


def _compile(query: str, *, regex: bool, whole_word: bool) -> re.Pattern[str] | None:
    """Compile ``query`` to a case-insensitive pattern, or ``None`` if it is invalid/empty."""
    text = query.strip()
    if not text:
        return None
    pattern = text if regex else re.escape(text)
    if whole_word:
        pattern = rf"\b{pattern}\b"
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None


def _snippet(line: str, start: int, end: int, *, width: int = 80) -> str:
    """A match-centered excerpt of ``line``, with ellipses when trimmed."""
    if len(line) <= width:
        return line.strip()
    match_len = end - start
    pad = max(0, (width - match_len) // 2)
    lo = max(0, start - pad)
    hi = min(len(line), end + pad)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(line) else ""
    return f"{prefix}{line[lo:hi].strip()}{suffix}"


def search_vault(
    vault: Vault,
    query: str,
    *,
    regex: bool = False,
    whole_word: bool = False,
    within_paths: set[str] | None = None,
) -> list[SearchHit]:
    """Return every matching line across the vault, most-relevant first.

    ``within_paths`` restricts the scan to those note paths ("search within results").
    A note whose *title* matches ranks above notes matched only in the body; within a
    tier, notes are ordered by path and hits by line number, so the list is stable and
    reads predictably. An empty/invalid query yields no hits (never an error).
    """
    matcher = _compile(query, regex=regex, whole_word=whole_word)
    if matcher is None:
        return []

    title_tier: list[SearchHit] = []
    body_tier: list[SearchHit] = []
    for path in sorted(vault.texts):
        if within_paths is not None and path not in within_paths:
            continue
        note = vault.notes.get(path)
        title = note.title if note is not None else path
        title_hit = bool(matcher.search(title))
        bucket = title_tier if title_hit else body_tier
        for line_index, raw_line in enumerate(vault.texts[path].splitlines()):
            match = matcher.search(raw_line)
            if match is None:
                continue
            bucket.append(
                SearchHit(
                    path=path,
                    title=title,
                    line_number=line_index + 1,
                    line=raw_line,
                    snippet=_snippet(raw_line, match.start(), match.end()),
                    start=match.start(),
                    end=match.end(),
                )
            )
    return title_tier + body_tier


def _fuzzy_score(query: str, candidate: str) -> int | None:
    """Subsequence fuzzy score, or ``None`` when ``query`` is not a subsequence.

    Rewards contiguous runs and an early first match, so "int" scores higher on
    "Introduction" than on "Print Layout". Case-insensitive.
    """
    if not query:
        return 0
    q = query.lower()
    c = candidate.lower()
    score = 0
    run = 0
    ci = 0
    first_index: int | None = None
    for ch in q:
        found = c.find(ch, ci)
        if found == -1:
            return None
        if first_index is None:
            first_index = found
        run = run + 1 if found == ci else 1
        score += run  # contiguous matches compound
        ci = found + 1
    # Earlier first match is better; shorter candidates are better tiebreaks.
    score = score * 100 - (first_index or 0) * 3 - len(candidate)
    return score


def quick_switch_matches(vault: Vault, query: str, *, limit: int = 50) -> list[SwitchMatch]:
    """Fuzzy-match note titles/aliases for the quick switcher, best first.

    An empty query returns every note ordered by title (the full browse list). Each note
    is scored by the best of its title and aliases; ties break by title then path so the
    order is deterministic. ``limit`` caps the returned list.
    """
    scored: list[SwitchMatch] = []
    for path, note in vault.notes.items():
        candidates = (note.title, *note.aliases)
        best: int | None = None
        for candidate in candidates:
            s = _fuzzy_score(query, candidate)
            if s is not None and (best is None or s > best):
                best = s
        if best is not None:
            scored.append(SwitchMatch(path=path, title=note.title, score=best))
    scored.sort(key=lambda m: (-m.score, m.title.lower(), m.path))
    return scored[:limit]
