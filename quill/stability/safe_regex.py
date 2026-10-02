"""Bounded-time regex helpers built on the third-party ``regex`` package.

Implements: ROADMAP STAB-9 (ReDoS-safe regex: ``safe_finditer`` and
``safe_subn`` wrap user-supplied patterns with a per-call wall-clock
budget via :class:`RegexTimeoutError`; callers catch the timeout and
surface a clear error rather than hanging the worker).
"""

from __future__ import annotations

import functools
import logging
import time

try:
    import regex as _regex
    _HAVE_REGEX = True
except ImportError:  # pragma: no cover
    import re as _regex  # type: ignore[no-redef]
    _HAVE_REGEX = False

from quill.core.error_codes import CodedError

logger = logging.getLogger(__name__)


class RegexTimeoutError(CodedError):
    code = "QUILL-STABILITY-REGEX-TIMEOUT"


@functools.lru_cache(maxsize=128)
def _compile_cached(pattern: str, flags: int):
    return _regex.compile(pattern, flags)


def safe_finditer(
    pattern: str,
    text: str,
    *,
    timeout_seconds: float = 1.0,
    flags: int = 0,
):
    started = time.monotonic()
    try:
        compiled = _compile_cached(pattern, flags)
        if _HAVE_REGEX:
            matches = list(compiled.finditer(text, timeout=timeout_seconds))
        else:
            matches = list(compiled.finditer(text))
        duration_ms = (time.monotonic() - started) * 1000
        logger.info(
            "Regex search completed pattern_length=%d text_length=%d matches=%d duration_ms=%.1f",
            len(pattern),
            len(text),
            len(matches),
            duration_ms,
        )
        return matches
    except TimeoutError as exc:
        duration_ms = (time.monotonic() - started) * 1000
        logger.warning(
            "Regex search timed out pattern_length=%d text_length=%d timeout=%s duration_ms=%.1f",
            len(pattern),
            len(text),
            timeout_seconds,
            duration_ms,
        )
        raise RegexTimeoutError(
            "This regular expression search took too long and was stopped."
        ) from exc


def safe_subn(
    pattern: str,
    replacement: str,
    text: str,
    *,
    timeout_seconds: float = 1.0,
    flags: int = 0,
) -> tuple[str, int]:
    started = time.monotonic()
    try:
        compiled = _compile_cached(pattern, flags)
        if _HAVE_REGEX:
            updated, count = compiled.subn(replacement, text, timeout=timeout_seconds)
        else:
            updated, count = compiled.subn(replacement, text)
        duration_ms = (time.monotonic() - started) * 1000
        logger.info(
            (
                "Regex replace completed pattern_length=%d text_length=%d "
                "replacements=%d duration_ms=%.1f"
            ),
            len(pattern),
            len(text),
            count,
            duration_ms,
        )
        return updated, count
    except TimeoutError as exc:
        duration_ms = (time.monotonic() - started) * 1000
        logger.warning(
            "Regex replace timed out pattern_length=%d text_length=%d timeout=%s duration_ms=%.1f",
            len(pattern),
            len(text),
            timeout_seconds,
            duration_ms,
        )
        raise RegexTimeoutError(
            "This regular expression search took too long and was stopped."
        ) from exc
