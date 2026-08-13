"""Palette toggles that say which way they are currently set (#1383).

The Command Palette lists ``Command.title`` verbatim and has no checkmark
column, so "Toggle Soft Wrap" reads identically whether soft wrap is on or off
-- which is the one fact the user opened the palette to learn. Announce Track
Titles was what got reported (twice); every other boolean command in the palette
had the same defect, so this is the general fix rather than one more label.

``_refresh_palette_toggle_titles`` runs once each time the palette opens, so no
individual toggle handler has to remember to retitle itself.
"""

from __future__ import annotations


class PaletteToggleLabelsMixin:
    #: #1383 (generalised): palette toggles whose current state belongs in
    #: their own label. The Command Palette lists ``Command.title`` verbatim and
    #: has no checkmark column, so "Toggle Soft Wrap" reads identically whether
    #: soft wrap is on or off -- the one thing the user opened the palette to
    #: find out. Each entry maps a command id to the settings attribute that
    #: holds its state and that attribute's default.
    #:
    #: ``radio.toggle_title_announcements`` is deliberately absent: its state
    #: lives in the radio history file rather than Settings, and it retitles
    #: itself (``_radio_title_announce_command_title``).
    _PALETTE_TOGGLE_SETTINGS: dict[str, tuple[str, bool]] = {
        "view.toggle_soft_wrap": ("soft_wrap", True),
        "view.toggle_tab_control": ("show_tab_control", True),
        "view.toggle_find_wrap": ("wrap_find", True),
        "view.toggle_persistent_undo": ("persistent_undo", False),
        "view.toggle_spellcheck_as_you_type": ("spellcheck_as_you_type", False),
        "view.toggle_intellisense_as_you_type": ("intellisense_as_you_type", False),
        "format.toggle_abbreviation_expansion": ("abbreviation_expansion", True),
    }

    #: The same idea for toggles whose state is session-only and lives on the
    #: frame rather than in Settings: command id -> attribute, default.
    _PALETTE_TOGGLE_ATTRIBUTES: dict[str, tuple[str, bool]] = {
        "format.toggle_tab_insert_mode": ("_tab_inserts_literal", False),
        "view.toggle_overwrite_mode": ("_overwrite_mode", False),
        "edit.toggle_extend_selection_mode": ("_extend_selection_mode", False),
    }

    def _palette_toggle_state(self, command_id: str) -> bool | None:
        """The current state behind a palette toggle, or None when unknown."""
        if command_id == "view.toggle_dark_mode":
            # Not a boolean setting: the theme is a name, and only "dark" is on.
            return getattr(self.settings, "theme", "system") == "dark"
        runtime = self._PALETTE_TOGGLE_ATTRIBUTES.get(command_id)
        if runtime is not None:
            attribute, default = runtime
            return bool(getattr(self, attribute, default))
        entry = self._PALETTE_TOGGLE_SETTINGS.get(command_id)
        if entry is None:
            return None
        attribute, default = entry
        return bool(getattr(self.settings, attribute, default))

    @staticmethod
    def _palette_base_title(title: str) -> str:
        """A palette title with any previous "(currently ...)" suffix removed."""
        marker = " (currently "
        index = title.find(marker)
        return title[:index] if index >= 0 else title

    def _refresh_palette_toggle_titles(self) -> None:
        """Stamp "(currently On/Off)" onto every stateful palette toggle (#1383).

        Called once each time the palette opens, so the labels are correct
        without every individual toggle handler having to remember to retitle
        itself. Failures are swallowed per command: a palette that opens with
        one stale label is better than a palette that does not open.
        """
        ids = [
            *self._PALETTE_TOGGLE_SETTINGS,
            *self._PALETTE_TOGGLE_ATTRIBUTES,
            "view.toggle_dark_mode",
        ]
        for command_id in ids:
            command = self.commands.get(command_id)
            if command is None:
                continue
            try:
                state = self._palette_toggle_state(command_id)
            except Exception:  # noqa: BLE001 - a label is never worth a crash
                continue
            if state is None:
                continue
            base = self._palette_base_title(command.title)
            self.commands.set_title(command_id, f"{base} (currently {'On' if state else 'Off'})")
