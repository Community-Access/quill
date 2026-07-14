"""Safety contract for subprocess execution.

Implements: ROADMAP SEC-4 (documented and validated cwd safety for
``safe_subprocess``) and SEC-15 (validates ``cwd``, catches
``OSError``/``FileNotFoundError``, surfaces a clear re-raise).
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Sequence

from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)


def run_subprocess_safely(
    args: Sequence[str],
    *,
    timeout_seconds: float = 30.0,
    cwd: str | None = None,
    input: str | None = None,  # noqa: A002 - matches subprocess.run's own parameter name
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with a timeout and clear, logged failure handling.

    Safety contract (SEC-4):

    - ``args`` must be a non-empty sequence; the first element is the executable.
      Quill never builds these from untrusted document content — callers pass a
      fixed tool name (e.g. a bundled binary) plus controlled arguments.
    - ``cwd``, when provided, must already exist and be a directory. The working
      directory is validated before launch so a caller cannot accidentally point
      the child process at a missing or non-directory path; callers are expected
      to pass a trusted, absolute directory they control.
    - ``input``, when given, is piped to the child's stdin instead of being
      folded into ``args``. A payload of arbitrary/unbounded size (e.g. a
      whole document's text) must never become a command-line argument --
      Windows' CreateProcess has a roughly 32K total command-line length
      limit, so an argv-embedded payload silently fails to launch once a
      caller's input grows past that (braille_worker_client hit exactly this
      with a large document). Stdin has no such ceiling.

    Raises:
        ValueError: if ``args`` is empty or ``cwd`` is not an existing directory.
        subprocess.TimeoutExpired: if the process exceeds ``timeout_seconds``.
        OSError: if the executable cannot be launched (surfaced after logging).
    """

    arg_list = list(args)
    if not arg_list:
        raise ValueError("run_subprocess_safely requires a non-empty args sequence")
    if cwd is not None and not os.path.isdir(cwd):
        raise ValueError(f"cwd must be an existing directory: {cwd!r}")
    # H-1: log only the redacted form of the args list so secrets
    # (API keys, Authorization headers, etc.) never reach quill.log
    # and therefore never reach the crash bundle.
    safe_args = format_args_for_log(arg_list)
    logger.info(
        "Running subprocess %s timeout=%s cwd=%s",
        safe_args,
        timeout_seconds,
        cwd,
    )
    extra_kwargs: dict = {}
    if os.name == "nt":
        extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            arg_list,
            cwd=cwd,
            text=True,
            # #954: without an explicit encoding, subprocess.run decodes
            # stdout/stderr using the system's preferred locale encoding --
            # on Windows that is often a legacy code page (e.g. CP1252), not
            # UTF-8. Bundled tools like Pandoc always emit UTF-8 regardless of
            # the host locale, so a mismatched default decode could fail
            # inside the reader thread and silently leave stdout as None
            # (surfacing as "Pandoc succeeded but produced an empty
            # document," #954) rather than raising anywhere visible. UTF-8 is
            # forced here for every caller, and "replace" guarantees a
            # visible mojibake fallback instead of a silent empty result if a
            # tool ever emits genuinely non-UTF-8 bytes.
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            input=input,
            **extra_kwargs,
        )
        logger.info(
            "Subprocess finished returncode=%s %s",
            result.returncode,
            safe_args,
        )
        return result
    except subprocess.TimeoutExpired:
        logger.exception("Subprocess timed out %s timeout=%s", safe_args, timeout_seconds)
        raise
    except OSError as error:
        logger.exception("Subprocess failed to launch %s cwd=%s", safe_args, cwd)
        raise OSError(f"Could not run {arg_list[0]!r}: {error}") from error
