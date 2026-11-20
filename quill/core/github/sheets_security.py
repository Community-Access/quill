"""The Security Alert sheet: Dependabot, code scanning and secret scanning (Appendix C).

State, GitHub's own dismissal or resolution reasons and a comment are
editable; the alert's package, manifest, rule, tool, file and dates read.
Each kind takes a slightly different body, so the save is composed whole.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.alert_triage import DISMISS_REASONS, alert_kind_for
from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, SheetSaveError, Write
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


def _word(reason: str) -> str:
    """One spelling for a reason: GitHub writes code scanning's with spaces, secrets' with _."""
    return reason.strip().lower().replace("_", " ").replace("'", "")


#: How the sheet says each of GitHub's reasons; code scanning and secret scanning
#: share "false positive", "won't fix" and "used in tests", spelled two ways.
_SAID: dict[str, str] = {
    _word(value): value
    for value in (
        "fix_started",
        "inaccurate",
        "no_bandwidth",
        "not_used",
        "tolerable_risk",
        "false positive",
        "won't fix",
        "used in tests",
        "revoked",
    )
}


def _alert(data: Mapping[str, Any]) -> dict[str, Value]:
    reason = str(data.get("dismissed_reason") or data.get("resolution") or "")
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
        "reason": _SAID.get(_word(reason), reason),
        "comment": str(data.get("dismissed_comment") or data.get("resolution_comment") or ""),
        "location": str(dig(data, "most_recent_instance", "location", "path") or ""),
        "created": when(data.get("created_at")),
        "fixed": when(data.get("fixed_at")),
        "url": str(data.get("html_url") or ""),
    }


def _compose_alert(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    """The one PATCH for the alert's kind, or a plain refusal before anything is sent.

    Each kind closes its own way (a secret is resolved, the others dismissed)
    and takes only its own reasons, so a choice that fits another kind is
    refused rather than sent; GitHub decides fixed and auto-dismissed itself.
    """
    alert_path = ident.get("alert_path", "")
    kind = alert_kind_for(alert_path.split("/", 1)[0])
    path = f"/repos/{ident['repo']}/{alert_path}/{ident['number']}"
    current = str(ident.get("state") or "open")
    state = str(edits.get("state") or current)
    if current not in ("open", kind.closed_state) or state not in ("open", kind.closed_state):
        settled = current if current not in ("open", kind.closed_state) else state
        raise SheetSaveError(
            f"A {kind.label.lower()} alert is open or {kind.closed_state}, never set to "
            f"{settled} from here; GitHub marks an alert {settled} itself."
            if settled in ("fixed", "auto_dismissed")
            else f"A {kind.label.lower()} alert is {kind.closed_state}, not {settled}: "
            f"choose open or {kind.closed_state}."
        )
    if state == "open":
        if current == "open":
            raise SheetSaveError(
                f"A reason and a comment go with {kind.closed_state} alerts: set State to "
                f"{kind.closed_state} too."
            )
        return [("PATCH", path, {"state": "open"})]
    allowed = {_word(value): value for value, _words in DISMISS_REASONS[kind.key]}
    chosen = str(edits.get("reason") or ident.get("reason") or "")
    if _word(chosen) not in allowed:
        said = ", ".join(_SAID.get(word, word) for word in allowed)
        raise SheetSaveError(
            f"Choose one of GitHub's reasons for a {kind.label.lower()} alert: {said}."
        )
    body: dict[str, object] = {"state": state, kind.reason_field: allowed[_word(chosen)]}
    if "comment" in edits:
        body[kind.comment_field] = str(edits.get("comment") or "")
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
                    "GitHub's own reasons; each kind of alert takes its own.",
                    choices=tuple(_SAID.values()),
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
