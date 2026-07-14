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
import platform
import sys
import time
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quill import __version__
from quill.core.paths import app_data_dir, ensure_app_directories
from quill.stability.redaction import (
    BundleRedactionStats,
    filter_recent_commands,
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
        archive.writestr("metadata.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
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


def _snapshot_task(task: object) -> dict[str, Any]:
    # ``is_dataclass`` returns True for both dataclass *classes* and
    # dataclass *instances*; ``asdict`` rejects the class form. Filter
    # to instances only so the type checker is happy and the runtime
    # never tries to ``asdict()`` a class.
    if is_dataclass(task) and not isinstance(task, type):
        data = asdict(task)  # type: ignore[arg-type]
    elif hasattr(task, "__dict__"):
        data = dict(task.__dict__)
    else:
        data = {"repr": repr(task)}
    data.pop("future", None)
    return data
