"""Studio Normalizer -- a bundled sample ``studio.pipeline`` step.

Demonstrates the audio-processing-step capability for the Audio Studio: the
handler returns an ffmpeg filter fragment for a named stage, which the host
appends to the export/enhancement filter graph. It touches **no** audio bytes
and makes **no** network call -- the host runs ffmpeg -- so it needs no ``net``
capability (least privilege).

The out-of-process worker discards a handler's return value, so the fragment is
handed back by writing it to storage under ``_RESULT_KEY`` (kept in lock-step
with ``quill.core.quillins.app_host.PIPELINE_RESULT_KEY``); the host reads it
from the shared storage dict and appends it to the graph.
"""

from __future__ import annotations

# Must match quill.core.quillins.app_host.PIPELINE_RESULT_KEY.
_RESULT_KEY = "__quill_studio_pipeline_result__"

#: An EBU R128 loudness-normalization filter targeting -16 LUFS integrated, a
#: common target for spoken-word / audiobook narration.
_LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


def loudnorm_filter(api, event: dict) -> None:
    """Return the loudness-normalization fragment for the requested stage.

    ``event`` carries ``{"stage": ...}``. The sample only contributes to the
    ``master`` stage; for any other stage it returns nothing.
    """

    stage = str(event.get("stage", ""))
    api.set_storage(_RESULT_KEY, _LOUDNORM if stage == "master" else "")


def register(api) -> None:
    api.register_command("loudnorm_filter", loudnorm_filter)
    api.log("Studio Normalizer loaded")
