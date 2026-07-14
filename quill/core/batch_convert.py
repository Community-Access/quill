"""Batch import / export loop over a folder of files (issue #262).

Drives :mod:`quill.core.pandoc_runner` across every file in a user-picked
folder. Pure core: no ``wx`` imports, no ``MainFrame`` calls, no ``announce``
calls. The UI layer passes a ``progress`` callback and (optionally) a
``threading.Event`` for cancel.

Output naming (issue #262 verbatim): the originating stem is preserved and
the extension is replaced with the target format's canonical extension. By
default the output lands in an ``Output/`` subfolder inside the source
folder (``output_layout="subfolder"``); the user can opt into
``output_layout="same_folder"`` to keep originals and conversions side by
side. The wizard overrides the setting.

Pure logic. No ``wx`` imports. Strict-typed; always in scope for ``mypy``.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from quill.core import convert_profiles, pandoc_formats
from quill.core.error_codes import CodedError
from quill.io.pandoc import (
    PandocCancelledError,
    PandocConversionError,
    PandocUnavailableError,
    convert_file_with_pandoc,
)

logger = logging.getLogger(__name__)


OverwritePolicy = Literal["ask", "never", "always"]
OutputLayout = Literal["same_folder", "subfolder"]


@dataclass(frozen=True, slots=True)
class BatchPlan:
    """Inputs the user picked in the wizard (or via the menu stub).

    ``profile`` is a :mod:`quill.core.convert_profiles` name or ``None``.
    ``overwrite`` is one of the three :data:`OverwritePolicy` values.
    ``output_layout`` is one of the two :data:`OutputLayout` values.
    """

    root: Path
    recursive: bool
    source_format: str
    target_format: str
    output_layout: OutputLayout
    overwrite: OverwritePolicy
    profile: str | None = None


@dataclass(frozen=True, slots=True)
class BatchEntry:
    """One file's outcome in a batch run."""

    source: Path
    output: Path | None
    success: bool
    warning_count: int
    error: str | None
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class BatchReport:
    """Aggregate result of a batch run.

    ``total`` is the number of files the iterator found. ``converted`` is the
    count of successful entries; ``skipped`` is the count of files the
    overwrite policy rejected (``overwrite="never"`` with an existing output);
    ``failed`` is the count of files where Pandoc itself returned an error.
    The Status Page row reads ``converted`` + ``failed``; the report dialog
    enumerates ``entries`` with warnings or failures so the screen reader can
    read each one in turn.
    """

    plan: BatchPlan
    total: int
    converted: int
    skipped: int
    failed: int
    entries: tuple[BatchEntry, ...]
    duration_seconds: float
    cancelled: bool = False


class OverwriteRequired(CodedError):
    code = "QUILL-CONVERT-BATCH-OVERWRITE"
    """Raised by :func:`run_batch` when the policy is ``"ask"`` and the output exists.

    The UI catches this once at the batch level (or per file in the future)
    and prompts the user. We do not bury the prompt in the core; keeping it
    visible means the policy semantics are testable from core tests alone.
    """

    def __init__(self, outputs: tuple[Path, ...]) -> None:
        super().__init__(f"Overwrite confirmation required for {len(outputs)} existing file(s).")
        self.outputs = outputs


ProgressCallback = Callable[[str, int, int], None]


def iter_target_files(
    root: Path,
    recursive: bool,
    source_format: str,
) -> Iterator[Path]:
    """Yield files in ``root`` whose extension matches ``source_format``.

    Filters by extension rather than by ``pandoc_format_for_path`` so we
    trust the wizard's source-format picker over the file's own extension —
    a folder of ``.txt`` files imported as Markdown should still be processed.
    """

    if not root.is_dir():
        return
    extensions = pandoc_formats.extensions_for(source_format)
    if not extensions:
        # Fall back to the extension lookup; at worst we miss nothing.
        extensions = frozenset({".md", ".markdown"})
    matches: list[Path]
    if recursive:
        matches = sorted(
            path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in extensions
        )
    else:
        matches = sorted(
            path for path in root.iterdir() if path.is_file() and path.suffix.lower() in extensions
        )
    yield from matches


def output_path_for(source: Path, plan: BatchPlan) -> Path:
    """Compute the destination path for ``source`` under ``plan``.

    Issue #262: keep the originating stem, replace the extension. ``Output/``
    subfolder when ``output_layout="subfolder"`` (default), the source folder
    itself when ``"same_folder"``. The output subfolder is created lazily by
    the caller; this function does not touch the filesystem.
    """

    target_exts = pandoc_formats.extensions_for(plan.target_format)
    # Pick the canonical output extension. Prefer the longer / more common form
    # so ``.html`` wins over ``.htm`` for screen-reader-friendlier filenames.
    new_ext = max(target_exts, key=len) if target_exts else ".out"
    new_name = source.stem + new_ext
    if plan.output_layout == "subfolder":
        return source.parent / "Output" / new_name
    return source.parent / new_name


def _pending_overwrite_outputs(plan: BatchPlan, sources: list[Path]) -> list[Path]:
    """Return the output paths that already exist (so the caller can prompt)."""

    return [output_path_for(src, plan) for src in sources if output_path_for(src, plan).exists()]


