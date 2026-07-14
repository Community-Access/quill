"""Pandoc integration for QUILL (issue #262 expands the existing module).

Historically this module only knew three output writers (``markdown``, ``html``,
``plain``) because the only caller was the legacy single-file "Pandoc
Conversion Wizard". Issue #262 widens that to a curated Tier-1 list of
eleven input formats and ten output formats, and adds a batch loop that
needs a real progress / cancel channel.

The public API stays the same: :func:`convert_document_with_pandoc` and
:func:`convert_file_with_pandoc` are the only two functions. Both now
accept any Tier-1 format from :mod:`quill.core.pandoc_formats` and take an
optional ``progress`` callback and ``cancel`` event. The ``WRITER_MAP``
legacy alias is kept as a default for the old single-file wizard.

Safety:

* The subprocess is launched via
  :func:`quill.stability.safe_subprocess.run_subprocess_safely` so the
  redact-args-in-logs contract applies and a missing Pandoc surfaces as a
  clean :class:`PandocUnavailableError` rather than an ``OSError`` from
  inside ``subprocess.run``.
* Cancellation is cooperative: the cancel ``Event`` is checked before the
  subprocess is spawned. We do not attempt to terminate Pandoc mid-run
  (Pandoc reads most inputs eagerly; adding a control protocol for a
  one-shot tool is overkill). The batch loop's between-file granularity is
  what cancellation actually means in practice.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core import pandoc_formats
from quill.core.external_tools import ExternalToolStatus, get_external_tool_status
from quill.stability.safe_subprocess import run_subprocess_safely

logger = logging.getLogger(__name__)

# Legacy alias kept for the existing single-file wizard. New callers should
# pass a Tier-1 format name from :mod:`quill.core.pandoc_formats` directly.
WRITER_MAP: dict[str, str] = {
    "markdown": "gfm",
    "html": "html5",
    "plain": "plain",
}

# Pandoc writers that produce a binary file and cannot be written to stdout.
# convert_document_with_pandoc captures stdout as text, so asking it for one of
# these is a programming error -- Pandoc would otherwise fail with the cryptic
# "Cannot write <fmt> output to terminal". We reject it up front with a clear
# message so the mistake surfaces wherever it is made.
_BINARY_WRITERS: frozenset[str] = frozenset({"docx", "odt", "epub", "pdf", "pptx"})

ProgressCallback = Callable[[str, int, int], None]


class PandocUnavailableError(RuntimeError):
    pass


class PandocConversionError(RuntimeError):
    pass


class PandocCancelledError(RuntimeError):
    """Raised when a cancel event was set before the conversion started."""


@dataclass(frozen=True, slots=True)
class PandocConversionResult:
    text: str
    output_kind: str
    source_path: Path
    pandoc_path: str


# ---------------------------------------------------------------------------
# Text conversion (used when the target is editable in QUILL).
# ---------------------------------------------------------------------------


def convert_document_with_pandoc(
    source_path: Path,
    output_kind: str,
    tool_status: ExternalToolStatus | None = None,
    *,
    from_format: str = "markdown",
    progress: ProgressCallback | None = None,
    cancel: threading.Event | None = None,
) -> PandocConversionResult:
    """Convert ``source_path`` to text and return the text in the result.

    ``output_kind`` is the Tier-1 output format name (e.g. ``"html"``,
    ``"markdown"``, ``"plain_text"``). The actual Pandoc ``--to`` flag is
    resolved from :data:`WRITER_MAP` for the legacy three values, or passed
    through directly for newer Tier-1 names. The caller is expected to pick
    a format that produces text (i.e. not DOCX, EPUB, PDF).
    """

    status = tool_status or get_external_tool_status("pandoc")
    if not status.installed or not status.path:
        raise PandocUnavailableError("Pandoc is not installed or bundled with Quill.")
    if not source_path.is_file():
        raise PandocConversionError(f"Input file not found: {source_path}")

    writer = _resolve_writer(output_kind)
    if writer in _BINARY_WRITERS:
        raise PandocConversionError(
            f"{output_kind!r} is a binary format and cannot be read into the editor as "
            "text. Choose a text output (markdown, html, or plain text)."
        )
    if cancel is not None and cancel.is_set():
        raise PandocCancelledError("Cancelled before start.")

    if progress is not None:
        try:
            progress("start", 0, 1)
        except Exception:  # noqa: BLE001
            logger.exception("pandoc progress callback raised on start")

    command = [
        str(status.path),
        str(source_path),
        "--from",
        from_format,
        "--to",
        writer,
        "--wrap=none",
    ]
    if output_kind == "html":
        command.append("--standalone")
    try:
        completed = run_subprocess_safely(
            command, timeout_seconds=60.0, cwd=str(source_path.parent)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_exception(exc) from exc

    if cancel is not None and cancel.is_set():
        raise PandocCancelledError("Cancelled during run.")

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or str(completed.returncode)
        raise PandocConversionError(details)

    # #954: a successful returncode with no stdout is not a valid empty
    # document -- it means the subprocess's stdout capture failed silently
    # (the historical cause was a locale-encoding mismatch on the reader
    # thread, now fixed in run_subprocess_safely, but this guard stays as a
    # second line of defense). Silently returning text=None here surfaced to
    # the user as "Pandoc succeeded but produced an empty document."
    if completed.stdout is None:
        raise PandocConversionError(
            "Pandoc reported success but produced no output. This usually means its "
            "output could not be decoded; please report this as a bug."
        )

    if progress is not None:
        try:
            progress("done", 1, 1)
        except Exception:  # noqa: BLE001
            logger.exception("pandoc progress callback raised on done")

    return PandocConversionResult(
        text=completed.stdout,
        output_kind=output_kind,
        source_path=source_path,
        pandoc_path=str(status.path),
    )


# ---------------------------------------------------------------------------
# File conversion (used when the target is a binary file on disk).
# ---------------------------------------------------------------------------


def convert_file_with_pandoc(
    source_path: Path,
    target_path: Path,
    *,
    from_format: str,
    to_format: str,
    tool_status: ExternalToolStatus | None = None,
    progress: ProgressCallback | None = None,
    cancel: threading.Event | None = None,
    timeout_seconds: float = 120.0,
    extra_args: tuple[str, ...] = (),
    resolve_writer: bool = True,
) -> Path:
    """Convert ``source_path`` to ``target_path`` via Pandoc.

    Used for binary outputs (DOCX, EPUB, PDF, ODT, RTF) and for the batch
    loop's "write to disk" path. ``from_format`` and ``to_format`` are
    Tier-1 format names from :mod:`quill.core.pandoc_formats`; the runner
    resolves the actual Pandoc ``--to`` flag via :func:`_resolve_writer`.

    ``resolve_writer=False`` skips that legacy aliasing and uses ``to_format``
    as a literal Pandoc writer token. The Convert File dialog passes real
    Pandoc tokens (e.g. ``"markdown"`` for Pandoc-flavoured Markdown) and must
    not have them remapped (``markdown`` -> ``gfm``). An empty ``from_format``
    lets Pandoc infer the reader from the input file extension.
    """

    status = tool_status or get_external_tool_status("pandoc")
    if not status.installed or not status.path:
        raise PandocUnavailableError("Pandoc is not installed or bundled with Quill.")
    if not source_path.is_file():
        raise PandocConversionError(f"Input file not found: {source_path}")

    writer = _resolve_writer(to_format) if resolve_writer else to_format.strip()
    if not writer:
        raise ValueError("Pandoc output kind must be a non-empty writer name")

    if cancel is not None and cancel.is_set():
        raise PandocCancelledError("Cancelled before start.")

    if progress is not None:
        try:
            progress("start", 0, 1)
        except Exception:  # noqa: BLE001
            logger.exception("pandoc progress callback raised on start")

    command = [str(status.path)]
    # An empty ``from_format`` lets Pandoc infer the reader from the input file
    # extension. The broader Convert File catalogue relies on this for inputs
    # that are not in the curated reader map.
    if from_format.strip():
        command += ["--from", from_format]
    command += [
        "--to",
        writer,
        "-o",
        str(target_path),
        *extra_args,
        str(source_path),
    ]
    try:
        completed = run_subprocess_safely(
            command, timeout_seconds=timeout_seconds, cwd=str(source_path.parent)
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_exception(exc) from exc

    if cancel is not None and cancel.is_set():
        raise PandocCancelledError("Cancelled during run.")

    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or str(completed.returncode)
        raise PandocConversionError(details)

    if not target_path.exists():
        raise PandocConversionError(f"Pandoc reported success but did not produce {target_path}.")

    if progress is not None:
        try:
            progress("done", 1, 1)
        except Exception:  # noqa: BLE001
            logger.exception("pandoc progress callback raised on done")

    return target_path


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _resolve_writer(output_kind: str) -> str:
    """Map a Tier-1 output name to the actual Pandoc ``--to`` value.

    Legacy values (``markdown`` -> ``gfm``, ``html`` -> ``html5``) keep
    their mapping for the existing single-file wizard. Newer Tier-1 names
    pass through unchanged: ``docx``, ``odt``, ``rtf``, ``epub``, ``pdf``,
    ``plain_text``, ``latex``, ``csv``, ``commonmark``, ``gfm`` are valid
    Pandoc writers as-is. ``plain_text`` is normalised to ``plain`` for
    Pandoc's CLI.
    """

    if output_kind in WRITER_MAP:
        return WRITER_MAP[output_kind]
    if output_kind == "plain_text":
        return "plain"
    if output_kind in pandoc_formats.TIER1_OUTPUTS:
        return output_kind
    # Broader Convert File catalogue: pass an arbitrary Pandoc writer token
    # (e.g. "rst", "asciidoc", "org", "html5") through unchanged. Pandoc itself
    # validates the writer and produces a clear error for an unknown one, so we
    # no longer reject it here. An empty token is still a programming error.
    if not output_kind.strip():
        raise ValueError("Pandoc output kind must be a non-empty writer name")
    return output_kind


def _map_exception(exc: BaseException) -> RuntimeError:
    """Translate a subprocess / OS exception into a Pandoc error class."""

    import subprocess

    if isinstance(exc, subprocess.TimeoutExpired):
        return PandocConversionError("Pandoc conversion timed out.")
    if isinstance(exc, OSError):
        return PandocUnavailableError(str(exc))
    return PandocConversionError(f"Pandoc invocation failed: {exc}")
