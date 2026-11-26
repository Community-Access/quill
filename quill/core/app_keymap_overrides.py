"""Resolve per-app accelerator defaults without overwriting custom bindings."""

from __future__ import annotations

from collections.abc import Mapping


def calculate_app_keymap_overrides(
    app_id: str,
    keymap: Mapping[str, str],
    *,
    app_keymaps: Mapping[str, Mapping[str, str]],
    default_keymap: Mapping[str, str],
) -> dict[str, str]:
    """Apply app defaults when a key is absent or still equals the shipped default.

    This leaves a listener's real customisation untouched. It also replaces
    editor-only chords with the menu accelerators the owning app can use.
    """
    return {
        command_id: binding
        for command_id, binding in app_keymaps.get(app_id, {}).items()
        if not keymap.get(command_id) or keymap.get(command_id) == default_keymap.get(command_id)
    }
