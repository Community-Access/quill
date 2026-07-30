"""``.quilljob`` files — a portable, hand-editable Audio Studio run recipe.

A job file pins one complete Audio Studio run (every
:class:`~quill.ui.audio_studio.request.BatchSpeechRequest` field): generate it
from the wizard's summary page, keep it beside the project or mail it to a
colleague, edit it in Notepad, and load it back on the Studio's first page to
re-run the exact same build. The ChapterForge ``.cfjob`` idea, re-based on
QUILL's request contract and atomic-write invariant.

Format: UTF-8 JSON with a ``format`` marker and a flat ``request`` object.
Unknown keys are ignored and missing keys keep the caller's defaults, so a
hand-edited or older file loads gracefully. wx-free, strict-typed.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError

JOB_EXTENSION = ".quilljob"
_FORMAT = "quill-audio-studio-job"
_VERSION = 1

# Extensions people commonly pick here by mistake, thinking this button adds a
# document to narrate. Seeing one lets us steer them to the right journey
# instead of leaking a decode error for a binary file (a .docx is a ZIP).
_DOCUMENT_SUFFIXES = frozenset({
    ".docx",
    ".docm",
    ".doc",
    ".rtf",
    ".odt",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".txt",
    ".pdf",
    ".epub",
})

_NARRATE_HINT = (
    " To narrate a document, go back to the first page, choose “Narrate "
    "documents into an audiobook,” and pick the folder that contains it. "
    "This button only reopens a job file you saved earlier from a finished run."
)


class JobFileError(CodedError):
    """The file is not a readable Audio Studio job; message is speakable."""

    code = "QUILL-SPEECH-JOBFILE-INVALID"


def _not_a_job_message(path: Path) -> str:
    """A speakable explanation for a file that is not a QUILL job file."""
    base = "That is not a QUILL Audio Studio job file."
    if path.suffix.lower() in _DOCUMENT_SUFFIXES:
        return base + _NARRATE_HINT
    return base


def save_job(path: Path, request: Any) -> Path:
    """Write *request* (a BatchSpeechRequest) to *path* atomically."""
    from quill.core.storage import write_json_atomic

    body = dataclasses.asdict(request)
    body.pop("_voice_label", None)
    body.pop("preview", None)
    body["source_folder"] = str(request.source_folder)
    document = {"format": _FORMAT, "version": _VERSION, "request": body}
    if path.suffix.lower() != JOB_EXTENSION:
        path = path.with_suffix(JOB_EXTENSION)
    write_json_atomic(path, document)
    return path


def load_job(path: Path, defaults: Any) -> Any:
    """Read *path* onto a copy of *defaults*; unknown/missing keys are tolerated.

    Raises :class:`JobFileError` when the file is not a QUILL job file at all.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise JobFileError(f"Could not open that file: {exc}") from exc
    # A job file is small UTF-8 JSON. A binary file (e.g. a .docx, which is a
    # ZIP) fails to decode; a text file that is not our JSON fails to parse.
    # Either way the file simply is not a job — say so, never leak the codec
    # or parser detail, which is meaningless read aloud by a screen reader.
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise JobFileError(_not_a_job_message(path)) from exc
    if not isinstance(document, dict) or document.get("format") != _FORMAT:
        raise JobFileError(_not_a_job_message(path))
    body = document.get("request")
    if not isinstance(body, dict):
        raise JobFileError("That job file has no request in it.")

    request = dataclasses.replace(defaults)
    valid = {f.name: f for f in dataclasses.fields(request)}
    for key, value in body.items():
        if key not in valid or key.startswith("_") or key == "preview":
            continue
        current = getattr(request, key)
        if key == "source_folder":
            setattr(request, key, Path(str(value)))
        elif isinstance(current, bool):
            setattr(request, key, bool(value))
        elif isinstance(current, int):
            try:
                setattr(request, key, int(value))
            except (TypeError, ValueError):
                pass
        elif isinstance(current, float):
            try:
                setattr(request, key, float(value))
            except (TypeError, ValueError):
                pass
        elif isinstance(current, str):
            setattr(request, key, str(value))
        elif isinstance(current, tuple) and isinstance(value, list):
            if key == "translation_targets":
                setattr(
                    request,
                    key,
                    tuple(
                        (str(t[0]), str(t[1]), str(t[2]))
                        for t in value
                        if isinstance(t, (list, tuple)) and len(t) == 3
                    ),
                )
            elif key == "casting_rules":
                setattr(
                    request,
                    key,
                    tuple(
                        (str(t[0]), str(t[1]))
                        for t in value
                        if isinstance(t, (list, tuple)) and len(t) == 2
                    ),
                )
            else:
                setattr(request, key, tuple(str(v) for v in value))
    return request
