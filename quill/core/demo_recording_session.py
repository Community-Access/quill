"""What a demonstration recording saves: preferences, the crash-safe session file.

Split from :mod:`quill.core.demo_recording` (GATE-11). Two rules live here:
the microphone's *on* state is never written anywhere (MX-179), and
``session.json`` in a recording's hidden work folder holds enough to finish
the recording after a crash (REC-015).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from quill.core.demo_recording import (
    LEVEL_RANGE_DB,
    SESSION_FILE,
    WORK_PREFIX,
    CameraSetup,
    DemoPlan,
    DemoRecordingError,
    MarkerLog,
    SoundSource,
)
from quill.core.storage import read_json, write_json_atomic

#: Keys of a source that may be saved. ``enabled`` for the microphone is not
#: among them anywhere: MX-179 forbids remembering that a microphone was on.
_SAVED_SOURCE_KEYS = ("kind", "label", "source_id", "level_db", "device", "process_name")


def preferences_from_plan(plan: DemoPlan) -> dict[str, Any]:
    """What Studio remembers between recordings: settings, never open states."""
    sources = []
    for source in plan.sources:
        row: dict[str, Any] = {key: getattr(source, key) for key in _SAVED_SOURCE_KEYS}
        if source.kind == "application":
            row["enabled"] = source.enabled
        sources.append(row)
    return {
        "folder": plan.folder,
        "fps": plan.fps,
        "screen": plan.screen,
        "sound_format": plan.sound_format,
        "silent_track": plan.silent_track,
        "keep_awake": plan.keep_awake,
        "do_not_disturb": plan.do_not_disturb,
        "show_status_window": plan.show_status_window,
        "pointer": plan.pointer,
        "size_ceiling": plan.size_ceiling,
        "keep_stems": plan.keep_stems,
        "countdown": plan.countdown,
        "screen_reader": plan.screen_reader,
        "sources": sources,
        "camera": {
            "device": plan.camera.device,
            "position": plan.camera.position,
            "size_percent": plan.camera.size_percent,
            "face_alerts": plan.camera.face_alerts,
            "mirrored": plan.camera.mirrored,
        },
    }


def saved_level(preferences: dict[str, Any], source_id: str, default: float = 0.0) -> float:
    for row in preferences.get("sources", []) or []:
        if isinstance(row, dict) and row.get("source_id") == source_id:
            try:
                value = float(row.get("level_db", default))
            except (TypeError, ValueError):
                return default
            low, high = LEVEL_RANGE_DB
            return min(high, max(low, value))
    return default


@dataclass
class SegmentRecord:
    """One stretch between Start/Resume and Pause/Stop."""

    index: int
    folder: str
    video_start: float = 0.0
    camera_start: float = 0.0
    #: source_id -> wall time of the first captured sample.
    audio_starts: dict[str, float] = field(default_factory=dict)
    duration: float = 0.0
    closed: bool = False


@dataclass
class SessionRecord:
    """``session.json`` in the hidden work folder: enough to finish after a crash."""

    plan: dict[str, Any]
    output: str
    started: str
    segments: list[SegmentRecord] = field(default_factory=list)
    markers: list[dict[str, Any]] = field(default_factory=list)
    state: Literal["recording", "paused", "finalizing", "finished", "failed"] = "recording"

    def save(self, work: Path) -> None:
        data = asdict(self)
        # Defence in depth for MX-179: the plan snapshot never says the mic was on.
        for source in data["plan"].get("sources", []):
            if source.get("kind") == "microphone":
                source.pop("enabled", None)
        write_json_atomic(work / SESSION_FILE, data)

    @classmethod
    def load(cls, work: Path) -> SessionRecord:
        raw = read_json(work / SESSION_FILE, None)
        if not isinstance(raw, dict) or "output" not in raw:
            raise DemoRecordingError(f"{work.name} has no readable recording session.")
        segments = [
            SegmentRecord(**{k: v for k, v in seg.items() if k in SegmentRecord.__annotations__})
            for seg in raw.get("segments", [])
            if isinstance(seg, dict)
        ]
        return cls(
            plan=dict(raw.get("plan", {})),
            output=str(raw["output"]),
            started=str(raw.get("started", "")),
            segments=segments,
            markers=list(raw.get("markers", [])),
            state=raw.get("state", "recording"),
        )


def plan_to_dict(plan: DemoPlan) -> dict[str, Any]:
    return asdict(plan)


def plan_from_dict(data: dict[str, Any]) -> DemoPlan:
    sources = tuple(
        SoundSource(**{k: v for k, v in row.items() if k in SoundSource.__annotations__})
        for row in data.get("sources", [])
        if isinstance(row, dict)
    )
    camera_raw = dict(data.get("camera", {}) or {})
    if camera_raw.get("position") == "camera only":
        camera_raw["position"] = "bottom right"
        data = {**data, "screen": False}
    camera = CameraSetup(**{
        k: v for k, v in camera_raw.items() if k in CameraSetup.__annotations__
    })
    fields = {k: v for k, v in data.items() if k in DemoPlan.__annotations__}
    for key in ("bounds", "display_bounds"):
        if key in fields:
            fields[key] = tuple(fields[key])
    fields["sources"] = sources
    fields["camera"] = camera
    return DemoPlan(**fields)


def work_folder(output: Path, recording_id: str) -> Path:
    return output.parent / f"{WORK_PREFIX}{recording_id}"


def find_unfinished(folders: Iterable[Path]) -> list[Path]:
    """Hidden work folders a crash left behind, oldest first."""
    found: list[Path] = []
    for folder in folders:
        try:
            children = list(folder.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and child.name.startswith(WORK_PREFIX):
                if (child / SESSION_FILE).is_file():
                    found.append(child)
    return sorted(found, key=lambda path: path.stat().st_mtime)


def markers_from_session(session: SessionRecord) -> MarkerLog:
    log = MarkerLog()
    for row in session.markers:
        try:
            log.add(float(row["seconds"]), str(row["label"]), failure=bool(row.get("failure")))
        except (KeyError, TypeError, ValueError):
            continue
    return log


def with_source(plan: DemoPlan, source_id: str, **changes: Any) -> DemoPlan:
    sources = tuple(
        replace(source, **changes) if source.source_id == source_id else source
        for source in plan.sources
    )
    return replace(plan, sources=sources)


def describe_sources_json(plan: DemoPlan) -> str:
    """A compact, human-readable list for the verification report."""
    return json.dumps(
        [
            {
                "source": source.label,
                "kind": source.kind,
                "level_db": source.level_db,
                "left_out_of_system_sound": source.exclude_name or None,
            }
            for source in plan.enabled_sources()
        ],
        indent=2,
    )
