"""Defensive RTF scanning, adapted from QUILL for All (quill/io/rtf_safety.py).

RTF can embed OLE objects and executables (\\object, \\objdata), raw binary
(\\bin) and fields that fetch remote content. Nothing reaches the native
control until this has stripped the dangerous groups.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["RtfSafetyReport", "scan_rtf_safety"]

_DANGEROUS_DESTINATIONS: frozenset[str] = frozenset(
    {
        "object",
        "objdata",
        "objclass",
        "objemb",
        "objautlink",
        "objalias",
        "datastore",
    }
)

_DESTINATION_LABELS: dict[str, str] = {
    "object": "embedded OLE object",
    "objdata": "embedded object data",
    "objclass": "embedded object class",
    "objemb": "embedded OLE object",
    "objautlink": "auto-updating linked object",
    "objalias": "object alias",
    "datastore": "embedded data store",
}

_REMOTE_FIELD_RE = re.compile(r"INCLUDEPICTURE|INCLUDETEXT|DDEAUTO", re.IGNORECASE)
_BIN_RE = re.compile(r"\\bin\d+", re.IGNORECASE)


@dataclass(slots=True)
class RtfSafetyReport:
    safe: bool
    sanitized_rtf: str
    blocked: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _group_start_destination(rtf: str, brace_index: int) -> str | None:
    index = brace_index + 1
    length = len(rtf)
    if index < length and rtf[index] == "\\" and index + 1 < length and rtf[index + 1] == "*":
        index += 2
        while index < length and rtf[index] in " \r\n":
            index += 1
    if index >= length or rtf[index] != "\\":
        return None
    index += 1
    start = index
    while index < length and rtf[index].isalpha():
        index += 1
    word = rtf[start:index]
    return word if word in _DANGEROUS_DESTINATIONS else None


def _skip_group(rtf: str, brace_index: int) -> int:
    depth = 0
    index = brace_index
    length = len(rtf)
    while index < length:
        char = rtf[index]
        if char == "\\" and index + 1 < length and rtf[index + 1] in "{}\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return length


def _strip_dangerous_groups(rtf: str) -> tuple[str, list[str]]:
    out: list[str] = []
    blocked: list[str] = []
    index = 0
    length = len(rtf)
    while index < length:
        char = rtf[index]
        if char == "\\" and rtf.startswith(("\\{", "\\}", "\\\\"), index):
            out.append(rtf[index : index + 2])
            index += 2
            continue
        if char == "{":
            destination = _group_start_destination(rtf, index)
            if destination is not None:
                label = _DESTINATION_LABELS.get(destination, destination)
                if label not in blocked:
                    blocked.append(label)
                index = _skip_group(rtf, index)
                continue
        out.append(char)
        index += 1
    return "".join(out), blocked


def scan_rtf_safety(rtf: str) -> RtfSafetyReport:
    sanitized, blocked = _strip_dangerous_groups(rtf)
    warnings: list[str] = []
    if _BIN_RE.search(sanitized):
        sanitized = _BIN_RE.sub(r"\\bin0", sanitized)
        warnings.append("binary data")
    if _REMOTE_FIELD_RE.search(sanitized):
        warnings.append("remote content references")
    return RtfSafetyReport(
        safe=not blocked, sanitized_rtf=sanitized, blocked=blocked, warnings=warnings
    )
