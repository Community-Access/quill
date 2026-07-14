from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import write_json_atomic


@dataclass(slots=True)
class Snippet:
    id: str
    name: str
    trigger: str
    body: str
    description: str = ""
    tags: list[str] | None = None
    enabled: bool = True
    source: str = "user"

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger,
            "body": self.body,
            "description": self.description,
            "tags": list(self.tags or []),
            "enabled": bool(self.enabled),
            "source": self.source,
        }


@dataclass(slots=True)
class SnippetLibrary:
    version: int
    snippets: list[Snippet]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "snippets": [snippet.to_dict() for snippet in self.snippets],
        }


@dataclass(slots=True)
class Placeholder:
    token: str
    kind: str
    name: str
    options: list[str]


@dataclass(slots=True)
class ExpansionResult:
    text: str
    cursor: int


_PLACEHOLDER_PATTERN = re.compile(r"\$\{((?:[^{}]|\{[^{}]*\})*)\}")
_DEFAULT_LIBRARY_VERSION = 1
_SNIPPETS_RELATIVE_PATH = Path("snippets") / "snippets.json"

_STARTER_PACKS: dict[str, list[Snippet]] = {
    "daily-writing": [
        Snippet(
            id="daily-journal-header",
            name="Daily Journal Header",
            trigger=";journal",
            body="# ${input:title}\nDate: ${date}\n\n${cursor}",
            description="Start a daily journal entry with title and date.",
            tags=["writing", "journal"],
            source="starter-pack",
        ),
        Snippet(
            id="meeting-notes",
            name="Meeting Notes",
            trigger=";meeting",
            body="# Meeting: ${input:topic}\nAttendees: ${input:attendees}\n\n## Notes\n${cursor}",
            description="Capture a meeting topic, attendees, and notes.",
            tags=["writing", "meeting"],
            source="starter-pack",
        ),
    ],
    "developer-flow": [
        Snippet(
            id="bug-report-template",
            name="Bug Report Template",
            trigger=";bug",
            body=(
                "## Summary\n${input:summary}\n\n"
                "## Steps to Reproduce\n1. ${cursor}\n\n"
                "## Expected Result\n${input:expected}\n\n"
                "## Actual Result\n${input:actual}\n"
            ),
            description="Structured bug report skeleton.",
            tags=["developer", "reporting"],
            source="starter-pack",
        ),
        Snippet(
            id="commit-message",
            name="Commit Message Blueprint",
            trigger=";commit",
            body="type(scope): ${input:summary}\n\n${input:details}",
            description="Conventional commit message helper.",
            tags=["developer", "git"],
            source="starter-pack",
        ),
    ],
    "support-and-accessibility": [
        Snippet(
            id="screen-reader-checklist",
            name="Screen Reader QA Checklist",
            trigger=";srqa",
            body=(
                "Screen reader: ${choice:NVDA|JAWS|Narrator}\n"
                "Workflow tested: ${input:workflow}\n"
                "Result: ${choice:Pass|Needs Follow-up}\n"
                "Notes: ${cursor}"
            ),
            description="Capture screen-reader validation notes quickly.",
            tags=["accessibility", "qa"],
            source="starter-pack",
        ),
    ],
}


def snippet_library_path() -> Path:
    return app_data_dir() / _SNIPPETS_RELATIVE_PATH


def starter_pack_names() -> list[str]:
    return sorted(_STARTER_PACKS)


def starter_pack_snippets(name: str) -> list[Snippet]:
    return [
        replace(snippet, tags=list(snippet.tags) if snippet.tags is not None else None)
        for snippet in _STARTER_PACKS.get(name, [])
    ]


def snippet_library_from_dict(payload: object) -> SnippetLibrary:
    """Reconstruct a :class:`SnippetLibrary` from a serialized mapping.

    Mirrors the parsing in :func:`load_snippet_library` so a library read from
    a share package or any in-memory dict is validated identically to one read
    from disk.  Malformed entries are skipped rather than raising.
    """
    if not isinstance(payload, dict):
        return SnippetLibrary(version=_DEFAULT_LIBRARY_VERSION, snippets=[])
    version = int(payload.get("version", _DEFAULT_LIBRARY_VERSION))
    snippets: list[Snippet] = []
    raw_snippets = payload.get("snippets", [])
    if not isinstance(raw_snippets, list):
        raw_snippets = []
    for item in raw_snippets:
        if not isinstance(item, dict):
            continue
        tags_raw = item.get("tags", [])
        if isinstance(tags_raw, list):
            tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
        else:
            tags = []
        snippet = Snippet(
            id=str(item.get("id", "")).strip(),
            name=str(item.get("name", "")).strip(),
            trigger=str(item.get("trigger", "")).strip(),
            body=str(item.get("body", "")),
            description=str(item.get("description", "")).strip(),
            tags=tags,
            enabled=bool(item.get("enabled", True)),
            source=str(item.get("source", "user")).strip() or "user",
        )
        if snippet.id and snippet.name and snippet.trigger and snippet.body:
            snippets.append(snippet)
    return SnippetLibrary(version=version, snippets=snippets)


