from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Macro:
    name: str
    steps: list[str] = field(default_factory=list)


def macros_path() -> Path:
    return app_data_dir() / "macros.json"


@dataclass(slots=True)
class MacroManager:
    macros: dict[str, Macro] = field(default_factory=dict)
    recording_name: str | None = None
    playing_back: bool = False
    last_macro_name: str | None = None

    @classmethod
    def load(cls, *, persistent: bool = True) -> MacroManager:
        if not persistent:
            return cls()
        raw = read_json(macros_path(), default={})
        if not isinstance(raw, dict):
            return cls()
        macros: dict[str, Macro] = {}
        for name, payload in raw.get("macros", {}).items():
            if not isinstance(name, str) or not isinstance(payload, dict):
                continue
            steps = payload.get("steps", [])
            if not isinstance(steps, list):
                continue
            macros[name] = Macro(
                name=name,
                steps=[str(step) for step in steps if isinstance(step, str) and step],
            )
        recording_name = raw.get("recording_name")
        if isinstance(recording_name, str) and recording_name:
            # Repair on load: if the referenced macro no longer exists
            # (e.g. deleted via the Macros dialog), drop the stale
            # recording_name so start_recording does not raise later.
            if recording_name not in macros:
                logger.debug("Dropping stale recording_name %r on load", recording_name)
                recording_name = None
        else:
            recording_name = None
        last_macro_name = raw.get("last_macro_name")
        if not isinstance(last_macro_name, str) or not last_macro_name:
            last_macro_name = None
        return cls(macros=macros, recording_name=recording_name, last_macro_name=last_macro_name)

    def save(self) -> None:
        write_json_atomic(
            macros_path(),
            {
                "macros": {
                    name: {"steps": macro.steps} for name, macro in sorted(self.macros.items())
                },
                "recording_name": self.recording_name,
                "last_macro_name": self.last_macro_name,
            },
        )

    def start_recording(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Macro name cannot be empty.")
        if self.recording_name is not None:
            raise ValueError("A macro is already being recorded.")
        self.macros[cleaned] = Macro(name=cleaned)
        self.recording_name = cleaned
        self.save()

    def stop_recording(self) -> Macro | None:
        if self.recording_name is None:
            return None
        macro = self.macros[self.recording_name]
        self.last_macro_name = macro.name
        self.recording_name = None
        self.save()
        return macro

    def record(self, command_id: str) -> None:
        if self.recording_name is None or self.playing_back:
            return
        macro = self.macros[self.recording_name]
        macro.steps.append(command_id)
        self.save()

    def rename_macro(self, old_name: str, new_name: str) -> None:
        cleaned = new_name.strip()
        if not cleaned:
            raise ValueError("Macro name cannot be empty.")
        if old_name not in self.macros:
            raise KeyError(old_name)
        if cleaned != old_name and cleaned in self.macros:
            raise ValueError(f"Macro already exists: {cleaned}")
        macro = self.macros.pop(old_name)
        macro.name = cleaned
        self.macros[cleaned] = macro
        if self.recording_name == old_name:
            self.recording_name = cleaned
        if self.last_macro_name == old_name:
            self.last_macro_name = cleaned
        self.save()

    def delete_macro(self, name: str) -> None:
        if name not in self.macros:
            raise KeyError(name)
        del self.macros[name]
        if self.last_macro_name == name:
            self.last_macro_name = None
        if self.recording_name == name:
            self.recording_name = None
        self.save()

    def play_macro(self, name: str, runner: Callable[[str], None]) -> None:
        macro = self.macros.get(name)
        if macro is None:
            raise KeyError(name)
        self.playing_back = True
        try:
            for command_id in macro.steps:
                runner(command_id)
        finally:
            self.playing_back = False
            self.last_macro_name = macro.name
            self.save()

    def play_last_macro(self, runner: Callable[[str], None]) -> None:
        if self.last_macro_name is None:
            raise KeyError("No macro has been recorded yet.")
        self.play_macro(self.last_macro_name, runner)
