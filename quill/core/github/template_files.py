"""The template chooser and the community files with fields of their own (GitHub PRD 21.3, 21.8).

- **The chooser** (``.github/ISSUE_TEMPLATE/config.yml``): whether blank
  issues are allowed and the contact links, read and written with any other
  key kept. GitHub orders templates by file name, so :func:`order_renames`
  turns an order into number-prefixed names ("01-bug.yml").
- **FUNDING.yml**: one value per sponsor platform.
- **CITATION.cff**: title, version, DOI, release date, message and authors.
- **CODEOWNERS**: rules of a path pattern and its owners, and
  :func:`owners_for`, which answers "who owns this path" the way GitHub does
  -- the last matching rule wins.

YAML is read with ``yaml.safe_load`` only. No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.template_builder import TemplateDraftError, TemplateProblem

__all__ = [
    "FUNDING_PLATFORMS",
    "ChooserConfig",
    "CodeownersRule",
    "check_chooser",
    "dump_chooser",
    "dump_citation",
    "dump_funding",
    "order_renames",
    "owners_for",
    "parse_chooser",
    "parse_citation",
    "parse_codeowners",
    "parse_funding",
]


def _yaml_mapping(text: str, what: str) -> dict[str, Any]:
    import yaml  # type: ignore[import-untyped]

    try:
        data = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError as exc:
        raise TemplateDraftError(f"{what} is not valid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TemplateDraftError(f"{what} is not a set of keys.")
    return dict(data)


def _dump(data: dict[str, Any]) -> str:
    import yaml

    return str(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=4096))


# -- the chooser ----------------------------------------------------------------


@dataclass
class ChooserConfig:
    blank_issues_enabled: bool = True
    #: Each ``{"name", "url", "about"}``, in order.
    contact_links: list[dict[str, str]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


def parse_chooser(text: str) -> ChooserConfig:
    data = _yaml_mapping(text, "The chooser")
    links = data.pop("contact_links", None) or []
    blank = data.pop("blank_issues_enabled", True)
    return ChooserConfig(
        blank_issues_enabled=blank is not False,
        contact_links=[
            {k: str(link.get(k) or "") for k in ("name", "url", "about")}
            for link in links
            if isinstance(link, dict)
        ],
        extra=data,
    )


def dump_chooser(config: ChooserConfig) -> str:
    data: dict[str, Any] = {"blank_issues_enabled": config.blank_issues_enabled}
    if config.contact_links:
        data["contact_links"] = [dict(link) for link in config.contact_links]
    data.update(config.extra)
    return _dump(data)


def check_chooser(config: ChooserConfig) -> list[TemplateProblem]:
    found: list[TemplateProblem] = []
    for position, link in enumerate(config.contact_links, 1):
        where = f"Contact link {position} ({link.get('name') or 'no name'})"
        for key in ("name", "url", "about"):
            if not link.get(key, "").strip():
                found.append(TemplateProblem(where, f"needs {key}"))
        if link.get("url") and not link["url"].startswith(("https://", "http://")):
            found.append(TemplateProblem(where, "the address must start with https://"))
    return found


_PREFIX = re.compile(r"^\d+[-_.]")


def order_renames(filenames: Sequence[str]) -> list[tuple[str, str]]:
    """``(old, new)`` names that make GitHub show *filenames* in this order."""
    renames: list[tuple[str, str]] = []
    for position, name in enumerate(filenames, 1):
        bare = _PREFIX.sub("", name)
        new = f"{position:02d}-{bare}"
        if new != name:
            renames.append((name, new))
    return renames


# -- FUNDING.yml ----------------------------------------------------------------

#: The sponsor platforms GitHub reads, in its documentation's order.
FUNDING_PLATFORMS: tuple[tuple[str, str], ...] = (
    ("github", "GitHub Sponsors usernames, separated by commas"),
    ("patreon", "Patreon username"),
    ("open_collective", "Open Collective username"),
    ("ko_fi", "Ko-fi username"),
    ("tidelift", "Tidelift platform-name/package-name"),
    ("community_bridge", "LFX Mentorship project name"),
    ("liberapay", "Liberapay username"),
    ("issuehunt", "IssueHunt username"),
    ("lfx_crowdfunding", "LFX Crowdfunding project name"),
    ("polar", "Polar username"),
    ("buy_me_a_coffee", "Buy Me a Coffee username"),
    ("thanks_dev", "thanks.dev username"),
    ("custom", "Other addresses, separated by commas"),
)
_LISTS = frozenset({"github", "custom"})


def parse_funding(text: str) -> dict[str, str]:
    """Each platform's value as text (lists joined with commas); other keys kept."""
    data = _yaml_mapping(text, "FUNDING.yml")
    return {
        key: ", ".join(str(v) for v in value) if isinstance(value, list) else str(value or "")
        for key, value in data.items()
    }