def load_snippet_library(path: Path | None = None) -> SnippetLibrary:
    target = path or snippet_library_path()
    if not target.exists():
        return SnippetLibrary(version=_DEFAULT_LIBRARY_VERSION, snippets=[])
    payload = json.loads(target.read_text(encoding="utf-8"))
    return snippet_library_from_dict(payload)


def save_snippet_library(library: SnippetLibrary, path: Path | None = None) -> Path:
    target = path or snippet_library_path()
    write_json_atomic(target, library.to_dict())
    return target


def merge_starter_pack(library: SnippetLibrary, pack_name: str) -> SnippetLibrary:
    starter = starter_pack_snippets(pack_name)
    if not starter:
        return library
    by_id = {snippet.id: snippet for snippet in library.snippets}
    for snippet in starter:
        by_id.setdefault(snippet.id, snippet)
    merged = sorted(by_id.values(), key=lambda item: item.name.lower())
    return SnippetLibrary(version=library.version, snippets=merged)


def search_snippets(snippets: list[Snippet], query: str) -> list[Snippet]:
    needle = query.strip().lower()
    filtered = [snippet for snippet in snippets if snippet.enabled]
    if not needle:
        return sorted(filtered, key=lambda item: item.name.lower())

    exact_trigger: list[Snippet] = []
    starts_with_name: list[Snippet] = []
    tag_matches: list[Snippet] = []
    other_matches: list[Snippet] = []
    for snippet in filtered:
        trigger = snippet.trigger.lower()
        name = snippet.name.lower()
        description = snippet.description.lower()
        body = snippet.body.lower()
        tags = [tag.lower() for tag in (snippet.tags or [])]
        if trigger == needle:
            exact_trigger.append(snippet)
        elif name.startswith(needle):
            starts_with_name.append(snippet)
        elif any(needle in tag for tag in tags):
            tag_matches.append(snippet)
        elif needle in name or needle in trigger or needle in description or needle in body:
            other_matches.append(snippet)
    return [
        *sorted(exact_trigger, key=lambda item: item.name.lower()),
        *sorted(starts_with_name, key=lambda item: item.name.lower()),
        *sorted(tag_matches, key=lambda item: item.name.lower()),
        *sorted(other_matches, key=lambda item: item.name.lower()),
    ]


def find_snippet_by_trigger(snippets: list[Snippet], trigger: str) -> Snippet | None:
    needle = trigger.strip().lower()
    if not needle:
        return None
    for snippet in snippets:
        if snippet.enabled and snippet.trigger.lower() == needle:
            return snippet
    return None


def extract_placeholders(body: str) -> list[Placeholder]:
    placeholders: dict[str, Placeholder] = {}
    for match in _PLACEHOLDER_PATTERN.finditer(body):
        token = match.group(1).strip()
        if not token:
            continue
        if token == "cursor":
            placeholders.setdefault(
                token,
                Placeholder(token=token, kind="cursor", name="cursor", options=[]),
            )
            continue
        if token in {"date", "time"}:
            placeholders.setdefault(
                token,
                Placeholder(token=token, kind=token, name=token, options=[]),
            )
            continue
        if ":" in token:
            kind, rest = token.split(":", 1)
            kind = kind.strip().lower()
            rest = rest.strip()
            if not rest:
                raise ValueError(
                    f"Snippet placeholder '${{{token}}}' has no name after ':' "
                    "(e.g. ${input:title}, not ${input:})"
                )
            if kind == "choice":
                options = [part.strip() for part in rest.split("|") if part.strip()]
                if not options:
                    raise ValueError(
                        f"Snippet placeholder '${{{token}}}' has no choice options "
                        "(e.g. ${choice:Yes|No})"
                    )
                placeholders.setdefault(
                    token,
                    Placeholder(token=token, kind="choice", name=rest, options=options),
                )
                continue
            if kind in {"input", "name"}:
                placeholders.setdefault(
                    token,
                    Placeholder(token=token, kind="input", name=rest, options=[]),
                )
                continue
        placeholders.setdefault(
            token,
            Placeholder(token=token, kind="input", name=token, options=[]),
        )
    return list(placeholders.values())


def render_snippet(body: str, values: dict[str, str]) -> ExpansionResult:
    placeholders_by_token = {p.token: p for p in extract_placeholders(body)}
    chunks: list[str] = []
    cursor: int | None = None
    index = 0
    for match in _PLACEHOLDER_PATTERN.finditer(body):
        chunks.append(body[index : match.start()])
        token = match.group(1).strip()
        placeholder = placeholders_by_token.get(token)
        if placeholder is None:
            chunks.append(match.group(0))
        elif placeholder.kind == "cursor":
            if cursor is None:
                cursor = len("".join(chunks))
        elif placeholder.kind == "date":
            chunks.append(datetime.now().strftime("%Y-%m-%d"))
        elif placeholder.kind == "time":
            chunks.append(datetime.now().strftime("%H:%M"))
        elif token in values:
            chunks.append(values[token])
        else:
            raise ValueError(
                f"No value supplied for snippet placeholder '{placeholder.name}' (${{{token}}})"
            )
        index = match.end()
    chunks.append(body[index:])
    text = "".join(chunks)
    if cursor is None:
        cursor = len(text)
    elif cursor > len(text):
        cursor = len(text)
    return ExpansionResult(text=text, cursor=cursor)
