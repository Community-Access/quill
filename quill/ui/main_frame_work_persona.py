"""Work Persona commands for MainFrame (#896) — a named bundle that ties a
feature profile, a default working folder, favorite files, and (optionally)
a keymap profile together into one launch.

Extracted into a mixin (CQ-1). ``WorkPersonaMixin`` relies on ``self.features``,
``self.frame``, ``self.open_file``, ``self._announce``, ``self._set_status``,
and ``self._show_modal_dialog`` staying on ``MainFrame``, exactly like the
other command mixins.
"""

from __future__ import annotations

import os
from pathlib import Path

from quill.core.work_persona import WorkPersona, WorkPersonaStore


class WorkPersonaMixin:
    """Launch and manage named Work Persona bundles."""

    def _persona_store(self) -> WorkPersonaStore:
        if not hasattr(self, "_work_persona_store"):
            from quill.core import paths

            self._work_persona_store = WorkPersonaStore(paths.app_data_dir())
        return self._work_persona_store

    def apply_persona(self, persona: WorkPersona) -> None:
        """Apply *persona*: feature profile, working folder, favorites, keymap."""
        applied: list[str] = []

        try:
            self.features.switch_profile(persona.technical_profile)
            applied.append("feature profile")
        except KeyError:
            pass

        if persona.working_folder and Path(persona.working_folder).is_dir():
            try:
                os.chdir(persona.working_folder)
                applied.append("working folder")
            except OSError:
                pass

        if persona.keymap_profile:
            from quill.core.keymap import load_keymap_profile, save_keymap

            try:
                save_keymap(load_keymap_profile(persona.keymap_profile))
                applied.append("keymap (takes effect next restart)")
            except Exception:  # noqa: BLE001 - an unknown keymap profile must not crash launch
                pass

        opened = 0
        for file_str in persona.favorite_files:
            path = Path(file_str)
            if path.is_file():
                self.open_file(path)
                opened += 1
        if opened:
            applied.append(f"{opened} favorite file{'s' if opened != 1 else ''}")

        summary = ", ".join(applied) if applied else "nothing (empty persona)"
        self._set_status(f"Applied persona '{persona.name}': {summary}.")

    def apply_persona_by_name(self, name: str) -> bool:
        """Apply the stored persona named *name*. Returns False if not found."""
        persona = self._persona_store().get(name)
        if persona is None:
            self._set_status(f"Work Persona '{name}' was not found.")
            return False
        self.apply_persona(persona)
        return True

    def open_work_personas(self) -> None:
        from quill.ui.work_persona_dialog import WorkPersonaDialog

        dlg = WorkPersonaDialog(
            self.frame,
            self._persona_store(),
            announce_cb=self._announce,
            apply_cb=self.apply_persona,
        )
        dlg.show()
        dlg.close()