def dump_funding(values: dict[str, str]) -> str:
    data: dict[str, Any] = {}
    for key, value in values.items():
        value = value.strip()
        if not value:
            continue
        if key in _LISTS:
            parts = [part.strip() for part in value.split(",") if part.strip()]
            data[key] = parts if len(parts) > 1 or key == "custom" else parts[0]
        else:
            data[key] = value
    return _dump(data) if data else ""


# -- CITATION.cff ---------------------------------------------------------------

_CITATION_KEYS = ("title", "version", "doi", "date-released", "message")


def parse_citation(text: str) -> tuple[dict[str, str], list[str], dict[str, Any]]:
    """``(fields, authors as "Family, Given", every other key)``."""
    data = _yaml_mapping(text, "CITATION.cff")
    fields = {key: str(data.pop(key, "") or "") for key in _CITATION_KEYS}
    authors: list[str] = []
    for author in data.pop("authors", None) or []:
        if isinstance(author, dict):
            if author.get("name"):
                authors.append(str(author["name"]))
            else:
                family = str(author.get("family-names") or "")
                given = str(author.get("given-names") or "")
                authors.append(f"{family}, {given}".strip(", "))
    return fields, authors, data


def dump_citation(fields: dict[str, str], authors: Iterable[str], extra: dict[str, Any]) -> str:
    data: dict[str, Any] = {"cff-version": extra.get("cff-version", "1.2.0")}
    for key in _CITATION_KEYS:
        if fields.get(key, "").strip():
            data[key] = fields[key].strip()
    people: list[dict[str, str]] = []
    for line in authors:
        if not line.strip():
            continue
        family, comma, given = line.partition(",")
        if comma:
            people.append({"family-names": family.strip(), "given-names": given.strip()})
        else:
            people.append({"name": line.strip()})
    data["authors"] = people
    for key, value in extra.items():
        data.setdefault(key, value)
    return _dump(data)


# -- CODEOWNERS -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CodeownersRule:
    line: int
    pattern: str
    owners: tuple[str, ...]


def parse_codeowners(text: str) -> list[CodeownersRule]:
    rules: list[CodeownersRule] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        rules.append(CodeownersRule(number, pattern, tuple(owners)))
    return rules


def _pattern_regex(pattern: str) -> re.Pattern[str]:
    """GitHub's CODEOWNERS pattern (gitignore-like) as a regular expression."""
    anchored = pattern.startswith("/") or "/" in pattern.rstrip("/")
    body = pattern.strip("/")
    directory = pattern.endswith("/")
    out = ""
    index = 0
    while index < len(body):
        if body.startswith("**/", index):
            out += "(?:.*/)?"
            index += 3
        elif body.startswith("**", index):
            out += ".*"
            index += 2
        elif body[index] == "*":
            out += "[^/]*"
            index += 1
        elif body[index] == "?":
            out += "[^/]"
            index += 1
        else:
            out += re.escape(body[index])
            index += 1
    prefix = "^" if anchored else "^(?:.*/)?"
    suffix = "/.*$" if directory else "(?:/.*)?$"
    return re.compile(prefix + out + suffix)


def owners_for(text: str, path: str) -> CodeownersRule | None:
    """The rule that owns *path* (the last match wins), or None."""
    target = path.strip().lstrip("/")
    found: CodeownersRule | None = None
    for rule in parse_codeowners(text):
        if _pattern_regex(rule.pattern).match(target):
            found = rule
    return found
