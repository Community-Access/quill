"""The exact-OptiLab pass over a finished radio recording.

Extracted from ``recording.py`` under GATE-11 (extract, never rebaseline) so
the recorder could gain its end-of-recording report without growing. The
recorder still owns *when* this runs (after the parts are joined, never during
the capture); this module owns *what* it does and what it says about it.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.radio.recording_commands import encode_args_for_format
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)


class _Settings(Protocol):
    format: str
    bitrate_kbps: int


class _Job(Protocol):
    @property
    def exact(self) -> ExactOptilab | None: ...

    @property
    def settings(self) -> _Settings: ...


def apply_exact_optilab(job: _Job, path: Path, notify: Callable[[str], None]) -> None:
    """Run the real OptiLab engine over the finished recording, if asked.

    Runs *after* the recording is over and after any parts are joined, never
    during the capture: an adapter fault mid-recording must not be able to
    cost somebody the recording they were making. The pass writes a temp file
    and replaces the original only on success, so the worst case here is a
    file that is exactly what was recorded, plus a spoken explanation.
    *notify* receives that one ready-to-speak sentence either way.
    """
    spec = job.exact
    if spec is None or not spec.active:
        return
    from quill.core.audio import exact_optilab

    if not exact_optilab.available():
        notify(
            f"{path.name} was saved without exact OptiLab processing. "
            f"{exact_optilab.unavailable_reason()}"
        )
        return
    encode_args = encode_args_for_format(job.settings.format, job.settings.bitrate_kbps)
    if not encode_args:
        return  # raw capture; nothing to re-encode into
    try:
        exact_optilab.process_in_place(path, spec, encode_args=encode_args)
    except Exception as exc:  # noqa: BLE001 - the recording itself is safe either way
        logger.warning("Exact OptiLab processing of %s failed: %s", path.name, exc)
        notify(f"{path.name} was saved, but exact OptiLab processing could not be applied: {exc}")
        return
    logger.info("Exact OptiLab processing applied to %s", format_args_for_log([str(path)]))
    notify(f"{path.name} was processed with the OptiLab engine.")
