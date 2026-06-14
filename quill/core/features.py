from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.feature_catalog import FEATURE_ALIASES, FEATURE_DEFINITIONS, FeatureDefinition
from quill.core.feature_command_map import COMMAND_FEATURE_MAP
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

FEATURE_STATE_ON = "on"
FEATURE_STATE_QUIET = "quiet"
FEATURE_STATE_OFF = "off"

PROFILE_ESSENTIAL = "essential"
PROFILE_WRITER = "writer"
PROFILE_DEVELOPER_POWER_TEXT = "developer_power_text"
PROFILE_ACCESSIBILITY_PROFESSIONAL = "accessibility_professional"
PROFILE_FULL_QUILL = "full_quill"


@dataclass(slots=True)
class FeatureProfile:
    id: str
    name: str
    description: str
    states: dict[str, str] = field(default_factory=dict)


PROFILE_DEFINITIONS: dict[str, FeatureProfile] = {
    PROFILE_ESSENTIAL: FeatureProfile(
        id=PROFILE_ESSENTIAL,
        name="Essential",
        description="Core editing, file, and navigation features.",
        states={
            "core.app": FEATURE_STATE_ON,
            "core.editor": FEATURE_STATE_ON,
            "core.file": FEATURE_STATE_ON,
            "core.edit": FEATURE_STATE_ON,
            "core.search": FEATURE_STATE_ON,
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_OFF,
            "core.links": FEATURE_STATE_QUIET,
            "core.navigate": FEATURE_STATE_ON,
            "core.window": FEATURE_STATE_ON,
            "core.view": FEATURE_STATE_ON,
            "core.spellcheck": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_QUIET,
            "core.analysis": FEATURE_STATE_QUIET,
            "core.trust": FEATURE_STATE_ON,
            "core.accessibility": FEATURE_STATE_ON,
            "core.notifications": FEATURE_STATE_ON,
            "core.updates": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.help": FEATURE_STATE_ON,
            "core.palette": FEATURE_STATE_ON,
            "core.profile": FEATURE_STATE_ON,
            "core.recovery": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_QUIET,
            "core.intellisense": FEATURE_STATE_OFF,
            "future.character_inspector": FEATURE_STATE_OFF,
            "future.cleanup": FEATURE_STATE_OFF,
            "future.regex_library": FEATURE_STATE_OFF,
            "future.ai": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_WRITER: FeatureProfile(
        id=PROFILE_WRITER,
        name="Writer",
        description="Writing, formatting, and cleanup with guided power features.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.ocr": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
            "future.ai": FEATURE_STATE_QUIET,
        },
    ),
    "reader_and_student": FeatureProfile(
        id="reader_and_student",
        name="Reader and Student",
        description="Reading, highlights, references, and light writing workflows.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_OFF,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.ocr": FEATURE_STATE_QUIET,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_OFF,
            "future.cleanup": FEATURE_STATE_OFF,
            "future.regex_library": FEATURE_STATE_OFF,
        },
    ),
    "office_and_admin": FeatureProfile(
        id="office_and_admin",
        name="Office and Admin",
        description="Reliable file work, sessions, cleanup, and printing.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_QUIET,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_DEVELOPER_POWER_TEXT: FeatureProfile(
        id=PROFILE_DEVELOPER_POWER_TEXT,
        name="Developer and Power Text",
        description="Regular Expression, cleanup, inspection, and document analysis tools.",
        states={
            "core.search.regex": FEATURE_STATE_ON,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_ON,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_QUIET,
            "core.watch_folder": FEATURE_STATE_QUIET,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_ON,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    "low_vision": FeatureProfile(
        id="low_vision",
        name="Low Vision",
        description="Higher contrast, larger reading aids, and friendly inspection tools.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_ON,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_QUIET,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    "braille_screen_reader_power_user": FeatureProfile(
        id="braille_screen_reader_power_user",
        name="Braille and Screen Reader Power User",
        description="Screen-reader-friendly navigation with advanced text tools surfaced calmly.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_ACCESSIBILITY_PROFESSIONAL: FeatureProfile(
        id=PROFILE_ACCESSIBILITY_PROFESSIONAL,
        name="Accessibility Professional",
        description="Reading, inspection, trust, and accessibility diagnostics.",
        states={
            "core.search.regex": FEATURE_STATE_QUIET,
            "core.format": FEATURE_STATE_QUIET,
            "core.macros": FEATURE_STATE_QUIET,
            "core.links": FEATURE_STATE_ON,
            "core.read_aloud": FEATURE_STATE_ON,
            "core.voice_commands": FEATURE_STATE_ON,
            "core.watch_folder": FEATURE_STATE_ON,
            "core.analysis": FEATURE_STATE_ON,
            "core.shell": FEATURE_STATE_QUIET,
            "core.keymap": FEATURE_STATE_ON,
            "core.ocr": FEATURE_STATE_ON,
            "core.intellisense": FEATURE_STATE_QUIET,
            "future.character_inspector": FEATURE_STATE_QUIET,
            "future.cleanup": FEATURE_STATE_QUIET,
            "future.regex_library": FEATURE_STATE_QUIET,
        },
    ),
    PROFILE_FULL_QUILL: FeatureProfile(
        id=PROFILE_FULL_QUILL,
        name="Full Quill",
        description="Everything visible, including advanced and experimental paths.",
        states={feature_id: FEATURE_STATE_ON for feature_id in FEATURE_DEFINITIONS},
    ),
}


DEFAULT_PROFILE_ID = PROFILE_ESSENTIAL


def features_path() -> Path:
    return app_data_dir() / "features.json"


QPF_EXTENSION = ".qpf"


def export_feature_profile_file(manager: FeatureManager, path: Path) -> None:
    """Write a manager's profile and feature-flag state to a ``.qpf`` file.

    The on-disk shape is the versioned mapping produced by
    :meth:`FeatureManager.export_profile_data`, so a power user or
    administrator can pre-tune which features are on before first run.
    """

    write_json_atomic(path, manager.export_profile_data())


def import_feature_profile_file(manager: FeatureManager, path: Path) -> list[str]:
    """Apply a ``.qpf`` profile file to ``manager`` and persist the result.

    Returns a list of human-readable warnings for anything that was ignored
    (for example an unknown profile id). Raises ``ValueError`` when the file is
    missing, empty, or not a supported profile document.
    """

    raw = read_json(path, default=None)
    return manager.import_profile_data(raw)


def reset_feature_profile_store() -> None:
    manager = FeatureManager.load()
    manager.reset_to_essential_profile()


def feature_for_command(command_id: str) -> str:
    explicit = COMMAND_FEATURE_MAP
    if command_id in explicit:
        return explicit[command_id]
    if command_id.startswith("tools.read_aloud"):
        return "core.read_aloud"
    if command_id.startswith("tools.shell"):
        return "core.shell"
    if command_id.startswith("tools."):
        return "core.help"
    if command_id.startswith("format.") or command_id.startswith("edit.sort_"):
        return "core.format"
    if command_id.startswith("edit."):
        return "core.edit"
    if command_id.startswith("file."):
        return "core.file"
    if command_id.startswith("navigate."):
        return "core.navigate"
    if command_id.startswith("view."):
        return "core.view"
    if command_id.startswith("window."):
        return "core.window"
    if command_id.startswith("help."):
        return "core.help"
    return "core.app"


def find_feature(feature_name: str) -> FeatureDefinition | None:
    key = feature_name.strip().lower()
    feature_id = FEATURE_ALIASES.get(key)
    if feature_id is not None:
        return FEATURE_DEFINITIONS.get(feature_id)
    for feature in FEATURE_DEFINITIONS.values():
        if key in feature.id.lower() or key in feature.name.lower():
            return feature
    return None


def _normalize_states(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    states: dict[str, str] = {}
    for feature_id, state in raw.items():
        if not isinstance(feature_id, str) or not isinstance(state, str):
            continue
        normalized_state = state.strip().lower()
        if normalized_state not in {FEATURE_STATE_ON, FEATURE_STATE_QUIET, FEATURE_STATE_OFF}:
            continue
        if feature_id not in FEATURE_DEFINITIONS:
            continue
        states[feature_id] = normalized_state
    return states


@dataclass(slots=True)
class FeatureManager:
    active_profile_id: str = DEFAULT_PROFILE_ID
    previous_profile_id: str | None = None
    overrides: dict[str, str] = field(default_factory=dict)
    show_quiet_features: bool = True

    @classmethod
    def load(cls, *, persistent: bool = True) -> FeatureManager:
        if not persistent:
            return cls()
        raw = read_json(features_path(), default={})
        if not isinstance(raw, dict):
            return cls()
        active_profile_id = str(raw.get("active_profile_id", DEFAULT_PROFILE_ID))
        if active_profile_id not in PROFILE_DEFINITIONS:
            active_profile_id = DEFAULT_PROFILE_ID
        previous_profile_id = str(raw.get("previous_profile_id", "")) or None
        if previous_profile_id not in PROFILE_DEFINITIONS:
            previous_profile_id = None
        overrides = _normalize_states(raw.get("overrides"))
        show_quiet_features = bool(raw.get("show_quiet_features", True))
        return cls(
            active_profile_id=active_profile_id,
            previous_profile_id=previous_profile_id,
            overrides=overrides,
            show_quiet_features=show_quiet_features,
        )

    def save(self) -> None:
        write_json_atomic(
            features_path(),
            {
                "active_profile_id": self.active_profile_id,
                "previous_profile_id": self.previous_profile_id,
                "overrides": self.overrides,
                "show_quiet_features": self.show_quiet_features,
            },
            base=app_data_dir(),
        )

    @property
    def active_profile(self) -> FeatureProfile:
        return PROFILE_DEFINITIONS[self.active_profile_id]

    def dependency_chain(self, feature_id: str) -> tuple[str, ...]:
        dependency_ids: list[str] = []
        feature = FEATURE_DEFINITIONS.get(feature_id)
        if feature is None:
            return ()
        for dependency_id in feature.dependencies:
            dependency_ids.append(dependency_id)
            dependency_ids.extend(self.dependency_chain(dependency_id))
        seen: set[str] = set()
        ordered: list[str] = []
        for dependency_id in dependency_ids:
            if dependency_id in seen:
                continue
            seen.add(dependency_id)
            ordered.append(dependency_id)
        return tuple(ordered)

    def state_for(self, feature_id: str) -> str:
        definition = FEATURE_DEFINITIONS.get(feature_id)
        if definition is None:
            return FEATURE_STATE_OFF
        if definition.locked_on:
            return FEATURE_STATE_ON
        if definition.locked_off:
            return FEATURE_STATE_OFF
        if feature_id in self.overrides:
            return self.overrides[feature_id]
        return self.active_profile.states.get(feature_id, FEATURE_STATE_ON)

    def state_for_command(self, command_id: str) -> str:
        return self.state_for(feature_for_command(command_id))

    def is_enabled(self, feature_id: str) -> bool:
        if self.state_for(feature_id) == FEATURE_STATE_OFF:
            return False
        # FLAG-1: a feature whose dependency chain is not fully enabled stays
        # off, no matter how the dependency was turned off (profile or override).
        return all(
            self.state_for(dependency_id) != FEATURE_STATE_OFF
            for dependency_id in self.dependency_chain(feature_id)
        )

    def is_visible(self, feature_id: str) -> bool:
        if not self.is_enabled(feature_id):
            return False
        state = self.state_for(feature_id)
        return state == FEATURE_STATE_ON or (
            state == FEATURE_STATE_QUIET and self.show_quiet_features
        )

    def visible_commands(self, commands: list[Any]) -> list[Any]:
        return [command for command in commands if self.is_visible(command.feature_id)]

    def describe_feature(self, feature_name: str) -> str:
        feature = find_feature(feature_name)
        if feature is None:
            return f"No feature named {feature_name!r} was found."
        state = self.state_for(feature.id)
        profile = self.active_profile
        reason = "This feature is on."
        if state == FEATURE_STATE_QUIET:
            reason = "This feature is quiet in the current profile."
        elif state == FEATURE_STATE_OFF:
            reason = f"This feature is off in the {profile.name} profile."
        return (
            f"Feature: {feature.name}\n"
            f"ID: {feature.id}\n"
            f"State: {state}\n"
            f"Profile: {profile.name}\n"
            f"Maturity: {feature.maturity}\n"
            f"Privacy: {feature.privacy}\n"
            f"{reason}"
        )

    def profile_summary(self) -> str:
        profile = self.active_profile
        return f"Profile: {profile.name}\n\n{profile.description}"

    def available_profiles(self) -> list[FeatureProfile]:
        return [PROFILE_DEFINITIONS[key] for key in PROFILE_DEFINITIONS]

    def change_profile_preview(self, target_profile_id: str) -> str:
        target = PROFILE_DEFINITIONS[target_profile_id]
        current = self.active_profile
        if target.id == current.id:
            return (
                f"{target.name} is already active.\n\n"
                "No switch was made because this profile is already in use."
            )
        turn_on: list[str] = []
        turn_quiet: list[str] = []
        turn_off: list[str] = []
        for feature_id, definition in FEATURE_DEFINITIONS.items():
            current_state = self.state_for(feature_id)
            target_state = target.states.get(feature_id, FEATURE_STATE_ON)
            if definition.locked_on:
                continue
            if current_state == target_state:
                continue
            if target_state == FEATURE_STATE_ON:
                turn_on.append(definition.name)
            elif target_state == FEATURE_STATE_QUIET:
                turn_quiet.append(definition.name)
            else:
                turn_off.append(definition.name)
        return (
            f"Switching from {current.name} to {target.name} will turn on "
            f"{len(turn_on)} features, make {len(turn_quiet)} features quiet, "
            f"and turn off {len(turn_off)} features.\n\n"
            + self._format_feature_lines("Turned on", turn_on)
            + self._format_feature_lines("Made quiet", turn_quiet)
            + self._format_feature_lines("Turned off", turn_off)
        ).rstrip()

    def compare_profiles(self, source_profile_id: str, target_profile_id: str) -> str:
        if source_profile_id not in PROFILE_DEFINITIONS:
            raise KeyError(source_profile_id)
        if target_profile_id not in PROFILE_DEFINITIONS:
            raise KeyError(target_profile_id)
        source = PROFILE_DEFINITIONS[source_profile_id]
        target = PROFILE_DEFINITIONS[target_profile_id]
        if source.id == target.id:
            return f"{source.name} and {target.name} are the same profile."
        changes: list[str] = []
        for feature_id, definition in FEATURE_DEFINITIONS.items():
            source_state = source.states.get(feature_id, FEATURE_STATE_ON)
            target_state = target.states.get(feature_id, FEATURE_STATE_ON)
            if definition.locked_on or source_state == target_state:
                continue
            changes.append(f"- {definition.name}: {source_state} -> {target_state}")
        if not changes:
            return f"{source.name} and {target.name} have the same effective feature states."
        return f"Comparing {source.name} to {target.name}\n\n" + "\n".join(changes)

    def enable_feature(self, feature_id: str) -> list[str]:
        if feature_id not in FEATURE_DEFINITIONS:
            raise KeyError(feature_id)
        affected: list[str] = []
        for dependency_id in self.dependency_chain(feature_id):
            if self.state_for(dependency_id) == FEATURE_STATE_ON:
                continue
            self.overrides[dependency_id] = FEATURE_STATE_ON
            affected.append(dependency_id)
        if (
            not FEATURE_DEFINITIONS[feature_id].locked_on
            and self.state_for(feature_id) != FEATURE_STATE_ON
        ):
            self.overrides[feature_id] = FEATURE_STATE_ON
            affected.append(feature_id)
        self.save()
        return affected

    def disable_feature(self, feature_id: str) -> list[str]:
        if feature_id not in FEATURE_DEFINITIONS:
            raise KeyError(feature_id)
        definition = FEATURE_DEFINITIONS[feature_id]
        if definition.locked_on:
            return []
        affected: list[str] = []
        for dependent_id, dependent in FEATURE_DEFINITIONS.items():
            if feature_id not in dependent.dependencies:
                continue
            if self.state_for(dependent_id) == FEATURE_STATE_OFF:
                continue
            self.overrides[dependent_id] = FEATURE_STATE_OFF
            affected.append(dependent_id)
        self.overrides[feature_id] = FEATURE_STATE_OFF
        affected.append(feature_id)
        self.save()
        return affected

    def set_feature_enabled(self, feature_id: str, enabled: bool) -> list[str]:
        """Turn a single feature on or off, resolving dependencies.

        Returns the feature ids whose effective state changed (including the
        target feature). Enabling a feature also enables what it needs;
        disabling one also turns off the features that depend on it.
        """
        if enabled:
            return self.enable_feature(feature_id)
        return self.disable_feature(feature_id)

    def describe_feature_toggle(
        self, feature_id: str, enabled: bool, affected: Sequence[str]
    ) -> str:
        """Build a screen-reader announcement for a single feature toggle.

        ``affected`` is the list returned by :meth:`set_feature_enabled` and
        is expected to include ``feature_id`` itself when a change occurred.
        """
        definition = FEATURE_DEFINITIONS.get(feature_id)
        name = definition.name if definition is not None else feature_id
        if not affected:
            return f"{name} is already {'on' if enabled else 'off'}."
        others = [
            FEATURE_DEFINITIONS[other_id].name
            for other_id in affected
            if other_id != feature_id and other_id in FEATURE_DEFINITIONS
        ]
        verb = "Turned on" if enabled else "Turned off"
        if not others:
            return f"{verb} {name}."
        count = len(others)
        noun = "feature" if count == 1 else "features"
        relation = "it needs" if enabled else "that need it"
        return f"{verb} {name} (and {count} {noun} {relation}: {', '.join(others)})."

    def switch_profile(self, target_profile_id: str) -> None:
        if target_profile_id not in PROFILE_DEFINITIONS:
            raise KeyError(target_profile_id)
        self.previous_profile_id = self.active_profile_id
        self.active_profile_id = target_profile_id
        self.overrides = {}
        self.save()

    def undo_last_profile_change(self) -> bool:
        if self.previous_profile_id is None:
            return False
        target = self.previous_profile_id
        self.previous_profile_id = self.active_profile_id
        self.active_profile_id = target
        self.overrides = {}
        self.save()
        return True

    def reset_to_essential_profile(self) -> None:
        self.previous_profile_id = self.active_profile_id
        self.active_profile_id = DEFAULT_PROFILE_ID
        self.overrides = {}
        self.save()

    def export_profile_data(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "active_profile_id": self.active_profile_id,
            "previous_profile_id": self.previous_profile_id,
            "overrides": self.overrides,
            "show_quiet_features": self.show_quiet_features,
        }

    def import_profile_data(self, raw: object) -> list[str]:
        if not isinstance(raw, dict):
            raise ValueError("Profile import must be a JSON object.")
        if int(raw.get("schema_version", 0)) != 1:
            raise ValueError("Unsupported profile schema version.")
        warnings: list[str] = []
        active_profile_id = str(raw.get("active_profile_id", DEFAULT_PROFILE_ID))
        if active_profile_id not in PROFILE_DEFINITIONS:
            warnings.append(f"Ignored unknown profile {active_profile_id!r}.")
            active_profile_id = DEFAULT_PROFILE_ID
        previous_profile_id = str(raw.get("previous_profile_id", "")) or None
        if previous_profile_id not in PROFILE_DEFINITIONS:
            previous_profile_id = None
        overrides = _normalize_states(raw.get("overrides"))
        show_quiet_features = bool(raw.get("show_quiet_features", True))
        self.active_profile_id = active_profile_id
        self.previous_profile_id = previous_profile_id
        self.overrides = {
            feature_id: state
            for feature_id, state in overrides.items()
            if not FEATURE_DEFINITIONS[feature_id].locked_on
        }
        self.show_quiet_features = show_quiet_features
        self._enforce_dependencies()
        self.save()
        return warnings

    def _enforce_dependencies(self) -> None:
        for feature_id, state in list(self.overrides.items()):
            if state != FEATURE_STATE_ON:
                continue
            for dependency_id in self.dependency_chain(feature_id):
                if FEATURE_DEFINITIONS[dependency_id].locked_on:
                    continue
                self.overrides[dependency_id] = FEATURE_STATE_ON

    def health_report(self, commands: list[Any]) -> str:
        missing = [command.id for command in commands if not command.feature_id]
        disabled_required = [
            command.id
            for command in commands
            if self.state_for(command.feature_id) == FEATURE_STATE_OFF
            and FEATURE_DEFINITIONS[command.feature_id].locked_on
        ]
        lines = [
            "Feature profile health check",
            f"Active profile: {self.active_profile.name}",
            f"Visible feature definitions: {len(FEATURE_DEFINITIONS)}",
            f"Commands without a feature mapping: {len(missing)}",
            f"Locked features disabled: {len(disabled_required)}",
        ]
        if missing:
            lines.append("")
            lines.append("Unmapped commands:")
            lines.extend(f"- {command_id}" for command_id in missing)
        if disabled_required:
            lines.append("")
            lines.append("Locked commands turned off:")
            lines.extend(f"- {command_id}" for command_id in disabled_required)
        if not missing and not disabled_required:
            lines.append("")
            lines.append("No coverage problems found.")
        return "\n".join(lines)

    @staticmethod
    def _format_feature_lines(label: str, items: list[str]) -> str:
        if not items:
            return ""
        return f"{label}:\n" + "\n".join(f"- {item}" for item in items) + "\n\n"
