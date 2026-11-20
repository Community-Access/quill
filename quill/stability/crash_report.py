"""Crash report and diagnostic bundle construction.

Implements: ROADMAP STAB-2 (the diagnostic-bundle path the user
chooses from Help > Save Diagnostics) and H-2/H-3 from the pre-release
review (redacted bundle; no document content in logs). The bundle
is built in two passes through :mod:`quill.stability.redaction` so
secrets and personally identifying information never leave the user
machine in plaintext, even when the user shares the bundle with
support.
"""

from __future__ import annotations

import json
import logging
import math
import platform
import sys
import time
import zipfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quill import __version__
from quill.core.paths import app_data_dir, ensure_app_directories
from quill.stability.redaction import (
    BundleRedactionStats,
    filter_recent_commands,
    redact_text_for_bundle,
    redact_text_for_bundle_with_stats,
)

logger = logging.getLogger(__name__)


def _display_version() -> str:
    """The channel-annotated version ("0.9.0 Beta 2"), never the bare number.

    Falls back to ``__version__`` when build metadata is absent (dev runs).
    """
    try:
        from quill.build_info import get_short_version

        return str(get_short_version())
    except Exception:  # noqa: BLE001 - version lookup must never break a report
        return __version__


def _collect_macos_diagnostic_reports(
    *, max_files: int = 5, max_age_days: int = 7, max_file_chars: int = 200_000
) -> dict[str, str]:
    """Collect recent macOS crash reports for this process (darwin only).

    Reads ``~/Library/Logs/DiagnosticReports/`` for ``.crash`` / ``.ips`` files
    whose name references Quill and that were modified within *max_age_days*.
    Returns ``{archive_label: raw_text}`` for the most recent *max_files*, each
    truncated to *max_file_chars*. Non-darwin platforms return an empty dict so
    the diagnostic bundle is unchanged on Windows/Linux (#42).
    """
    if sys.platform != "darwin":
        return {}
    reports_dir = Path.home() / "Library" / "Logs" / "DiagnosticReports"
    if not reports_dir.is_dir():
        return {}
    cutoff = time.time() - max_age_days * 86400
    candidates: list[tuple[float, Path]] = []
    for entry in reports_dir.iterdir():
        if not entry.is_file():
            continue
        name = entry.name.lower()
        if not (name.endswith(".crash") or name.endswith(".ips")):
            continue
        if "quill" not in name:
            continue
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        candidates.append((mtime, entry))
    candidates.sort(reverse=True)
    collected: dict[str, str] = {}
    for _mtime, entry in candidates[:max_files]:
        try:
            text = entry.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(text) > max_file_chars:
            text = text[:max_file_chars] + "\n...[truncated]\n"
        collected[f"macos/{entry.name}"] = text
    return collected


def build_diagnostic_bundle(
    *,
    logs_path: Path | None = None,
    fault_dump_path: Path | None = None,
    thread_dump_path: Path | None = None,
    memory_snapshot_path: Path | None = None,
    task_snapshot: Sequence[object] | None = None,
    feature_flags: Mapping[str, bool] | None = None,
    enabled_plugins: Sequence[str] | None = None,
    safe_mode: bool = False,
    recent_commands: Sequence[str] | None = None,
    wx_version: str | None = None,
    output_path: Path | None = None,
) -> Path:
    ensure_app_directories()
    output_dir = app_data_dir() / "diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: UP017
    bundle_path = output_path or output_dir / f"quill-diagnostic-bundle-{_ts}.zip"

    # H-3: only well-formed command ids are allowed in the bundle.
    # Anything else is dropped silently (the caller can compare the
    # length to detect a drop, but for the bundle itself we just
    # include the well-formed ones).
    safe_recent_commands = filter_recent_commands(recent_commands)

    # H-2: every text file included in the bundle is redacted through
    # the same helper. The redaction stats are recorded in
    # metadata.json so the user can see *what* was redacted.
    redaction_stats: dict[str, BundleRedactionStats] = {}

    payload: dict[str, Any] = {
        # #967/#968 triage lesson: bare __version__ says "0.9.0" for every
        # beta, so a crash from Beta 1 was indistinguishable from Beta 2 and a
        # fixed bug looked like a regression. Use the channel-annotated
        # display version ("0.9.0 Beta 2") everywhere reports carry a version.
        "quill_version": _display_version(),
        "python_version": sys.version.splitlines()[0],
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "safe_mode": safe_mode,
        "wx_version": wx_version,
        "feature_flags": dict(feature_flags or {}),
        "enabled_plugins": list(enabled_plugins or []),
        "recent_commands": safe_recent_commands,
    }
    if task_snapshot is not None:
        payload["active_tasks"] = [_snapshot_task(task) for task in task_snapshot]

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        # Build the bundle in two passes: first, redact every text
        # file so the redaction stats are known; then write
        # metadata.json with the stats and the redacted text bodies.
        # H-2 contract: metadata.json must include the redaction
        # counters so the user can see the bundle was sanitized.
        redacted_texts: dict[str, str] = {}
        for label, path in (
            ("quill.log", logs_path),
            ("faulthandler.log", fault_dump_path),
            ("thread-dump.log", thread_dump_path),
            ("memory-snapshot.txt", memory_snapshot_path),
        ):
            if path is None or not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            redacted, file_stats = redact_text_for_bundle_with_stats(text)
            redaction_stats[label] = file_stats
            redacted_texts[label] = redacted

        # #42: macOS-native forensic data -- recent crash reports from
        # ~/Library/Logs/DiagnosticReports/. Inert on non-darwin (returns {}).
        for label, raw_text in _collect_macos_diagnostic_reports().items():
            redacted, file_stats = redact_text_for_bundle_with_stats(raw_text)
            redaction_stats[label] = file_stats
            redacted_texts[label] = redacted

        if redaction_stats:
            payload["redaction"] = {
                label: stats.as_dict() for label, stats in redaction_stats.items()
            }
        # H-2: metadata.json also carries user-derived strings -- task names
        # embed document paths/titles, and plugin/feature identifiers can leak
        # local paths -- so every string in it is redacted with the same rules
        # as every other text file before it enters the archive. The values
        # are redacted and bounded *before* serializing, not the serialized
        # text afterwards: that line-by-line pass cut a long task name's line
        # at 200 characters, closing quote and all, and the file stopped being
        # JSON (plan.md, "Shared diagnostics and background-runtime review").
        metadata_json = _serialize_metadata(payload)
        archive.writestr("metadata.json", metadata_json + "\n")
        for label, body in redacted_texts.items():
            archive.writestr(label, body)
    if redaction_stats:
        total_dropped = sum(s.lines_dropped for s in redaction_stats.values())
        total_truncated = sum(s.lines_truncated for s in redaction_stats.values())
        if total_dropped or total_truncated:
            logger.info(
                "Diagnostic bundle redaction: %d lines dropped, %d lines truncated across %d files",
                total_dropped,
                total_truncated,
                len(redaction_stats),
            )
    return bundle_path


