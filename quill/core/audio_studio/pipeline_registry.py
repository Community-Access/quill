"""Process-wide registry of Quillin-supplied audio-processing steps.

A Quillin running in the Audio Studio may contribute a ``studio.pipeline`` step
that returns an ffmpeg filter fragment for a named processing stage (a
loudness normalizer, a de-esser). :class:`~quill.core.quillins.app_host.QuillinAppHost`
populates this registry from every enabled step contribution, and
:func:`quill.core.audio_enhance.build_filter_graph` (when a caller opts into a
pipeline stage) folds the fragments into the ffmpeg ``-af`` graph.

The registry is deliberately tiny and wx-free: a step is a callable
``(stage) -> str`` returning an ffmpeg filter fragment (e.g. ``"loudnorm"``), or
``""`` for nothing. The handler touches no audio bytes and makes no network call
of its own -- the host runs ffmpeg -- so consulting the registry never introduces
a new egress site.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

#: The stages a step may attach to (kept in lock-step with the schema enum and
#: ``quill.core.quillins.validation._PIPELINE_STAGES``).
PIPELINE_STAGES: tuple[str, ...] = ("pre", "master", "post")

#: A step callable. Given the ``stage`` being built, it returns an ffmpeg filter
#: fragment to append, or ``""`` when it contributes nothing for that stage.
PipelineStep = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class PipelineStepEntry:
    """A registered audio-processing step and the stage it attaches to."""

    step_id: str
    stage: str
    display_name: str
    handler: PipelineStep


_steps: list[PipelineStepEntry] = []


def register_step(step_id: str, stage: str, display_name: str, handler: PipelineStep) -> None:
    """Register (or replace, by id) an audio-processing step."""

    clear_step(step_id)
    _steps.append(PipelineStepEntry(step_id, stage, display_name, handler))


def clear_step(step_id: str) -> None:
    """Remove the step with ``step_id`` if present."""

    _steps[:] = [s for s in _steps if s.step_id != step_id]


def clear_steps() -> None:
    """Forget every registered step (a full host reload starts here)."""

    _steps.clear()


def registered_step_ids() -> tuple[str, ...]:
    """The ids of every currently registered step (for tests / diagnostics)."""

    return tuple(s.step_id for s in _steps)


def filters_for_stage(stage: str) -> list[str]:
    """Return the ffmpeg filter fragments every step contributes for ``stage``.

    Steps whose declared ``stage`` matches are consulted in registration order; a
    handler that raises, or returns an empty/blank fragment, is skipped so one
    faulty step never breaks the export graph.
    """

    fragments: list[str] = []
    for step in _steps:
        if step.stage != stage:
            continue
        try:
            fragment = step.handler(stage)
        except Exception:  # noqa: BLE001 - a faulty step must never break the graph
            continue
        if isinstance(fragment, str) and fragment.strip():
            fragments.append(fragment.strip())
    return fragments
