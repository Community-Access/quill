"""Bulk draft import with validation and dry run (PRD 18.10).

Parses posts from CSV, TSV, JSON, and Markdown (posts separated by ``---``
lines) into ``ParsedRow`` records, then builds :class:`quill_social.model.Draft`
objects. Per PRD 18.10 the importer provides validation, an accessible preview,
a dry run, and duplicate detection. Parsing is forgiving: a malformed row never
raises -- its problems are collected in ``row.errors`` so the whole import is
never lost to one bad line.

The module is pure (no I/O, no clock beyond the model default) so it is fully
unit-testable. Time-zone confirmation (PRD 18.10) is surfaced to the caller via
the dry-run report; scheduling itself is left to the queue schedule and
scheduler services.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field

from quill_social.model import VISIBILITIES, Draft

# Recognized import formats.
FORMATS = ("csv", "tsv", "json", "markdown")

# Column / key names understood in tabular and JSON input.
_TEXT_KEYS = ("text", "body", "content", "post")
_TARGET_KEYS = ("targets", "target", "accounts", "account")
_KNOWN_KEYS = {
    "text", "body", "content", "post", "targets", "target", "accounts",
    "account", "visibility", "content_warning", "cw", "lang", "language",
    "campaign_id", "campaign", "name", "title",
}


@dataclass
class ParsedRow:
    """One imported post plus any validation problems (PRD 18.10)."""

    index: int = 0
    text: str = ""
    targets: list[str] = field(default_factory=list)
    visibility: str = "public"
    content_warning: str = ""
    lang: str = ""
    campaign_id: str = ""
    name: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "text": self.text,
            "targets": list(self.targets),
            "visibility": self.visibility,
            "content_warning": self.content_warning,
            "lang": self.lang,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "errors": list(self.errors),
        }


@dataclass
class DryRunReport:
    """An accessible preview of an import before it is committed (PRD 18.10)."""

    total: int = 0
    valid: int = 0
    invalid: int = 0
    duplicate_groups: list[list[int]] = field(default_factory=list)
    preview_lines: list[str] = field(default_factory=list)
    needs_timezone_confirmation: bool = True

    @property
    def duplicate_count(self) -> int:
        return sum(len(g) for g in self.duplicate_groups)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "valid": self.valid,
            "invalid": self.invalid,
            "duplicate_groups": [list(g) for g in self.duplicate_groups],
            "duplicate_count": self.duplicate_count,
            "preview_lines": list(self.preview_lines),
            "needs_timezone_confirmation": self.needs_timezone_confirmation,
        }


# -- helpers ------------------------------------------------------------------


def _first(mapping: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return str(mapping[key]).strip()
    return ""


def _split_targets(raw: str | list) -> list[str]:
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    if not raw:
        return []
    out: list[str] = []
    token = ""
    for ch in str(raw):
        if ch in ";,|" or ch.isspace():
            if token:
                out.append(token)
                token = ""
        else:
            token += ch
    if token:
        out.append(token)
    return out


def _normalize(text: str) -> str:
    """Normalize for duplicate detection: lowercase, collapse whitespace."""
    return " ".join(text.lower().split())


def _row_from_mapping(index: int, mapping: dict) -> ParsedRow:
    row = ParsedRow(index=index)
    row.text = _first(mapping, _TEXT_KEYS)
    row.targets = _split_targets(mapping.get("targets") or mapping.get("target")
                                 or mapping.get("accounts") or mapping.get("account")
                                 or "")
    row.visibility = (_first(mapping, ("visibility",)) or "public").lower()
    row.content_warning = _first(mapping, ("content_warning", "cw"))
    row.lang = _first(mapping, ("lang", "language"))
    row.campaign_id = _first(mapping, ("campaign_id", "campaign"))
    row.name = _first(mapping, ("name", "title"))
    _validate(row)
    return row


def _validate(row: ParsedRow) -> None:
    if not row.text.strip():
        row.errors.append("empty post text")
    if row.visibility not in VISIBILITIES:
        row.errors.append(f"unknown visibility '{row.visibility}'")
        row.visibility = "public"


# -- parsers ------------------------------------------------------------------


def _parse_delimited(source_text: str, delimiter: str) -> list[ParsedRow]:
    rows: list[ParsedRow] = []
    reader = csv.DictReader(io.StringIO(source_text), delimiter=delimiter)
    if reader.fieldnames is None:
        return rows
    for i, raw in enumerate(reader):
        mapping = {(k or "").strip().lower(): v for k, v in raw.items() if k}
        rows.append(_row_from_mapping(i, mapping))
    return rows


def _parse_json(source_text: str) -> list[ParsedRow]:
    try:
        data = json.loads(source_text)
    except (ValueError, TypeError) as exc:
        return [ParsedRow(index=0, errors=[f"invalid JSON: {exc}"])]
    if isinstance(data, dict):
        data = data.get("posts") or data.get("drafts") or [data]
    if not isinstance(data, list):
        return [ParsedRow(index=0, errors=["JSON must be a list of posts"])]
    rows: list[ParsedRow] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            rows.append(ParsedRow(index=i, errors=["row is not an object"]))
            continue
        mapping = {str(k).strip().lower(): v for k, v in item.items()}
        rows.append(_row_from_mapping(i, mapping))
    return rows


def _parse_markdown(source_text: str) -> list[ParsedRow]:
    blocks: list[str] = []
    current: list[str] = []
    for line in source_text.splitlines():
        if line.strip() == "---":
            blocks.append("\n".join(current))
            current = []
        else:
            current.append(line)
    blocks.append("\n".join(current))
    rows: list[ParsedRow] = []
    index = 0
    for block in blocks:
        if not block.strip():
            continue
        row = ParsedRow(index=index, text=block.strip())
        _validate(row)
        rows.append(row)
        index += 1
    return rows


def parse(source_text: str, fmt: str) -> list[ParsedRow]:
    """Parse ``source_text`` in format ``fmt`` into rows (PRD 18.10).

    ``fmt`` is one of :data:`FORMATS`. Malformed rows are returned with their
    problems in ``errors`` rather than raising.
    """
    fmt = fmt.lower()
    if fmt == "csv":
        return _parse_delimited(source_text, ",")
    if fmt == "tsv":
        return _parse_delimited(source_text, "\t")
    if fmt == "json":
        return _parse_json(source_text)
    if fmt == "markdown":
        return _parse_markdown(source_text)
    return [ParsedRow(index=0, errors=[f"unknown format '{fmt}'"])]


# -- outputs ------------------------------------------------------------------


def to_drafts(
    rows: list[ParsedRow], default_targets: list[str] | None = None
) -> list[Draft]:
    """Build drafts from valid rows (PRD 18.10). Invalid rows are skipped."""
    defaults = list(default_targets or [])
    drafts: list[Draft] = []
    for row in rows:
        if not row.ok:
            continue
        drafts.append(
            Draft(
                text=row.text,
                targets=row.targets or list(defaults),
                visibility=row.visibility,
                content_warning=row.content_warning,
                lang=row.lang,
                campaign_id=row.campaign_id,
                name=row.name,
            )
        )
    return drafts


def dry_run(rows: list[ParsedRow]) -> DryRunReport:
    """An accessible preview with counts and duplicate detection (PRD 18.10)."""
    report = DryRunReport(total=len(rows))
    by_norm: dict[str, list[int]] = {}
    for row in rows:
        if row.ok:
            report.valid += 1
        else:
            report.invalid += 1
        norm = _normalize(row.text)
        if norm:
            by_norm.setdefault(norm, []).append(row.index)
        report.preview_lines.append(_preview_line(row))
    report.duplicate_groups = [
        sorted(idxs) for idxs in by_norm.values() if len(idxs) > 1
    ]
    return report


def _preview_line(row: ParsedRow) -> str:
    snippet = row.text.strip().replace("\n", " ")[:80] or "(empty)"
    targets = ", ".join(row.targets) if row.targets else "default targets"
    status = "ok" if row.ok else "errors: " + "; ".join(row.errors)
    return (
        f"Row {row.index + 1}: {snippet} | visibility {row.visibility} | "
        f"to {targets} | {status}"
    )
