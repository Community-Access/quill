"""Capture routing rules (PRD 14.5): keyword -> folder, first match wins.

A user-ordered list of rules, each mapping one keyword (a domain name or any
substring a URL could contain) to one collection. When a web bookmark is
captured without an explicitly chosen collection, the first rule whose keyword
appears in the URL files the bookmark into that rule's collection. The Inbox
flag is untouched, so a routed bookmark still shows up for review.

One keyword maps to one folder: keywords are unique case-insensitively across
the list. Rules live in ``routing.json`` next to the database, following the
same fail-safe load/save pattern as ``a11y.py`` and ``external_player.py``.
wx-free and unit-testable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from quill.apps.beacon.model import TYPE_WEB, TYPE_WEB_HEADING, TYPE_WEB_PASSAGE

SETTINGS_FILE = "routing.json"

# Routing applies to web-based bookmarks only; files, podcasts, radio, and
# generic URIs keep their capture-time collections.
_WEB_TYPES = (TYPE_WEB, TYPE_WEB_HEADING, TYPE_WEB_PASSAGE)


@dataclass
class Rule:
    """One routing rule: a URL keyword and the collection it files into."""

    keyword: str
    collection: str

    def to_dict(self) -> dict:
        return {"keyword": self.keyword, "collection": self.collection}

    @classmethod
    def from_dict(cls, d: dict) -> Rule:
        return cls(keyword=str(d.get("keyword") or ""), collection=str(d.get("collection") or ""))


def validate(rules: list[Rule]) -> str | None:
    """Return an error message for a bad rule list, or None if it is valid."""
    seen: set[str] = set()
    for rule in rules:
        kw = rule.keyword.strip().lower()
        if not kw:
            return "A rule needs a keyword."
        if not rule.collection.strip():
            return f"Rule '{rule.keyword}' needs a folder."
        if kw in seen:
            return f"Keyword '{rule.keyword}' is already used by another rule."
        seen.add(kw)
    return None


def load_rules(data_dir) -> list[Rule]:
    """Load rules from the data dir; empty list if missing or corrupt.

    A hand-edited file that reuses a keyword keeps the first rule and drops
    the rest, preserving the one-keyword-one-folder invariant.
    """
    path = os.path.join(str(data_dir), SETTINGS_FILE)
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, ValueError, OSError):
        return []
    rules: list[Rule] = []
    seen: set[str] = set()
    for item in (raw.get("rules") or []) if isinstance(raw, dict) else []:
        rule = Rule.from_dict(item)
        kw = rule.keyword.strip().lower()
        if not kw or not rule.collection.strip() or kw in seen:
            continue
        seen.add(kw)
        rules.append(rule)
    return rules


def save_rules(data_dir, rules: list[Rule]) -> None:
    """Persist rules in priority order. Raises ValueError on an invalid list."""
    error = validate(rules)
    if error:
        raise ValueError(error)
    path = os.path.join(str(data_dir), SETTINGS_FILE)
    os.makedirs(str(data_dir), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"rules": [r.to_dict() for r in rules]}, fh, indent=2, ensure_ascii=False)


def match_collection(url: str, rules: list[Rule]) -> str | None:
    """Return the collection of the first rule whose keyword is in ``url``.

    Matching is a case-insensitive substring test, so a keyword can be a
    domain (``github.com``) or any URL fragment (``/recipes/``). List order
    is priority: first match wins.
    """
    if not url:
        return None
    haystack = url.lower()
    for rule in rules:
        if rule.keyword.strip().lower() in haystack:
            return rule.collection
    return None


def route(beacon, resource, rules: list[Rule]) -> str | None:
    """File a freshly captured web beacon by rule; return the folder or None.

    Does nothing when the resource is not web-based, when the caller already
    chose a collection (an explicit choice always wins), or when no rule
    matches. The Inbox flag is never changed.
    """
    if not rules or beacon.collections:
        return None
    if resource is None or resource.type not in _WEB_TYPES:
        return None
    url = resource.canonical_id or resource.primary_uri or ""
    collection = match_collection(url, rules)
    if collection is None and resource.primary_uri and resource.primary_uri != url:
        collection = match_collection(resource.primary_uri, rules)
    if collection:
        beacon.collections = [collection]
    return collection