def run_batch(
    plan: BatchPlan,
    *,
    progress: ProgressCallback | None = None,
    cancel: threading.Event | None = None,
    per_file_timeout_seconds: float = 60.0,
    ask_overwrite: Callable[[Path], bool] | None = None,
) -> BatchReport:
    """Run the batch and return a :class:`BatchReport`.

    ``progress(message, current, total)`` is called once per file with the
    file name as message. ``cancel`` is honoured between files. ``ask_overwrite``
    is invoked when ``plan.overwrite == "ask"`` and the output already exists;
    it must return ``True`` to overwrite or ``False`` to skip. When
    ``ask_overwrite`` is ``None`` and the policy is ``"ask"``, the batch
    raises :class:`OverwriteRequired` so the UI can prompt at a higher level.
    """

    started = time.monotonic()
    sources = list(iter_target_files(plan.root, plan.recursive, plan.source_format))
    total = len(sources)

    if total == 0:
        if progress is not None:
            progress("No matching files found.", 0, 0)
        return BatchReport(
            plan=plan,
            total=0,
            converted=0,
            skipped=0,
            failed=0,
            entries=(),
            duration_seconds=time.monotonic() - started,
        )

    profile_flags = tuple(convert_profiles.flags_for_profile(plan.profile))

    # Honour the "ask" overwrite policy up-front by collecting every
    # would-overwrite path and prompting once. This is the batch-level
    # experience; per-file prompts would be screen-reader-hostile.
    if plan.overwrite == "ask" and ask_overwrite is None:
        pending = _pending_overwrite_outputs(plan, sources)
        if pending:
            raise OverwriteRequired(tuple(pending))

    entries: list[BatchEntry] = []
    converted = 0
    skipped = 0
    failed = 0
    cancelled = False

    for index, source in enumerate(sources, start=1):
        if cancel is not None and cancel.is_set():
            cancelled = True
            break

        if progress is not None:
            try:
                progress(f"{source.name}", index - 1, total)
            except Exception:  # noqa: BLE001
                logger.exception("batch_convert progress callback raised")

        destination = output_path_for(source, plan)
        # Ensure the destination parent exists. Done lazily per file so the
        # ``Output/`` subfolder is created on first write only.
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Overwrite policy enforcement (per file, after the batch-level ask).
        if destination.exists():
            if plan.overwrite == "never":
                entries.append(
                    BatchEntry(
                        source=source,
                        output=None,
                        success=False,
                        warning_count=0,
                        error="Output already exists; overwrite policy is 'never'.",
                        duration_seconds=0.0,
                    )
                )
                skipped += 1
                continue
            if plan.overwrite == "ask":
                if ask_overwrite is None or not ask_overwrite(destination):
                    entries.append(
                        BatchEntry(
                            source=source,
                            output=None,
                            success=False,
                            warning_count=0,
                            error="User declined to overwrite existing file.",
                            duration_seconds=0.0,
                        )
                    )
                    skipped += 1
                    continue

        file_started = time.monotonic()
        result_success: bool
        result_warnings: tuple[str, ...] = ()
        result_error: str | None
        try:
            convert_file_with_pandoc(
                source,
                destination,
                from_format=plan.source_format,
                to_format=plan.target_format,
                cancel=cancel,
                timeout_seconds=per_file_timeout_seconds,
                extra_args=tuple(profile_flags),
            )
            result_success = True
            result_error = None
        except PandocCancelledError as exc:
            cancelled = True
            entries.append(
                BatchEntry(
                    source=source,
                    output=None,
                    success=False,
                    warning_count=0,
                    error=str(exc),
                    duration_seconds=time.monotonic() - file_started,
                )
            )
            if progress is not None:
                try:
                    progress(
                        f"Cancelled at {source.name}",
                        index,
                        total,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("batch_convert progress callback raised")
            break
        except (PandocUnavailableError, PandocConversionError) as exc:
            result_success = False
            result_error = str(exc)
        file_duration = time.monotonic() - file_started

        entry = BatchEntry(
            source=source,
            output=destination if result_success else None,
            success=result_success,
            warning_count=len(result_warnings),
            error=None if result_success else result_error,
            duration_seconds=file_duration,
        )
        entries.append(entry)
        if result_success:
            converted += 1
        else:
            failed += 1

        if progress is not None:
            try:
                progress(f"{source.name} -> {destination.name}", index, total)
            except Exception:  # noqa: BLE001
                logger.exception("batch_convert progress callback raised")

    if progress is not None:
        try:
            progress(
                f"Done: {converted} converted, {skipped} skipped, {failed} failed.",
                total,
                total,
            )
        except Exception:  # noqa: BLE001
            logger.exception("batch_convert progress callback raised")

    return BatchReport(
        plan=plan,
        total=total,
        converted=converted,
        skipped=skipped,
        failed=failed,
        entries=tuple(entries),
        duration_seconds=time.monotonic() - started,
        cancelled=cancelled,
    )


__all__ = [
    "BatchEntry",
    "BatchPlan",
    "BatchReport",
    "OverwritePolicy",
    "OverwriteRequired",
    "OutputLayout",
    "iter_target_files",
    "output_path_for",
    "run_batch",
]
