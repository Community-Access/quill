"""Back Up Settings and Restore Settings, for QuillLite (#1501).

Asked for by a QUILL user who wanted to configure the app once and carry that
configuration to his other machines: *"the user often makes several changes to a
complex app like this over a long period of time, and they often don't remember
exactly how they got something to work as they did."*

Two rules, and both come straight out of his description.

**The file is a configuration, not a snapshot of one desk.** What describes
*this* computer -- the recent-files list, the restored session, the window size,
the last time it checked for an update -- is left out
(:data:`quill.core.lite.settings.LOCAL_SETTINGS`). Carrying those to another
machine gives you an app pointing at files that are not there, which is the
failure he was asking to avoid rather than a backup of anything.

**Restoring says what was different.** He asked for a wizard that would notice
settings added since the file was written and walk him through them. What
actually answers the question is a sentence: how many came across, how many are
new since, and how many locations were left alone. A listener can act on that;
an interrogation of three hundred settings is not something anybody finishes.

Nothing here writes a partial state. Restore builds the whole settings object
from defaults plus the file, so the result is a configuration you could describe,
rather than a merge of two that nobody can.
"""

from __future__ import annotations

import json
from pathlib import Path

import wx

from quill.core.lite.settings import export_portable, import_portable

__all__ = ["DocumentSettingsBackupMixin"]

#: The file a backup goes in. ``.qsf`` is what QUILL already uses and what the
#: reporter proposed by name, so the two products agree on the extension even
#: though they do not read each other's files.
WILDCARD = "Quill settings files (*.qsf)|*.qsf|All files (*.*)|*.*"

_SUFFIX = ".qsf"


class DocumentSettingsBackupMixin:
    """``Tools > Back Up Settings`` and ``Tools > Restore Settings``."""

    def cmd_backup_settings(self) -> None:
        """Write every portable setting to a file you can take with you."""
        with wx.FileDialog(
            self,
            "Back up settings",
            wildcard=WILDCARD,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_lite_modal(dialog, "Back up settings") != wx.ID_OK:
                self.control.SetFocus()
                return
            target = Path(dialog.GetPath())
        if target.suffix.lower() != _SUFFIX:
            target = target.with_suffix(_SUFFIX)
        payload, report = export_portable(self.app.settings)
        try:
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as error:
            # Named, not swallowed: a backup that did not happen and did not say
            # so is worse than no backup, because you stop worrying about it.
            self._announce(f"Could not write {target.name}: {error}")
            self.control.SetFocus()
            return
        message = f"Backed up {report.carried} settings to {target.name}"
        if report.local:
            count = len(report.local)
            noun = "location" if count == 1 else "locations"
            message += (
                f". {count} folder and file {noun} were left out, "
                "because those belong to this computer"
            )
        self._announce(message + ".")
        self.control.SetFocus()

    def cmd_restore_settings(self) -> None:
        """Read a backup back in, and say what was different about it."""
        with wx.FileDialog(
            self,
            "Restore settings",
            wildcard=WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_lite_modal(dialog, "Restore settings") != wx.ID_OK:
                self.control.SetFocus()
                return
            source = Path(dialog.GetPath())
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            self._announce(f"Could not read settings from {source.name}: {error}")
            self.control.SetFocus()
            return
        settings, report = import_portable(raw)
        if not report.carried:
            # A file with nothing this build recognises is almost always the
            # wrong file. Changing every setting to its default on the strength
            # of it would be the worst possible reading of the user's intent.
            self._announce(
                f"{source.name} has no settings this version recognises. Nothing was changed."
            )
            self.control.SetFocus()
            return
        self.app.settings = settings
        self.app.save_settings()
        self.app.reapply_settings()
        self.app.rebuild_all_menus()
        self._announce(f"Settings restored from {source.name}. {report.summary()}")
        self.control.SetFocus()

    # ------------------------------------------------------------------ #

    def _show_lite_modal(self, dialog: wx.Dialog, label: str) -> int:
        """The hardened modal path, reached the way the rest of QuillLite does."""
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))
