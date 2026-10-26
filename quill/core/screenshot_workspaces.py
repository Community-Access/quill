"""Named capture recipes: data only; never persist upload permission or output destinations."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic
from quill.core.studio_capture import CaptureTarget


def load_workspaces() -> dict[str, Any]:
    raw = read_json(app_data_dir() / "studio-capture-workspaces.json", {})
    return raw if isinstance(raw, dict) else {}


def save_workspace(
    name: str,
    target: CaptureTarget,
    delay: int,
    count: int,
    interval: int,
    *,
    mode: str = "One screenshot",
) -> None:
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("Give this setup a name, up to 100 characters.")
    if not 0 <= delay <= 60 or not 1 <= count <= 30 or not 1 <= interval <= 60:
        raise ValueError("Choose a valid delay, 1–30 captures and 1–60 seconds between captures.")
    raw = load_workspaces()
    raw[name] = {
        "target": asdict(target),
        "delay": delay,
        "count": count,
        "interval": interval,
        "mode": mode,
    }
    if len(raw) > 100:
        raise ValueError("Remove an unused setup before saving another; the limit is 100.")
    write_json_atomic(app_data_dir() / "studio-capture-workspaces.json", raw)


def workspace_target(name: str) -> tuple[CaptureTarget, int, int, int]:
    raw = load_workspaces()[name]
    target = raw["target"]
    # Explicit schema: imported/edited JSON cannot add commands, URLs or credentials.
    result = CaptureTarget(
        kind=target["kind"],
        label=str(target["label"]),
        bounds=cast(tuple[int, int, int, int], tuple(int(v) for v in target["bounds"])),
        window_handle=int(target.get("window_handle", 0)),
        process_id=int(target.get("process_id", 0)),
        device=str(target.get("device", "")),
        application=str(target.get("application", "")),
        reference_bounds=cast(
            tuple[int, int, int, int],
            tuple(int(v) for v in target.get("reference_bounds", (0, 0, 0, 0))),
        ),
        element_id=tuple(int(v) for v in target.get("element_id", ())),
    )
    count, interval, delay = int(raw["count"]), int(raw["interval"]), int(raw["delay"])
    if result.kind not in {"window", "display", "desktop", "region", "element", "active_window"}:
        raise ValueError("Unsupported saved target. Remove this setup and choose a new one.")
    if (
        len(result.bounds) != 4
        or not 1 <= count <= 30
        or not 1 <= interval <= 60
        or not 0 <= delay <= 60
    ):
        raise ValueError("Invalid saved setup. Remove it and choose a new one.")
    return result, delay, count, interval


def remove_workspace(name: str) -> None:
    raw = load_workspaces()
    raw.pop(name, None)
    write_json_atomic(app_data_dir() / "studio-capture-workspaces.json", raw)
