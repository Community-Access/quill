"""What a language server says, in the shapes QUILL already speaks.

Completion items become the suggestion list's rows (with the same kind words
layer 1 says), diagnostics become :class:`quill.core.problems.Problem`, a
signature becomes the one sentence parameter hints say, and code actions
become Quick Fix rows. Positions are converted between the server's
zero-based UTF-16 line and character and QUILL's offsets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.problems.model import Problem

__all__ = [
    "QuickFix",
    "ServerCompletion",
    "apply_text_edits",
    "completion_names",
    "lsp_position",
    "offset_from_lsp",
    "problems_from_diagnostics",
    "quick_fixes",
    "signature_sentence",
]

#: LSP CompletionItemKind -> the kind word the list says (layer 1's words).
_COMPLETION_KINDS: dict[int, str] = {
    1: "text",
    2: "method",
    3: "function",
    4: "constructor",
    5: "field",
    6: "variable",
    7: "class",
    8: "interface",
    9: "module",
    10: "property",
    11: "unit",
    12: "value",
    13: "enum",
    14: "keyword",
    15: "snippet",
    16: "colour",
    17: "file",
    18: "reference",
    19: "folder",
    20: "enum member",
    21: "constant",
    22: "struct",
    23: "event",
    24: "operator",
    25: "type parameter",
}

_SEVERITIES = {1: "error", 2: "warning", 3: "info", 4: "info"}


def _utf16_units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def lsp_position(text: str, offset: int) -> dict[str, int]:
    """QUILL's character *offset* as the server's ``{line, character}``."""
    offset = max(0, min(offset, len(text)))
    line = text.count("\n", 0, offset)
    start = text.rfind("\n", 0, offset) + 1
    return {"line": line, "character": _utf16_units(text[start:offset])}


def offset_from_lsp(text: str, line: int, character: int) -> int:
    """The server's ``line`` and UTF-16 ``character`` as QUILL's offset."""
    start = 0
    for _ in range(max(0, line)):
        newline = text.find("\n", start)
        if newline < 0:
            return len(text)
        start = newline + 1
    end = text.find("\n", start)
    end = len(text) if end < 0 else end
    units = 0
    for index in range(start, end):
        if units >= character:
            return index
        units += 2 if ord(text[index]) > 0xFFFF else 1
    return end


@dataclass(frozen=True, slots=True)
class ServerCompletion:
    """One server completion, ready for the list."""

    label: str
    insert: str
    kind: str
    detail: str


def completion_names(result: Any, fragment: str, *, limit: int = 8) -> list[ServerCompletion]:
    """The server's completions for *fragment*, best first, at most *limit*.

    Servers return everything that could go here, often hundreds; the list
    keeps the ones that start with what you typed (same case first), in the
    server's own ``sortText`` order after that.
    """
    items = result.get("items", []) if isinstance(result, dict) else list(result or [])
    lowered = fragment.lower()
    rows: list[tuple[tuple[int, str], ServerCompletion]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        insert = str(item.get("insertText") or (item.get("textEdit") or {}).get("newText") or label)
        filter_text = str(item.get("filterText") or label)
        # Servers write filter text their own way ("<div", "div>"); what counts
        # is the word inside, the part you were typing.
        candidates = {filter_text, label, insert}
        words = [text.lstrip("<./#@:-'\"") for text in candidates]
        if not label or label in seen or not any(w.lower().startswith(lowered) for w in words):
            continue
        if insert == fragment:
            continue
        seen.add(label)
        kind = _COMPLETION_KINDS.get(int(item.get("kind") or 1), "name")
        detail = str(item.get("detail") or (item.get("labelDetails") or {}).get("detail") or "")
        same_case = 0 if any(w.startswith(fragment) for w in words) else 1
        rows.append((
            (same_case, str(item.get("sortText") or label)),
            ServerCompletion(label, insert, kind, detail),
        ))
    rows.sort(key=lambda row: row[0])
    return [row[1] for row in rows[:limit]]


def problems_from_diagnostics(diagnostics: list[dict[str, Any]], *, source: str) -> list[Problem]:
    """A server's diagnostics as Problems, 1-based like every other checker's."""
    problems: list[Problem] = []
    for item in diagnostics:
        start = (item.get("range") or {}).get("start") or {}
        message = " ".join(str(item.get("message", "")).split())
        if not message:
            continue
        problems.append(
            Problem(
                line=int(start.get("line", 0)) + 1,
                column=int(start.get("character", 0)) + 1,
                severity=_SEVERITIES.get(int(item.get("severity") or 1), "error"),
                message=message,
                source=str(item.get("source") or source),
            )
        )
    return problems


def signature_sentence(result: Any) -> str:
    """Parameter hints in one sentence: "parameter 2 of 3, seconds. sleep(ms, seconds, label)".

    Empty when the server has no signature here.
    """
    if not isinstance(result, dict):
        return ""
    signatures = result.get("signatures") or []
    if not signatures:
        return ""
    index = int(result.get("activeSignature") or 0)
    signature = signatures[min(max(index, 0), len(signatures) - 1)]
    label = str(signature.get("label", ""))
    parameters = signature.get("parameters") or []
    active = signature.get("activeParameter", result.get("activeParameter"))
    if not parameters or active is None:
        return label
    active = min(max(int(active), 0), len(parameters) - 1)
    name = _parameter_label(label, parameters[active].get("label"))
    return f"Parameter {active + 1} of {len(parameters)}, {name}. {label}"


def _parameter_label(signature: str, label: Any) -> str:
    if isinstance(label, list) and len(label) == 2:
        return signature[int(label[0]) : int(label[1])]
    return str(label or "")


@dataclass(frozen=True, slots=True)
class QuickFix:
    """One code action the server offers for a problem."""

    title: str
    #: The edits for the document Quick Fix was asked about, ``(start, end, text)``
    #: as QUILL offsets, applied from the end backwards.
    edits: tuple[tuple[int, int, str], ...]
    preferred: bool = False


def quick_fixes(actions: Any, uri: str, text: str) -> list[QuickFix]:
    """The actions that change only this document's text, preferred first.

    An action that runs a server command, or edits other files, is left out:
    it could not be shown as text before it happens.
    """
    fixes: list[QuickFix] = []
    for action in actions or []:
        if not isinstance(action, dict) or "command" in action and "edit" not in action:
            continue
        edit = action.get("edit") or {}
        changes = (edit.get("changes") or {}).get(uri)
        if changes is None:
            for change in edit.get("documentChanges") or []:
                if (change.get("textDocument") or {}).get("uri") == uri:
                    changes = change.get("edits")
        if not changes:
            continue
        others = set((edit.get("changes") or {}).keys()) - {uri}
        if others:
            continue
        spans = []
        for item in changes:
            span = item.get("range") or {}
            start, end = span.get("start") or {}, span.get("end") or {}
            spans.append((
                offset_from_lsp(text, int(start.get("line", 0)), int(start.get("character", 0))),
                offset_from_lsp(text, int(end.get("line", 0)), int(end.get("character", 0))),
                str(item.get("newText", "")),
            ))
        fixes.append(
            QuickFix(str(action.get("title", "Fix")), tuple(spans), bool(action.get("isPreferred")))
        )
    fixes.sort(key=lambda fix: not fix.preferred)
    return fixes


def apply_text_edits(text: str, edits: tuple[tuple[int, int, str], ...]) -> str:
    """*text* with *edits* applied, last first so earlier offsets stay true."""
    for start, end, new in sorted(edits, key=lambda edit: edit[0], reverse=True):
        text = text[:start] + new + text[end:]
    return text
