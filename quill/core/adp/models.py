"""ADP Assistant response models (mirrors s:/code/adp docs/API.md sections 3 and 6).

The dataset envelope is deliberately extensible server-side: unknown
``result.kind`` values and unknown row fields must render generically, never
be rejected. ``history`` is opaque -- round-trip it verbatim; never edit it.
wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AdpDataset:
    """One tool's structured results: {tool, input, result}."""

    tool: str
    input: dict[str, object] = field(default_factory=dict)
    result: dict[str, object] = field(default_factory=dict)

    @property
    def kind(self) -> str:
        return str(self.result.get("kind", ""))

    @property
    def rows(self) -> list[dict[str, object]]:
        rows = self.result.get("rows")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

    @property
    def count(self) -> int | None:
        count = self.result.get("count")
        return int(count) if isinstance(count, (int, float)) else None

    @classmethod
    def from_dict(cls, data: object) -> AdpDataset | None:
        if not isinstance(data, dict):
            return None
        result = data.get("result")
        input_ = data.get("input")
        return cls(
            tool=str(data.get("tool", "")),
            input=dict(input_) if isinstance(input_, dict) else {},
            result=dict(result) if isinstance(result, dict) else {},
        )


@dataclass(slots=True)
class AskResponse:
    """POST /api/ask's 200 body: speakable answer + datasets + opaque history."""

    answer: str
    datasets: list[AdpDataset] = field(default_factory=list)
    history: list[object] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: object) -> AskResponse:
        if not isinstance(data, dict):
            return cls(answer="")
        raw_datasets = data.get("datasets")
        datasets: list[AdpDataset] = []
        if isinstance(raw_datasets, list):
            for entry in raw_datasets:
                parsed = AdpDataset.from_dict(entry)
                if parsed is not None:
                    datasets.append(parsed)
        history = data.get("history")
        return cls(
            answer=str(data.get("answer", "")),
            datasets=datasets,
            history=list(history) if isinstance(history, list) else [],
        )


#: Columns for the accessible results table (API.md section 6/12's validated
#: presentation): value pulled from the first matching key present in a row.
TABLE_COLUMNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Title", ("title", "program", "name")),
    ("Year", ("year",)),
    ("Type", ("media_type", "network")),
    ("Providers", ("providers",)),
    ("Rating", ("rating",)),
    ("Genres", ("genres", "tags")),
)


def row_cell(row: dict[str, object], keys: tuple[str, ...]) -> str:
    """First present key's value, list-joined, for the results table."""
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    return ""