def _maybe_write_redacted(
    archive: zipfile.ZipFile,
    name: str,
    path: Path | None,
    stats: dict[str, BundleRedactionStats],
    stat_label: str,
) -> None:
    """Write ``path`` to the bundle after redaction.

    Mirrors :func:`_maybe_write_file` (kept below for any callers that
    want the unredacted behavior) but routes every text file through
    :func:`redact_text_for_bundle_with_stats` first. Files larger than
    a sanity cap are still skipped to avoid pulling a gigabyte of
    faulthandler output into a bundle.
    """

    if path is None or not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    redacted, file_stats = redact_text_for_bundle_with_stats(text)
    stats[stat_label] = file_stats
    archive.writestr(name, redacted)


def _maybe_write_file(archive: zipfile.ZipFile, name: str, path: Path | None) -> None:
    """Write a file into the archive *without* redaction.

    Kept for callers that explicitly want the raw content (e.g. a
    developer-only bundle) but should not be used by the default
    user-facing bundle path.
    """

    if path is None or not path.exists():
        return
    archive.write(path, arcname=name)


_SNAPSHOT_TASK_FIELDS = (
    "operation_id",
    "name",
    "started_at",
    "timeout_seconds",
    "safe_to_cancel",
    "safe_to_kill",
    "submitted_at",
    "result_summary",
)


#: How long one string in metadata.json may be after redaction. A task name or
#: a plugin id longer than this is cut with an ellipsis -- inside the string,
#: where the cut cannot break the file.
_MAX_METADATA_STRING = 200

#: How deep metadata.json may nest. Nothing QUILL writes nests past four; the
#: bound is only there so a self-referencing task attribute cannot recurse.
_MAX_METADATA_DEPTH = 8


def _redact_metadata_string(text: str) -> str:
    """One metadata string, redacted and bounded, never dropped."""
    redacted = redact_text_for_bundle(text)
    if text and not redacted.strip():
        # The bundle contract drops a line that is all secret; a JSON value
        # cannot vanish, so it says what happened instead.
        redacted = "[REDACTED]"
    if len(redacted) > _MAX_METADATA_STRING:
        redacted = redacted[:_MAX_METADATA_STRING] + "…"
    return redacted


def _redact_metadata_value(value: Any, depth: int = 0) -> Any:
    """*value* with every string in it -- keys too -- redacted and bounded."""
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        # NaN and infinity are not JSON; json.dumps would write them anyway.
        return value if math.isfinite(value) else str(value)
    if isinstance(value, str):
        return _redact_metadata_string(value)
    if depth >= _MAX_METADATA_DEPTH:
        return "[nested too deeply]"
    if isinstance(value, Mapping):
        return {
            _redact_metadata_string(str(key)): _redact_metadata_value(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple | set | frozenset):
        return [_redact_metadata_value(item, depth + 1) for item in value]
    return _redact_metadata_string(str(value))


def _serialize_metadata(payload: Mapping[str, Any]) -> str:
    """metadata.json's text: redacted value by value, then checked to parse.

    The check is the contract, not decoration: a diagnostic bundle support
    cannot open is worse than none, so a payload that somehow does not
    round-trip is replaced with one that says so.
    """
    safe = _redact_metadata_value(payload)
    text = json.dumps(safe, indent=2, ensure_ascii=False, allow_nan=False)
    try:
        json.loads(text)
    except ValueError:  # pragma: no cover - the walk above only emits JSON types
        logger.exception("Diagnostic bundle metadata did not round-trip as JSON")
        text = json.dumps({"error": "metadata could not be serialized"}, indent=2)
    return text


def _snapshot_task(task: object) -> dict[str, Any]:
    # A ``QuillTask`` carries a live ``future`` (whose internal ``RLock`` cannot
    # be pickled) and a ``cancellation_token`` wrapping a ``threading.Event``.
    # ``asdict`` deep-copies *every* field before we could drop them, which
    # raised ``TypeError: cannot pickle '_thread.RLock'`` whenever a task was in
    # flight -- breaking Save Diagnostics deterministically. Build the snapshot
    # field-by-field from the plain serialisable fields only, never touching the
    # future or the token.
    if any(hasattr(task, name) for name in _SNAPSHOT_TASK_FIELDS):
        return {name: getattr(task, name, None) for name in _SNAPSHOT_TASK_FIELDS}
    if hasattr(task, "__dict__"):
        data = dict(task.__dict__)
        data.pop("future", None)
        data.pop("cancellation_token", None)
        return data
    return {"repr": repr(task)}
