"""Intelligent assistance -- local heuristics, no AI required (PRD 47, Phase 5).

Three opt-in, on-device assists that run without any model or network call:

- :func:`suggest_tags` -- term-frequency tag suggestions from a beacon's text.
- :func:`extractive_summary` -- a few highest-scoring sentences, in order.
- :func:`suggest_relationships` -- other beacons that share tags, collections,
  or domain with the given one.

A fourth, :func:`semantic_search`, is an **opt-in hook**: it returns nothing
by default (no model) but defines the :class:`SemanticIndex` protocol an
external embedding model implements. Nothing here fetches a model or calls the
network; the hook is the documented seam where one would plug in (PRD 47.4).

All pure logic over text and the store; wx-free and unit-testable.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Protocol, runtime_checkable

# A small, generic English stopword list. Kept short so domain terms survive.
_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "from",
    "by",
    "at",
    "into",
    "you",
    "your",
    "i",
    "we",
    "they",
    "he",
    "she",
    "his",
    "her",
    "their",
    "not",
    "no",
    "so",
    "than",
    "too",
    "very",
    "can",
    "will",
    "just",
    "about",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9']{2,}")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "") if w.lower() not in _STOPWORDS]


def suggest_tags(text: str, *, existing: list[str] | None = None, limit: int = 5) -> list[str]:
    """Suggest tags by term frequency, excluding ones already present.

    Single-pass TF over the text, stopword-filtered. Existing tags (compared
    case-insensitively) are never re-suggested. Returns lowercase tags.
    """
    existing = existing or []
    existing_lower = {t.lower() for t in existing}
    counts = Counter(_tokens(text))
    out: list[str] = []
    for word, _n in counts.most_common():
        if word in existing_lower:
            continue
        out.append(word)
        if len(out) >= limit:
            break
    return out


def extractive_summary(text: str, *, max_sentences: int = 3) -> str:
    """Return up to ``max_sentences`` highest-scoring sentences, in order.

    Scores sentences by the summed frequency of their non-stopword words,
    normalized by length so a long sentence is not favored purely for length.
    Short text (fewer than two sentences) is returned unchanged.
    """
    text = (text or "").strip()
    if not text:
        return ""
    sentences = [s.strip() for s in _SENT_RE.split(text) if s.strip()]
    if len(sentences) <= max_sentences:
        return text
    freq = Counter(_tokens(text))
    scored = []
    for i, s in enumerate(sentences):
        toks = _tokens(s)
        if not toks:
            continue
        score = sum(freq[t] for t in toks) / len(toks)
        scored.append((score, i, s))
    scored.sort(key=lambda t: (-t[0], t[1]))
    picked = sorted(scored[:max_sentences], key=lambda t: t[1])
    return " ".join(s for _, _, s in picked)


def suggest_relationships(store, beacon_id: str, *, limit: int = 10) -> list[dict]:
    """Suggest related beacons by shared tags, collections, and domain.

    Scoring: shared tag = 3, shared collection = 2, same domain = 1. Returns a
    list of ``{"beacon_id", "title", "score", "reasons"}`` sorted by score.
    Excludes self, trashed, and already-related beacons.
    """
    b = store.get_beacon(beacon_id)
    if not b:
        return []
    my_tags = {t.lower() for t in b.tags}
    my_cols = {c.lower() for c in b.collections}
    res = store.get_resource(b.resource_id) if b.resource_id else None
    my_domain = _domain(res.primary_uri) if res else ""
    already = {r.tgt_beacon for r in store.relationships_for(beacon_id)}
    already.add(beacon_id)

    out: list[dict] = []
    for other in store.list_beacons(limit=1000):
        if other.beacon_id in already:
            continue
        reasons: list[str] = []
        score = 0
        shared_tags = my_tags & {t.lower() for t in other.tags}
        if shared_tags:
            score += 3 * len(shared_tags)
            reasons.append("tags: " + ", ".join(sorted(shared_tags)))
        shared_cols = my_cols & {c.lower() for c in other.collections}
        if shared_cols:
            score += 2 * len(shared_cols)
            reasons.append("collections: " + ", ".join(sorted(shared_cols)))
        ores = store.get_resource(other.resource_id) if other.resource_id else None
        odomain = _domain(ores.primary_uri) if ores else ""
        if my_domain and odomain and my_domain == odomain:
            score += 1
            reasons.append("same domain: " + my_domain)
        if score > 0:
            out.append({
                "beacon_id": other.beacon_id,
                "title": other.title,
                "score": score,
                "reasons": reasons,
            })
    out.sort(key=lambda r: (-r["score"], r["title"]))
    return out[:limit]


def _domain(url: str) -> str:
    m = re.match(r"https?://([^/]+)/?", url or "")
    return m.group(1).lower() if m else ""


@runtime_checkable
class SemanticIndex(Protocol):
    """Opt-in semantic search seam (PRD 47.4). No default implementation.

    An external embedding model implements this; the assist layer calls it
    only when one is registered. The framework ships no model and makes no
    network call -- this protocol is the documented plug-in point.
    """

    def search(self, query: str, *, limit: int = 20) -> list[tuple[str, float]]:
        """Return ``(beacon_id, score)`` pairs ranked by semantic similarity."""
        ...


class NoSemanticIndex:
    """Default no-op index: semantic search is off until a model is plugged in."""

    def search(self, query: str, *, limit: int = 20) -> list[tuple[str, float]]:
        return []


def semantic_search(
    store, query: str, *, index: SemanticIndex | None = None, limit: int = 20
) -> list[dict]:
    """Run semantic search if an index is registered, else return [].

    With no index (the default, no model), this returns an empty list -- the
    feature is opt-in and silent until the user turns it on (PRD 47.4). When an
    index is registered, results are joined back to live beacons so trashed or
    deleted ids are filtered out.
    """
    if index is None:
        return []
    results: list[dict] = []
    for beacon_id, score in index.search(query, limit=limit * 2):
        b = store.get_beacon(beacon_id)
        if not b or b.trashed:
            continue
        results.append({"beacon_id": beacon_id, "title": b.title, "score": float(score)})
        if len(results) >= limit:
            break
    return results
