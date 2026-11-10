"""The Security Alert sheet: Dependabot, code scanning and secret scanning (Appendix C).

State, GitHub's own dismissal or resolution reasons and a comment are
editable; the alert's package, manifest, rule, tool, file and dates read.
Each kind takes a slightly different body, so the save is composed whole.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import (
    dig,
    ed,
    page,
    ro,
    when,
)
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["ALERT_PATHS", "SECURITY_ALERT"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind


#: Each alert kind's path and the words GitHub uses for its states.
ALERT_PATHS: dict[str, str] = {
    "dependabot": "dependabot/alerts",
    "code_scanning": "code-scanning/alerts",
    "secret_scanning": "secret-scanning/alerts",
}


def _alert(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "number": int(data.get("number") or 0),
        "state": str(data.get("state") or ""),
        "severity": str(
            dig(data, "security_advisory", "severity")
            or dig(data, "rule", "security_severity_level")
            or dig(data, "rule", "severity")
            or ""
        ),
        "package": str(dig(data, "dependency", "package", "name") or ""),
        "manifest": str(dig(data, "dependency", "manifest_path") or ""),
        "rule": str(
            dig(data, "rule", "description") or dig(data, "secret_type_display_name") or ""
        ),
        "tool": str(dig(data, "tool", "name") or ""),
        "reason": str(data.get("dismissed_reason") or data.get("resolution") or ""),
        "comment": str(data.get("dismissed_comment") or data.get("resolution_comment") or ""),
        "location": str(dig(data, "most_recent_instance", "location", "path") or ""),
        "created": when(data.get("created_at")),
        "fixed": when(data.get("fixed_at")),
        "url": str(data.get("html_url") or ""),
    }


def _compose_alert(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    kind = "secret_scanning" if ident.get("alert_path", "").startswith("secret") else "other"
    path = f"/repos/{ident['repo']}/{ident.get('alert_path', '')}/{ident['number']}"
    state = str(edits.get("state") or ident.get("state") or "open")
    reason = str(edits.get("reason") or ident.get("reason") or "")
    comment = str(edits.get("comment") or "")
    if kind == "secret_scanning":
        body: dict[str, object] = {"state": "resolved" if state == "resolved" else "open"}
        if state == "resolved":
            body.update({"resolution": reason or "false_positive", "resolution_comment": comment})
    else:
        body = {"state": "dismissed" if state == "dismissed" else "open"}
        if state == "dismissed":
            body.update({
                "dismissed_reason": reason or "tolerable_risk",
                "dismissed_comment": comment,
            })
    return [("PATCH", path, body)]


SECURITY_ALERT = SheetDef(
    "security_alert",
    SheetSpec(
        "security_alert",
        "Security Alert",
        (
            page(
                "general",
                "General",
                ro("number", "Number", _K.NUMBER),
                ed(
                    "state",
                    "State",
                    _K.CHOICE,
                    "Open, or dismissed (or resolved, for a secret) with a reason.",
                    choices=("open", "dismissed", "resolved"),
                ),
                ed(
                    "reason",
                    "Reason",
                    _K.CHOICE,
                    "GitHub's own reasons.",
                    choices=(
                        "fix_started",
                        "inaccurate",
                        "no_bandwidth",
                        "not_used",
                        "tolerable_risk",
                        "false positive",
                        "won't fix",
                        "used in tests",
                        "false_positive",
                        "wont_fix",
                        "revoked",
                        "used_in_tests",
                    ),
                ),
                ed("comment", "Comment", _K.MULTILINE),
                ro("severity", "Severity"),
                ro("created", "Opened", _K.DATE),
                ro("url", "Address", _K.LINK),
            ),
            page(
                "location",
                "Location",
                ro("package", "Package"),
                ro("manifest", "Manifest"),
                ro("location", "File"),
                ro("rule", "Rule"),
                ro("tool", "Tool"),
            ),
            page("history", "History", ro("fixed", "Fixed", _K.DATE)),
            page(
                "fix",
                "Fix",
                ro(
                    "fix_note",
                    "Fix",
                    help="For Dependabot, a security update "
                    "pull request fixes it; Open on GitHub to create one.",
                ),
            ),
        ),
    ),
    (Read("/repos/{repo}/{alert_path}/{number}", _alert),),
    {
        key: Write(
            "/repos/{repo}/{alert_path}/{number}",
            "repo:write+scope:security_events",
            _V,
            "PATCH",
            "patch",
        )
        for key in ("state", "reason", "comment")
    },
    title=lambda ident: f"Alert {ident['number']}",
    compose=_compose_alert,
    adopt=("state", "reason"),
)
