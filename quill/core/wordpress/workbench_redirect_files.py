"""Redirection's groups, and redirects to and from a file (complete.md 2.3, Redirects).

**Groups.** Every redirect lives in a group. Redirects > Groups lists them
(``GET redirection/v1/group``), and New Group, Rename and Turn On or Off send
``POST redirection/v1/group`` and ``POST redirection/v1/group/<id>`` with
``{"name", "moduleId"}``, and ``POST redirection/v1/bulk/group/<action>`` with
``{"items": [ids]}``, the same shapes as the redirect routes already used.
Deleting a group deletes its redirects with it, so it is tier 3 and names
how many go.

**Export and import run here, not in the plugin.** The plugin's own import
takes an uploaded form file, which QUILL does not send; instead Export reads
the redirects already read for the list and writes them to a file on this
computer (CSV, the plugin's own columns, or JSON), and Import reads a CSV or
a Redirection JSON export here, previews every redirect it would add and
every line it cannot use, and adds each through ``POST redirection/v1/redirect``,
the route Add Redirect uses. Wx-free.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_redirects import NAMESPACE, _target
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "GROUP_ACTIONS",
    "MODULES",
    "ImportPlan",
    "export_csv",
    "export_json",
    "group_body",
    "group_route",
    "group_row",
    "parse_import",
]

#: Redirection's modules: where a group's redirects run.
MODULES: dict[int, str] = {1: "WordPress", 2: "Apache", 3: "Nginx"}
GROUP_ACTIONS = frozenset({"enable", "disable", "delete"})
_CODES = frozenset({301, 302, 303, 304, 307, 308})


def group_row(site: str, raw: Mapping[str, Any]) -> WbRow:
    """One group: its name, module, how many redirects and whether it is on."""
    on = raw.get("enabled") is not False
    module = MODULES.get(int(raw.get("module_id", 1) or 1), "WordPress")
    count = int(raw.get("redirects", 0) or 0)
    name = str(raw.get("name", "") or f"Group {raw.get('id')}")
    return WbRow(
        "redirect_group",
        site,
        str(raw.get("id", "")),
        {"name": name, "module": module, "redirects": str(count), "state": "on" if on else "off"},
        f"{name}: {count} redirect{'s' if count != 1 else ''}, run by {module}, "
        f"{'on' if on else 'turned off'}.",
        status="enabled" if on else "disabled",
        raw=dict(raw),
    )


def group_body(name: str, module_id: int = 1) -> dict[str, Any]:
    words = " ".join(name.split())
    if not words:
        raise ValueError("A group needs a name.")
    return {"name": words, "moduleId": int(module_id) if int(module_id) in MODULES else 1}


def group_route(group_id: int | None = None, action: str = "") -> str:
    if action:
        if action not in GROUP_ACTIONS:
            raise ValueError(f"{action} is not something a group can do.")
        return f"{NAMESPACE}/bulk/group/{action}"
    return f"{NAMESPACE}/group" + (f"/{int(group_id)}" if group_id else "")


# -- export ------------------------------------------------------------------------------


def _export_rows(redirects: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source": str(r.get("url", "") or ""),
            "target": _target(r),
            "regex": 1 if r.get("regex") else 0,
            "code": int(r.get("action_code", 301) or 301),
            "type": str(r.get("action_type", "url") or "url"),
            "hits": int(r.get("hits", 0) or 0),
            "title": str(r.get("title", "") or ""),
            "status": "enabled" if r.get("enabled", True) is not False else "disabled",
            "last_access": friendly_date(str(r.get("last_access", "") or ""))
            if r.get("last_access")
            else "",
        }
        for r in redirects
    ]


def export_csv(redirects: Sequence[Mapping[str, Any]]) -> str:
    """The redirects as CSV, in the columns Redirection's own CSV import reads first."""
    out = io.StringIO()
    names = ["source", "target", "regex", "code", "type", "hits", "title", "status", "last_access"]
    writer = csv.DictWriter(out, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_export_rows(redirects))
    return out.getvalue()


def export_json(redirects: Sequence[Mapping[str, Any]], groups: Sequence[Mapping[str, Any]]) -> str:
    """The redirects and groups, in the shape of Redirection's own JSON export."""
    data = {
        "plugin": {"version": "", "date": ""},
        "groups": [dict(g) for g in groups],
        "redirects": [dict(r) for r in redirects],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# -- import ------------------------------------------------------------------------------


@dataclass
class ImportPlan:
    """The redirects a file would add, and every line it cannot use, with why."""

    adds: list[tuple[str, str, int, bool]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        found = [f"{source} leads to {target} ({code})." for source, target, code, _r in self.adds]
        if self.problems:
            found += ["Not added:", *self.problems]
        return found


def _add(plan: ImportPlan, where: str, source: str, target: str, code: Any, regex: Any) -> None:
    source, target = source.strip(), target.strip()
    try:
        number = int(str(code or 301).strip() or 301)
    except ValueError:
        number = 0
    if not source:
        plan.problems.append(f"{where}: it has no address to redirect from.")
    elif not target:
        plan.problems.append(f"{where}: {source} has no address to lead to.")
    elif number not in _CODES:
        plan.problems.append(f"{where}: {code} is not a redirect code (301, 302, 307 or 308).")
    elif any(a[0] == source for a in plan.adds):
        plan.problems.append(f"{where}: {source} is in the file twice; the first is used.")
    else:
        plan.adds.append((source, target, number, str(regex).strip() in ("1", "true", "True")))


def parse_import(text: str, filename: str, existing: Sequence[str] = ()) -> ImportPlan:
    """Read a CSV or a Redirection JSON export; skip sources the site already redirects."""
    plan = ImportPlan()
    stripped = text.lstrip("﻿").strip()
    if filename.casefold().endswith(".json") or stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except ValueError:
            plan.problems.append(f"{filename} is not JSON QUILL can read.")
            return plan
        found = data.get("redirects") if isinstance(data, Mapping) else None
        for number, raw in enumerate(found if isinstance(found, list) else [], start=1):
            if isinstance(raw, Mapping):
                _add(plan, f"Redirect {number}", str(raw.get("url", "")), _target(raw),
                     raw.get("action_code", 301), raw.get("regex", 0))  # fmt: skip
    else:
        rows = list(csv.reader(io.StringIO(stripped)))
        if rows and rows[0] and rows[0][0].strip().casefold() in ("source", "from", "url"):
            rows = rows[1:]
        for number, cells in enumerate(rows, start=1):
            if not any(c.strip() for c in cells):
                continue
            cells = [*cells, "", "", ""]
            _add(plan, f"Line {number}", cells[0], cells[1], cells[3] or 301, cells[2])
    known = {s.strip() for s in existing}
    kept = [a for a in plan.adds if a[0] not in known]
    plan.problems += [f"{a[0]}: the site already redirects it." for a in plan.adds if a[0] in known]
    plan.adds = kept
    if not plan.adds and not plan.problems:
        plan.problems.append(f"{filename} has no redirects in it.")
    return plan
