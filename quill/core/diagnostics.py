from __future__ import annotations

import hashlib
import json
import locale
import platform
import re
import sys
import zipfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from quill.core.document import Document
from quill.core.glow import glow_engine_version_summary
from quill.core.notifications import Notification
from quill.core.paths import app_data_dir
from quill.core.settings import Settings
from quill.core.storage import read_json, write_json_atomic

_SECRET_PREFIX_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s\"']+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)[^\s\"',]+"),
    re.compile(r"(?i)(x-api-key\s*[:=]\s*)[^\s\"',]+"),
    re.compile(r"(?i)(x-goog-api-key\s*[:=]\s*)[^\s\"',]+"),
    re.compile(r"(?i)(api[-_ ]?key\s*[:=]\s*)[^\s\"',]+"),
    re.compile(r"(?i)((?:access|secret|client)[-_ ]?(?:key|token|secret)\s*[:=]\s*)[^\s\"',]+"),
    re.compile(r"(?i)(\b(?:password|passwd|pwd|secret|token)\s*[:=]\s*)[^\s\"',]+"),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._-]{12,}"),
)
_SECRET_INLINE_PATTERNS = (
    re.compile(r"(?i)sk-[a-z0-9_-]{8,}"),  # OpenAI / Anthropic style
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),  # Google API keys
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key IDs
    re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}"),  # GitHub tokens
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),  # Slack tokens
)

# Settings field names that should never appear in diagnostics, matched by
# substring (case-insensitive) so future secret-bearing fields are covered.
_SECRET_FIELD_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "passwd",
    "credential",
    "private_key",
)


@dataclass(frozen=True, slots=True)
class DiagnosticEvent:
    timestamp: str
    kind: str
    name: str
    detail: str = ""


def diagnostic_events_path() -> Path:
    return app_data_dir() / "diagnostics" / "recent-actions.json"


def load_diagnostic_events(limit: int = 50) -> list[DiagnosticEvent]:
    raw = read_json(diagnostic_events_path(), default=[])
    if not isinstance(raw, list):
        return []
    items: list[DiagnosticEvent] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        timestamp = str(entry.get("timestamp", "")).strip()
        kind = str(entry.get("kind", "")).strip()
        name = str(entry.get("name", "")).strip()
        detail = str(entry.get("detail", "")).strip()
        if not timestamp or not kind or not name:
            continue
        items.append(DiagnosticEvent(timestamp=timestamp, kind=kind, name=name, detail=detail))
    return items[-limit:]


def record_diagnostic_event(kind: str, name: str, detail: str = "", limit: int = 50) -> None:
    events = load_diagnostic_events(limit=limit)
    events.append(
        DiagnosticEvent(
            timestamp=datetime.now(UTC).isoformat(),
            kind=kind.strip(),
            name=name.strip(),
            detail=detail.strip(),
        )
    )
    write_json_atomic(diagnostic_events_path(), [asdict(item) for item in events[-limit:]])


def write_diagnostics_bundle(
    target: Path,
    *,
    settings: Settings,
    keymap: dict[str, str],
    notifications: list[Notification],
    current_document: Document | None,
    include_file_paths: bool = False,
    extra_environment: dict[str, object] | None = None,
) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    metadata = collect_environment_info(extra_environment=extra_environment)
    if current_document is not None:
        metadata["current_document"] = document_snapshot(
            current_document,
            include_file_paths=include_file_paths,
        )
    recent_actions = [asdict(item) for item in load_diagnostic_events()]
    settings_payload = redact_settings(settings)
    notifications_payload = [asdict(entry) for entry in notifications[-50:]]

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
        archive.writestr(
            "recent-actions.json",
            json.dumps(recent_actions, indent=2, ensure_ascii=False) + "\n",
        )
        archive.writestr(
            "settings-redacted.json",
            json.dumps(settings_payload, indent=2, ensure_ascii=False) + "\n",
        )
        archive.writestr("keymap.json", json.dumps(keymap, indent=2, ensure_ascii=False) + "\n")
        archive.writestr(
            "notifications.json",
            json.dumps(notifications_payload, indent=2, ensure_ascii=False) + "\n",
        )
        _write_recent_logs(archive)
    return target


def build_diagnostics_review_text(
    *,
    settings: Settings,
    keymap: Mapping[str, str],
    notifications: list[Notification],
    current_document: Document | None,
    include_file_paths: bool,
    extra_environment: dict[str, object] | None = None,
) -> str:
    metadata = collect_environment_info(extra_environment=extra_environment)
    lines = [
        "Diagnostics Review",
        "",
        "Quill will create a local zip archive containing:",
        "- Redacted settings",
        "- Active keymap",
        f"- Up to {min(len(notifications), 50)} recent notifications",
        f"- Up to {len(load_diagnostic_events())} recent command and lifecycle events",
        "- Recent log files from the last 7 days, if present",
        "- Environment summary for support and troubleshooting",
    ]
    if current_document is not None:
        lines.append(f"- Current document snapshot for {current_document.name}")
        if include_file_paths:
            lines.append("- Plain file path included")
        else:
            lines.append("- File path will be hashed before export")
    lines.extend([
        "",
        f"Quill version: {metadata['quill_version']}",
        f"Platform: {metadata['platform']}",
        f"Python: {metadata['python_version']}",
        f"Keymap entries: {len(keymap)}",
        f"Settings keys: {len(redact_settings(settings))}",
    ])
    return "\n".join(lines)


