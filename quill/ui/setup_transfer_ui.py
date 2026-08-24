"""Export and import "my setup", from either app (11.10).

The pure half is :mod:`quill.core.setup_transfer`; this is the two file
prompts, the confirmation that says what an import will overwrite, and the
counted sentences. Shared by Quill Radio and QUILL Cast because the file is
shared: a setup written by one is restored by the other, which is the whole
point of carrying one file rather than two.

Import overwrites, and says so before it does. "Move my setup to another
machine" means the other machine ends up with this setup; merging two
libraries is a different feature with different questions, and pretending
this one does it would be the expensive kind of kindness.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core import setup_transfer

_WILDCARD = f"Quill setup files (*{setup_transfer.EXTENSION})|*{setup_transfer.EXTENSION}"


class SetupTransferMixin:
    """Two commands on the frame, and the prompts behind them."""

    def _register_setup_transfer_commands(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        commands.try_register(
            "app.export_setup",
            "Export My Setup...",
            self.export_my_setup,
            feature_id="core.app",
        )
        commands.try_register(
            "app.import_setup",
            "Import My Setup...",
            self.import_my_setup,
            feature_id="core.app",
        )

    # -- export ---------------------------------------------------------------

    def export_my_setup(self) -> None:
        """Write one file carrying everything this machine has been taught."""
        import wx

        from quill.core.paths import app_data_dir

        default = f"quill-setup-{datetime.now().strftime('%Y-%m-%d')}{setup_transfer.EXTENSION}"
        with wx.FileDialog(  # dialog_button_contract: exempt
            self.frame,
            "Save your setup as",
            wildcard=_WILDCARD,
            defaultFile=default,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as chooser:
            if chooser.ShowModal() != wx.ID_OK:
                self._announce("Export cancelled. Nothing was written.")
                return
            target = Path(chooser.GetPath())
        tally = setup_transfer.export_setup(
            app_data_dir(),
            target,
            app=self._setup_transfer_app_name(),
            stamped=datetime.now(UTC).isoformat(),
        )
        sentence = tally.sentence("Exported", target.name, noun="item")
        self._announce(f"{sentence} {setup_transfer.SECRETS_NOTE}")

    # -- import ---------------------------------------------------------------

    def import_my_setup(self) -> None:
        """Restore a setup file over this machine's settings, after confirming."""
        import wx

        from quill.core.paths import app_data_dir
        from quill.ui.dialog_contract import show_message_box

        with wx.FileDialog(  # dialog_button_contract: exempt
            self.frame,
            "Open a setup file",
            wildcard=_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as chooser:
            if chooser.ShowModal() != wx.ID_OK:
                self._announce("Import cancelled. Nothing was changed.")
                return
            source = Path(chooser.GetPath())
        manifest = setup_transfer.read_manifest(source)
        if not manifest:
            self._announce(f"{source.name} is not a Quill setup file. Nothing was changed.")
            return
        files = [str(name) for name in manifest.get("files", []) if isinstance(name, str)]
        contents = setup_transfer.describe_contents(files)
        created = str(manifest.get("created", "") or "an unknown time")
        answer = show_message_box(
            f"Restore the setup in {source.name}?\n\n{contents}\n\nIt was written by "
            f"{manifest.get('app', 'a Quill app')} at {created}. Restoring REPLACES what is "
            "on this machine -- your current subscriptions, favorites and settings are "
            f"overwritten, not merged.\n\n{setup_transfer.SECRETS_NOTE}",
            "Import My Setup",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self.frame,
            announce=self._announce,
        )
        if answer != wx.YES:
            self._announce("Import cancelled. Nothing was changed.")
            return
        tally = setup_transfer.import_setup(source, app_data_dir())
        sentence = tally.sentence("Restored", source.name, noun="item")
        self._announce(f"{sentence} Close and reopen the app for everything to be read back in.")

    # -- identity -------------------------------------------------------------

    def _setup_transfer_app_name(self) -> str:
        """Which app wrote the file, for its manifest."""
        title = getattr(getattr(self, "frame", None), "GetTitle", None)
        return str(title()) if callable(title) else "a Quill app"
