"""The GitHub API Console (PRD 22.2): any REST or GraphQL request, explained first.

The console is the guarantee behind "anything GitHub can do". This module is
its wx-free half:

- **Schema completion** from the vendored snapshot
  (``quill/data/github_api/rest.json``, refreshed only by
  ``scripts/github_api_snapshot.py``, never fetched): :func:`complete_path`
  matches what was typed against every operation's path template, keeping the
  values already typed, and :func:`find_operation` names the operation.
- **Permission and risk in words** before anything is sent:
  :func:`explain` says what the request does, its tier (section 18.4), the
  token scope the snapshot records, and that a write needs Full access and a
  typed confirmation (:func:`confirmation_word`).
- **The answer as a tree** (:func:`answer_tree`): each field or list item a
  node with its value in the label and its JSON path, for Copy Value and Copy
  Path; :func:`export_json` gives the text for JSON export.
- **Saved commands** (:class:`SavedCommands`), per account in
  ``github_console_commands.json``, schema-stamped and written atomically.

Strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "COMMANDS_FILENAME",
    "METHODS",
    "AnswerNode",
    "ConsoleCommand",
    "Operation",
    "SavedCommands",
    "answer_tree",
    "complete_path",
    "confirmation_word",
    "explain",
    "export_json",
    "find_operation",
    "is_write",
    "load_operations",
    "parse_body",
]

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "GRAPHQL")
COMMANDS_FILENAME = "github_console_commands.json"
_SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "github_api" / "rest.json"
_TIER_WORDS = {
    "read": "a read: nothing changes",
    "0": "organizing: changes only how things are arranged",
    "1": "visible to others: a change people will see",
    "2": "access and settings: changes who may do what, or how the repository behaves",
    "3": "destructive or hard to reverse",
}


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    name: str
    tier: str
    scope: str
    category: str = ""


@lru_cache(maxsize=4)
def _load(path: str) -> tuple[Operation, ...]:
    raw = read_json(Path(path), default={})
    rows = raw.get("operations") if isinstance(raw, dict) else None
    found: list[Operation] = []
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, dict) or not row.get("path"):
            continue
        found.append(
            Operation(
                str(row.get("method", "GET")).upper(),
                str(row["path"]),
                str(row.get("name", "")),
                str(row.get("tier", "read")),
                str(row.get("scope", "")).replace("`", ""),
                str(row.get("category", "")),
            )
        )
    return tuple(found)


def load_operations(path: Path | None = None) -> tuple[Operation, ...]:
    """Every REST operation in the vendored snapshot; empty when it is missing."""
    return _load(str(path or _SNAPSHOT))


def _segments(path: str) -> list[str]:
    return [s for s in path.split("?")[0].strip().strip("/").split("/")]


def _matches(typed: Sequence[str], template: Sequence[str], *, partial: bool) -> bool:
    if len(typed) > len(template) or (not partial and len(typed) != len(template)):
        return False
    for index, (have, want) in enumerate(zip(typed, template, strict=False)):
        last = partial and index == len(typed) - 1
        if want.startswith("{"):
            if not have and not last:
                return False
            continue
        if last:
            if not want.lower().startswith(have.lower()):
                return False
        elif have.lower() != want.lower():
            return False
    return True


def complete_path(
    typed: str,
    operations: Iterable[Operation],
    method: str = "",
    *,
    limit: int = 30,
) -> list[str]:
    """Paths that continue *typed*, with the values already typed kept in place."""
    text = typed.strip()
    if not text.startswith("/"):
        text = "/" + text
    have = _segments(text) if text != "/" else [""]
    out: list[str] = []
    for op in operations:
        if method and method not in ("GRAPHQL", op.method):
            continue
        template = _segments(op.path)
        if not _matches(have, template, partial=True):
            continue
        last = len(have) - 1
        tail = have[last] if template[last].startswith("{") and have[last] else template[last]
        filled = [*have[:last], tail]
        candidate = "/" + "/".join(filled + template[len(have) :])
        if candidate not in out:
            out.append(candidate)
    out.sort(key=lambda p: (p.count("/"), p))
    return out[:limit]


def find_operation(method: str, path: str, operations: Iterable[Operation]) -> Operation | None:
    """The snapshot's operation for *method* and a filled-in *path*, if any."""
    typed = _segments(path)
    best: Operation | None = None
    for op in operations:
        if op.method != method.upper() or not _matches(typed, _segments(op.path), partial=False):
            continue
        # Prefer the template with the most literal segments (/user/repos over /{x}/repos).
        literal = sum(not s.startswith("{") for s in _segments(op.path))
        if best is None or literal > sum(not s.startswith("{") for s in _segments(best.path)):
            best = op
    return best


def is_write(method: str, text: str = "") -> bool:
    """A REST method other than GET, or a GraphQL document holding a mutation."""
    if method.upper() == "GRAPHQL":
        return "mutation" in text.lower().split("{", 1)[0] or text.lstrip().lower().startswith(
            "mutation"
        )
    return method.upper() != "GET"