def build_bug_report_payload(
    *,
    current_document: Document | None,
    extra_environment: dict[str, object] | None = None,
    summary_override: str | None = None,
    happened: str | None = None,
    expected: str | None = None,
    steps: str | None = None,
    diagnostics_note: str | None = None,
    screen_reader_name: str | None = None,
    reporter_name: str | None = None,
    reporter_email: str | None = None,
) -> dict[str, str]:
    metadata = collect_environment_info(extra_environment=extra_environment)
    document_label = "No document open"
    if current_document is not None:
        snapshot = document_snapshot(current_document, include_file_paths=False)
        name = snapshot.get("name")
        if isinstance(name, str) and name.strip():
            document_label = name
    summary = (summary_override or "").strip() or f"Bug report: {document_label}"
    happened_text = (
        happened or ""
    ).strip() or "Please describe what happened and what you expected to happen."
    expected_text = (expected or "").strip() or "Please describe the expected behavior."
    steps_text = (steps or "").strip() or "Please list steps to reproduce."
    diagnostics_text = (diagnostics_note or "").strip() or (
        "If possible, attach a diagnostics bundle created from Help -> Save Diagnostics..."
    )
    env_lines = [
        f"- Quill version: {metadata['quill_version']}",
        f"- Platform: {metadata['platform']}",
        f"- Python: {metadata['python_version']}",
        f"- Locale: {metadata['locale']}",
        f"- Current document: {document_label}",
    ]
    if screen_reader_name:
        env_lines.append(f"- Screen reader: {screen_reader_name}")
    if reporter_name:
        env_lines.append(f"- Reported by: {reporter_name}")
    if reporter_email:
        env_lines.append(f"- Contact email: {reporter_email}")
    details = [
        "Issue details:",
        happened_text,
        "",
        "Expected behavior:",
        expected_text,
        "",
        "Steps to reproduce:",
        steps_text,
        "",
        "Environment summary:",
        *env_lines,
        "",
        diagnostics_text,
    ]
    return {
        "summary": summary,
        "body": "\n".join(details),
    }


def build_support_issue_url(
    payload: Mapping[str, str],
    *,
    source_app: str,
    version: str,
    platform_label: str,
    diagnostics_note: str | None = None,
) -> str:
    return "https://github.com/Community-Access/support/issues/new?" + urlencode({
        "template": "product-feedback.yml",
        "title": payload["summary"],
        "source-app": source_app,
        "category": "Bug report",
        "version": version,
        "platform": platform_label,
        "summary": payload["summary"],
        "happened": payload["body"],
        "diagnostics": diagnostics_note
        or ("If available, attach a diagnostics bundle created from Help -> Save Diagnostics..."),
    })


def collect_environment_info(
    extra_environment: dict[str, object] | None = None,
) -> dict[str, object]:
    info: dict[str, object] = {
        "quill_version": _safe_import_version(),
        "platform": platform.platform(),
        "windows_release": platform.release(),
        "python_version": sys.version.splitlines()[0],
        "locale": locale.getlocale(),
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    info["glow_engine"] = _safe_glow_engine_summary()
    if extra_environment:
        info.update(extra_environment)
    return info


def redact_settings(settings: Settings) -> dict[str, object]:
    payload = asdict(settings)
    for field_name in list(payload):
        lowered = field_name.lower()
        if any(marker in lowered for marker in _SECRET_FIELD_MARKERS):
            payload[field_name] = "[REDACTED]"
    return payload


def document_snapshot(document: Document, include_file_paths: bool) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "name": document.name,
        "modified": document.modified,
        "encoding": document.encoding,
        "line_ending": document.line_ending,
        "source_metadata": document.source_metadata,
    }
    if document.path is None:
        snapshot["path"] = None
    elif include_file_paths:
        snapshot["path"] = str(document.path)
    else:
        snapshot["path_hash"] = hashlib.sha256(str(document.path).encode("utf-8")).hexdigest()
    return snapshot


def _write_recent_logs(archive: zipfile.ZipFile) -> None:
    logs_dir = app_data_dir() / "logs"
    if not logs_dir.exists():
        return
    cutoff = datetime.now(UTC) - timedelta(days=7)
    for log_file in sorted(logs_dir.glob("*.log")):
        try:
            modified = datetime.fromtimestamp(log_file.stat().st_mtime, UTC)
        except OSError:
            continue
        if modified < cutoff:
            continue
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        archive.writestr(f"logs/{log_file.name}", _sanitize_log_text(text))


def _sanitize_log_text(text: str) -> str:
    sanitized = text
    for pattern in _SECRET_PREFIX_PATTERNS:
        sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
    for pattern in _SECRET_INLINE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def _safe_import_version() -> str:
    try:
        from quill import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "unknown"


def _safe_glow_engine_summary() -> str:
    try:
        return glow_engine_version_summary()
    except Exception:  # noqa: BLE001
        return "GLOW engine: unknown"
