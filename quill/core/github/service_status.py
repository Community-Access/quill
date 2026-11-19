"""GitHub's own service status, read only when you ask (complete.md 1.3).

When GitHub is slow or failing, the Workbench's errors look like the person's
own fault. Help > GitHub Service Status... reads GitHub's public status page
(``www.githubstatus.com``, the Statuspage summary) and says, in plain words,
whether GitHub says everything is working, which parts are not, and any
incident it is working on, with its latest update.

It is the one Workbench read that goes somewhere other than GitHub's API, so it
asks once before the first read (:func:`consented` / :func:`record_consent`),
sends nothing about you or your repositories, and never runs on its own.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "STATUS_URL",
    "ServiceStatus",
    "ServiceStatusError",
    "consented",
    "parse_summary",
    "read_status",
    "record_consent",
]

STATUS_URL = "https://www.githubstatus.com/api/v2/summary.json"
_CONSENT_FILE = "github_status_consent.json"

_COMPONENT_WORDS = {
    "operational": "working",
    "degraded_performance": "slow",
    "partial_outage": "partly down",
    "major_outage": "down",
    "under_maintenance": "under maintenance",
}


class ServiceStatusError(CodedError):
    """GitHub's status page could not be read, in one sentence."""

    code = "QUILL-GITHUB-STATUS-READ"


@dataclass(frozen=True)
class ServiceStatus:
    """What GitHub's status page says now."""

    overall: str
    trouble: list[str] = field(default_factory=list)
    incidents: list[str] = field(default_factory=list)

    def sentences(self) -> str:
        lines = [self.overall]
        if self.trouble:
            lines.append("Not working normally: " + "; ".join(self.trouble) + ".")
        lines.extend(self.incidents)
        if not self.trouble and not self.incidents:
            lines.append("GitHub lists no incident.")
        return "\n".join(lines)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def parse_summary(raw: Mapping[str, Any]) -> ServiceStatus:
    """The Statuspage summary JSON, in words."""
    found = raw.get("status")
    status: Mapping[str, Any] = found if isinstance(found, dict) else {}
    overall = _text(status.get("description")) or "GitHub did not say how it is."
    trouble = []
    for part in raw.get("components") or []:
        if not isinstance(part, dict) or part.get("group"):
            continue
        state = str(part.get("status") or "")
        if state and state != "operational":
            trouble.append(f"{_text(part.get('name'))} is {_COMPONENT_WORDS.get(state, state)}")
    incidents = []
    for incident in raw.get("incidents") or []:
        if not isinstance(incident, dict):
            continue
        updates = incident.get("incident_updates") or []
        latest = updates[0] if updates and isinstance(updates[0], dict) else {}
        said = _text(latest.get("body"))
        name = _text(incident.get("name")) or "An incident"
        state = _text(incident.get("status")).replace("_", " ")
        incidents.append(f"{name}, {state}." + (f" Latest: {said}" if said else ""))
    return ServiceStatus(f"GitHub says: {overall}.".replace("..", "."), trouble, incidents)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def read_status(timeout: float = 15.0) -> ServiceStatus:
    """Read the status page: HTTPS, verified TLS, no redirects, nothing sent but the request."""
    opener = build_opener(HTTPSHandler(context=verified_ssl_context()), _NoRedirect())
    request = Request(STATUS_URL, headers={"User-Agent": "QUILL", "Accept": "application/json"})
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = json.loads(response.read(512 * 1024).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - every failure is one sentence
        raise ServiceStatusError(
            f"QUILL could not read GitHub's status page: {exc}. Try again in a moment."
        ) from exc
    if not isinstance(raw, dict):
        raise ServiceStatusError("GitHub's status page answered with something QUILL cannot read.")
    return parse_summary(raw)


def consented() -> bool:
    """Whether the person has agreed to the status page being read."""
    path = app_data_dir() / _CONSENT_FILE
    data = read_json(path, default={}) if path.exists() else {}
    return bool(data.get("accepted", False)) if isinstance(data, dict) else False


def record_consent() -> None:
    write_json_atomic(app_data_dir() / _CONSENT_FILE, {"accepted": True})