def confirmation_word(method: str) -> str:
    """What a person types to send a write: the method itself, or MUTATION."""
    return "MUTATION" if method.upper() == "GRAPHQL" else method.upper()


def explain(method: str, path: str, operation: Operation | None, *, query_text: str = "") -> str:
    """What the request does and what it needs, in words, before it is sent."""
    if method.upper() == "GRAPHQL":
        if is_write("GRAPHQL", query_text):
            return (
                "A GraphQL mutation: it changes something on GitHub. It needs Full access "
                "in Workbench Options, and you type MUTATION to send it."
            )
        return "A GraphQL query: a read. Nothing changes."
    if operation is None:
        base = f"{method} {path}: not in QUILL's copy of GitHub's API description"
        if is_write(method):
            return (
                f"{base}, so its risk is unknown. Treat it as destructive. It needs Full "
                f"access, and you type {confirmation_word(method)} to send it."
            )
        return base + ". A GET only reads."
    tier = _TIER_WORDS.get(operation.tier, "a change")
    scope = f" The token needs the {operation.scope} scope." if operation.scope else ""
    if operation.tier == "read" and not is_write(method):
        return f"{operation.name}: {tier}.{scope}"
    return (
        f"{operation.name}: {tier}.{scope} It needs Full access in Workbench Options, "
        f"and you type {confirmation_word(method)} to send it."
    )


def parse_body(text: str) -> dict[str, Any]:
    """A JSON object, or ``name=value`` lines (numbers and true/false read as such)."""
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith("{"):
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"That is not valid JSON: {exc.msg}, line {exc.lineno}.") from exc
        if not isinstance(value, dict):
            raise ValueError("The body must be a JSON object.")
        return value
    found: dict[str, Any] = {}
    for line in stripped.splitlines():
        if not line.strip():
            continue
        name, sep, raw = line.partition("=")
        if not sep or not name.strip():
            raise ValueError(f"Write each line as name=value: {line.strip()}")
        value_text = raw.strip()
        try:
            found[name.strip()] = json.loads(value_text)
        except json.JSONDecodeError:
            found[name.strip()] = value_text
    return found


@dataclass
class AnswerNode:
    """One field or list item of an answer: label, JSON path, the value itself."""

    label: str
    path: str
    value: Any
    children: list[AnswerNode] = field(default_factory=list)

    def value_text(self) -> str:
        if isinstance(self.value, (dict, list)):
            return json.dumps(self.value, ensure_ascii=False, indent=2)
        return "" if self.value is None else str(self.value)


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return text if len(text) <= 200 else text[:200] + "..."


def answer_tree(value: Any, name: str = "Answer", path: str = "$") -> AnswerNode:
    """The answer as nodes: an object's fields, a list's items, a value in its label."""
    if isinstance(value, dict):
        node = AnswerNode(f"{name}: object, {len(value)} fields", path, value)
        node.children = [
            answer_tree(v, str(k), f"{path}.{k}" if str(k).isidentifier() else f"{path}[{k!r}]")
            for k, v in value.items()
        ]
        return node
    if isinstance(value, list):
        node = AnswerNode(f"{name}: list, {len(value)} items", path, value)
        node.children = [
            answer_tree(v, f"Item {i + 1}", f"{path}[{i}]") for i, v in enumerate(value)
        ]
        return node
    return AnswerNode(f"{name}: {_scalar(value)}", path, value)


def export_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


@dataclass(frozen=True)
class ConsoleCommand:
    name: str
    method: str
    path: str
    body: str = ""


@dataclass
class SavedCommands:
    """One account's saved console commands."""

    account: str
    path: Path | None = None
    commands: list[ConsoleCommand] = field(default_factory=list)

    def _file(self) -> Path:
        return self.path or (app_data_dir() / COMMANDS_FILENAME)

    @classmethod
    def load(cls, account: str, path: Path | None = None) -> SavedCommands:
        saved = cls(account, path)
        raw = read_json(saved._file(), default={})
        accounts = raw.get("accounts") if isinstance(raw, dict) else None
        mine = accounts.get(account) if isinstance(accounts, Mapping) else None
        for row in mine if isinstance(mine, list) else ():
            if isinstance(row, dict) and row.get("name") and row.get("method") in METHODS:
                saved.commands.append(
                    ConsoleCommand(
                        str(row["name"]),
                        str(row["method"]),
                        str(row.get("path", "")),
                        str(row.get("body", "")),
                    )
                )
        return saved

    def put(self, command: ConsoleCommand) -> None:
        """Add *command*, replacing one of the same name."""
        self.commands = [c for c in self.commands if c.name != command.name] + [command]

    def remove(self, name: str) -> None:
        self.commands = [c for c in self.commands if c.name != name]

    def save(self) -> None:
        target = self._file()
        raw = read_json(target, default={})
        accounts = raw.get("accounts") if isinstance(raw, dict) else None
        everyone = dict(accounts) if isinstance(accounts, dict) else {}
        everyone[self.account] = [asdict(c) for c in self.commands]
        write_json_atomic(target, {"schema_version": 1, "accounts": everyone})
