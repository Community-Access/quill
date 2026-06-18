"""Profile picker orchestration for ``MainFrame`` (issue #138).

Hosts the Alt+Shift+P quick picker plus the two startup conveniences: prompt for
a profile at launch (always, or only when a modifier is held), and switch
profiles automatically based on the opened file's extension. The picker dialog
itself lives in :mod:`quill.ui.profile_picker`; this mixin builds its data and
applies the chosen profile through the existing switch helpers.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.features import PROFILE_DEFINITIONS
from quill.core.profile_startup import (
    ProfileStartupConfig,
    load_profile_startup_config,
    normalize_extension,
    profile_for_path,
    save_profile_startup_config,
    should_prompt_on_startup,
)
from quill.ui.profile_picker import ProfileEntry, ProfilePickerDialog, ProfilePickerResult


class ProfilePickerMixin:
    def _profile_picker_entries(self) -> list[ProfileEntry]:
        from quill.core.onboarding_profiles import list_intent_profiles

        # Build a map from technical profile id -> intent profile preview text so
        # Alt+Shift+P shows the same "what you get" descriptions as the wizard.
        intent_text: dict[str, str] = {}
        for ip in list_intent_profiles():
            if ip.technical_profile not in intent_text:
                intent_text[ip.technical_profile] = ip.preview_text
            else:
                # Two intent profiles share the same technical base; concatenate.
                intent_text[ip.technical_profile] += "\n\n---\n\n" + ip.preview_text

        entries: list[ProfileEntry] = [
            (
                "built_in",
                profile.id,
                profile.name,
                intent_text.get(profile.id, profile.description),
            )
            for profile in PROFILE_DEFINITIONS.values()
        ]
        for profile in self._load_custom_profiles().values():
            description = profile.description or self._custom_profile_summary(profile)
            entries.append(("custom", profile.id, profile.name, description))
        return entries

    def _current_document_extension(self) -> str:
        path = getattr(self.document, "path", None)
        return normalize_extension(Path(path).suffix) if path else ""

    def open_profile_picker(self) -> None:
        """Show the quick profile picker (Alt+Shift+P)."""
        entries = self._profile_picker_entries()
        if not entries:
            self._set_status("No profiles available")
            return
        config = load_profile_startup_config()
        dialog = ProfilePickerDialog(
            self.frame,
            self._wx,
            entries=entries,
            active_profile_id=self.features.active_profile_id,
            current_extension=self._current_document_extension(),
            prompt_on_startup=config.prompt_on_startup,
        )
        result = dialog.show()
        if result is None:
            return
        self._apply_picked_profile(result, config)

    def _apply_picked_profile(
        self, result: ProfilePickerResult, config: ProfileStartupConfig
    ) -> None:
        if result.profile_kind == "custom":
            custom_profile = self._load_custom_profiles().get(result.profile_id)
            if custom_profile is None:
                self._set_status("Custom profile is no longer available")
                return
            self._apply_custom_profile(custom_profile)
        elif result.profile_id == self.features.active_profile_id:
            self._set_status(f"Already using {self.features.active_profile.name}")
        else:
            self.features.switch_profile(result.profile_id)
            self._apply_accelerators()
        self._set_status(f"Profile: {result.profile_name}")
        self._announce(f"Profile {result.profile_name}")
        self._persist_profile_startup_choices(result, config)

    def _persist_profile_startup_choices(
        self, result: ProfilePickerResult, config: ProfileStartupConfig
    ) -> None:
        updated = ProfileStartupConfig(
            prompt_on_startup=result.prompt_on_startup,
            prompt_on_modifier=config.prompt_on_modifier,
            extension_map=dict(config.extension_map),
        )
        # Only built-in profiles can back an extension mapping (custom ids are not
        # in PROFILE_DEFINITIONS, which profile_for_path validates against).
        extension = self._current_document_extension()
        if result.map_extension and extension and result.profile_kind == "built_in":
            updated = updated.with_extension(extension, result.profile_id)
        save_profile_startup_config(updated)

    def run_startup_profile_prompt(self) -> None:
        """Deferred-startup entry point: prompt for a profile if configured (#138)."""
        self.maybe_prompt_profile_on_startup(modifier_held=self._shift_held_at_launch())

    def maybe_prompt_profile_on_startup(self, *, modifier_held: bool) -> None:
        """Open the picker at launch when configured to (issue #138)."""
        config = load_profile_startup_config()
        if should_prompt_on_startup(config, modifier_held=modifier_held):
            self.open_profile_picker()

    def maybe_switch_profile_for_open(self, path: object) -> None:
        """Switch to the extension-mapped profile when opening ``path`` (issue #138)."""
        config = load_profile_startup_config()
        target = profile_for_path(path, config)
        if not target or target == self.features.active_profile_id:
            return
        self.features.switch_profile(target)
        self._apply_accelerators()
        name = PROFILE_DEFINITIONS[target].name
        extension = normalize_extension(Path(str(path)).suffix)
        self._set_status(f"Switched to {name} for {extension} files")
        self._announce(f"Profile {name}")

    def _shift_held_at_launch(self) -> bool:
        """True when Shift is held during launch (the modifier-prompt trigger)."""
        wx = self._wx
        get_key_state = getattr(wx, "GetKeyState", None)
        if not callable(get_key_state):
            return False
        try:
            return bool(get_key_state(wx.WXK_SHIFT))
        except Exception:  # noqa: BLE001 - key state is best-effort
            return False
