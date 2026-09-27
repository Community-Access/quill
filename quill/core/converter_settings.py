"""What Quill Converter remembers between runs.

A converter used for one job -- "make my voice memos MP3" -- is used for the
same job again, and making somebody re-choose the format, preset, effects and
output folder every time is making them re-listen to four combo boxes. So the
last choices are kept in ``converter.json`` in the app's data folder (the
portable ``data\\`` folder when running from a stick), written atomically,
and read forgivingly: an unknown or damaged value falls back to the default
rather than stopping the app from opening.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from quill.core.audio.dsp import DspOptions

FILE_NAME = "converter.json"

#: Stamped into every save (the persistence contract); bump it, and teach
#: ``from_json`` the old shape, when a field changes meaning.
SCHEMA = 1


@dataclass(slots=True)
class ConverterSettings:
    """The Converter's remembered choices."""

    fmt: str = "mp3"
    audio_preset: str = "just_convert"
    video_preset: str = "video_same"
    effect: str = "none"
    chapters: str = "keep"  # quill.core.audio.chapter_plan: keep, list, pauses, every-N, none
    custom_effects: DspOptions = field(default_factory=DspOptions)
    dest_dir: str = ""
    start_s: float = 0.0
    end_s: float = 0.0
    on_existing: str = "rename"
    open_folder_when_done: bool = False
    # View > Advanced Options and what it holds (quill/apps/converter_advanced.py).
    # Empty strings are each choice's neutral "use the preset / keep the file's own".
    show_advanced: bool = False
    adv_bitrate: str = ""
    adv_rate: str = ""
    adv_channels: str = "keep"
    adv_depth: str = ""
    adv_polish: str = ""
    recurse: bool = True

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["custom_effects"] = asdict(self.custom_effects)
        return data

    @classmethod
    def from_json(cls, data: object) -> ConverterSettings:
        if not isinstance(data, dict):
            return cls()
        out = cls()
        for item in fields(cls):
            if item.name == "custom_effects" or item.name not in data:
                continue
            value = data[item.name]
            default = getattr(out, item.name)
            if isinstance(default, bool):
                if isinstance(value, bool):
                    setattr(out, item.name, value)
            elif isinstance(default, float):
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                    setattr(out, item.name, float(value))
            elif isinstance(value, str):
                setattr(out, item.name, value)
        out.custom_effects = _dsp_from_json(data.get("custom_effects"))
        return out


def _dsp_from_json(data: object) -> DspOptions:
    if not isinstance(data, dict):
        return DspOptions()
    base = DspOptions()
    values: dict[str, Any] = {}
    for item in fields(DspOptions):
        if item.name not in data:
            continue
        value, default = data[item.name], getattr(base, item.name)
        if isinstance(default, bool) and isinstance(value, bool):
            values[item.name] = value
        elif (
            isinstance(default, float)
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            values[item.name] = float(value)
        elif isinstance(default, str) and isinstance(value, str):
            values[item.name] = value
    return DspOptions(**values)


def settings_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    return data_dir / FILE_NAME


def load(data_dir: Path | None = None) -> ConverterSettings:
    """The remembered choices, or the defaults when there are none."""
    from quill.core.storage import read_json

    return ConverterSettings.from_json(read_json(settings_path(data_dir), {}))


def save(settings: ConverterSettings, data_dir: Path | None = None) -> None:
    """Remember *settings* (atomic; a failure to save is never fatal)."""
    from quill.core.storage import write_json_atomic

    try:
        write_json_atomic(settings_path(data_dir), {"schema": SCHEMA, **settings.to_json()})
    except OSError:
        pass
